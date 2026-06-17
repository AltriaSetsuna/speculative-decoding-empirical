#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
VLLM_SCRIPTS_DIR = ROOT / "vllm" / "scripts"
D4C_DIR = ROOT / "D4C"
D4C_SCRIPTS_DIR = D4C_DIR / "scripts"
RESULTS_DIR = ROOT / "vllm" / "defects4j" / "results"
DEFAULT_HF_HOME = "/nasdata/yijiali/.cache/huggingface"
DEFAULT_D4C_PYTHON = "/home/yijiali/tools/miniconda3/envs/repairagent/bin/python"

VLLM_BASE_URL = "http://localhost:8081"
VLLM_MODELS_URL = f"{VLLM_BASE_URL}/v1/models"
VLLM_METRICS_URL = f"{VLLM_BASE_URL}/metrics"


@dataclass(frozen=True)
class Job:
    model: str
    method: str
    vllm_script: Path
    d4c_script: Path


METHOD_ORDER = {"autoregressive": 0, "ngram": 1, "suffix": 2, "eagle3": 3, "mlp": 4}
METHOD_SEQUENCE = ["autoregressive", "ngram", "suffix", "eagle3", "mlp"]
DEFECTS4J_CODE_CSV = D4C_DIR / "data" / "defects4j_code.csv"


def normalize_method(script_name: str) -> str:
    stem = Path(script_name).stem.lower()
    if stem.startswith("eagle3"):
        return "eagle3"
    if stem in {"suffix", "suiffix"}:
        return "suffix"
    return stem


def parse_custom_name(script: Path) -> str | None:
    text = script.read_text(errors="replace")
    match = re.search(r"^\s*CUSTOM_NAME=(['\"])(.*?)\1", text, flags=re.MULTILINE)
    if not match:
        return None
    custom_name = match.group(2)
    target_match = re.search(r"^\s*TARGET_MODEL=(['\"])(.*?)\1", text, flags=re.MULTILINE)
    target_model = target_match.group(2) if target_match else None
    frame_version = "vllm-0.12.0"
    if target_model:
        custom_name = custom_name.replace("${TARGET_MODEL##*/}", target_model.rsplit("/", 1)[-1])
    custom_name = custom_name.replace("${FRAME_VERSION}", frame_version)
    return custom_name


def discover_jobs(models: set[str] | None, methods: set[str] | None) -> list[Job]:
    jobs: list[Job] = []
    for model_dir in sorted(VLLM_SCRIPTS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        model = model_dir.name[:-3] if model_dir.name.endswith(".sh") else model_dir.name
        if models and model not in models:
            continue
        for vllm_script in sorted(model_dir.glob("*.sh")):
            method = normalize_method(vllm_script.name)
            if method == "mlp" and model != "L31-70B-I":
                continue
            if methods and method not in methods:
                continue
            d4c_script = D4C_SCRIPTS_DIR / "run_defects4j.sh"
            if d4c_script.exists():
                jobs.append(Job(model, method, vllm_script, d4c_script))
    return jobs


def http_get_text(url: str, timeout: float = 5.0) -> str | None:
    try:
        req = Request(url, headers={"User-Agent": "defects4j-vllm-sweep/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return resp.read().decode("utf-8", errors="replace")
    except (OSError, URLError, TimeoutError):
        return None
    return None


def vllm_endpoint_reachable() -> bool:
    return bool(http_get_text(VLLM_MODELS_URL, timeout=2.0) or http_get_text(f"{VLLM_BASE_URL}/health", timeout=2.0))


def fetch_served_model_name() -> str | None:
    text = http_get_text(VLLM_MODELS_URL, timeout=5.0)
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    for item in payload.get("data", []):
        model_id = item.get("id")
        if model_id:
            return str(model_id)
    return None


def wait_for_vllm(proc: subprocess.Popen, timeout_s: float, poll_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        if http_get_text(VLLM_MODELS_URL, timeout=5.0):
            return True
        if http_get_text(f"{VLLM_BASE_URL}/health", timeout=5.0):
            return True
        time.sleep(poll_s)
    return False


def stop_process_tree(proc: subprocess.Popen, grace_s: float = 30.0) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + grace_s
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.5)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


MetricKey = Tuple[str, Tuple[Tuple[str, str], ...]]


def parse_labels(raw: str | None) -> tuple[tuple[str, str], ...]:
    if not raw:
        return ()
    labels: list[tuple[str, str]] = []
    for match in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:\\.|[^"\\])*)"', raw):
        key, value = match.groups()
        labels.append((key, bytes(value, "utf-8").decode("unicode_escape")))
    return tuple(sorted(labels))


def parse_prometheus_metrics(text: str | None) -> dict[MetricKey, float]:
    values: dict[MetricKey, float] = {}
    if not text:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{([^}]*)\})?\s+([-+0-9.eE]+)$", line)
        if not match:
            continue
        name, raw_labels, raw_value = match.groups()
        try:
            value = float(raw_value)
        except ValueError:
            continue
        values[(name, parse_labels(raw_labels))] = value
    return values


def labels_dict(labels: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(labels)


def metric_sum(metrics: dict[MetricKey, float], name: str, **required_labels: str) -> float | None:
    total = 0.0
    matched = False
    for (metric_name, labels), value in metrics.items():
        if metric_name != name:
            continue
        label_map = labels_dict(labels)
        if all(label_map.get(key) == val for key, val in required_labels.items()):
            total += value
            matched = True
    return total if matched else None


def safe_div(num: float | None, den: float | None) -> float | None:
    if num is None or den in (None, 0):
        return None
    return num / den


def format_number(value: object, digits: int = 2) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def expected_defects4j_bugs() -> int | None:
    if not DEFECTS4J_CODE_CSV.exists():
        return None
    try:
        with DEFECTS4J_CODE_CSV.open(newline="") as f:
            counts: dict[str, int] = {}
            for row in csv.DictReader(f):
                slug = row.get("slug")
                if slug:
                    counts[slug] = counts.get(slug, 0) + 1
    except OSError:
        return None
    return sum(1 for count in counts.values() if count == 1)


def parse_eval_csv(path: Path) -> dict[str, object]:
    total_bugs = expected_defects4j_bugs()
    if not path.exists():
        return {"correct": None, "bugs": None, "evaluated_bugs": None, "total_bugs": total_bugs, "correct_pct": None, "correct_pct_total": None}
    rows = list(csv.DictReader(path.open()))
    if not rows:
        return {"correct": 0, "bugs": 0, "evaluated_bugs": 0, "total_bugs": total_bugs, "correct_pct": 0.0, "correct_pct_total": 0.0}
    bugs = len({row["slug"] for row in rows if row.get("slug")})
    correct = len({row["slug"] for row in rows if row.get("reward") == "True"})
    return {
        "correct": correct,
        "bugs": bugs,
        "evaluated_bugs": bugs,
        "total_bugs": total_bugs,
        "correct_pct": safe_div(correct * 100.0, bugs),
        "correct_pct_total": safe_div(correct * 100.0, total_bugs),
    }


def d4c_named_csv(prefix: Path, remote_model: str, max_try: int, temperature: float) -> Path:
    alias = remote_model.rsplit("/", 1)[-1]
    return Path(f"{prefix}_full_1shot_{alias}_{max_try}try_temp={temperature}.csv")


def summarize_metrics(metrics_text: str | None) -> dict[str, object]:
    metrics = parse_prometheus_metrics(metrics_text)
    generation_tokens = metric_sum(metrics, "vllm:request_generation_tokens_sum")
    decode_seconds = metric_sum(metrics, "vllm:request_decode_time_seconds_sum")
    accepted_tokens = metric_sum(metrics, "vllm:spec_decode_num_accepted_tokens_total")
    drafts = metric_sum(metrics, "vllm:spec_decode_num_drafts_total")
    accepted_by_pos: dict[int, float] = {}
    for pos in range(14):
        value = metric_sum(metrics, "vllm:spec_decode_num_accepted_tokens_per_pos_total", position=str(pos))
        if value is not None:
            accepted_by_pos[pos] = value
    n_alpha = {}
    for pos in range(14):
        numerator = accepted_by_pos.get(pos)
        denominator = drafts if pos == 0 else accepted_by_pos.get(pos - 1)
        n_alpha[str(pos)] = safe_div(numerator, denominator)
    return {
        "tps": safe_div(generation_tokens, decode_seconds),
        "mean_accept_length": safe_div(accepted_tokens, drafts),
        "generation_tokens": generation_tokens,
        "decode_seconds": decode_seconds,
        "accepted_tokens": accepted_tokens,
        "drafts": drafts,
        "accepted_by_pos": json.dumps(accepted_by_pos, ensure_ascii=False, sort_keys=True),
        "n_alpha": json.dumps(n_alpha, ensure_ascii=False, sort_keys=True),
        **{f"n_alpha_{pos}": n_alpha[str(pos)] for pos in range(14)},
    }


def job_result_dir(job: Job) -> Path:
    return RESULTS_DIR / job.model / job.method


def load_completed_result(job: Job) -> dict[str, object] | None:
    result_path = job_result_dir(job) / "result.json"
    if not result_path.exists():
        return None
    try:
        row = json.loads(result_path.read_text())
    except json.JSONDecodeError:
        return None
    return row if row.get("status") == "ok" else None


def is_completed(row: dict[str, object] | None) -> bool:
    if row is None or row.get("status") != "ok":
        return False
    try:
        return row.get("tps") is not None and float(row["tps"]) > 0
    except (TypeError, ValueError):
        return False


def completed_tps(row: dict[str, object] | None) -> float | None:
    if not is_completed(row):
        return None
    try:
        return float(row["tps"])
    except (TypeError, ValueError):
        return None


def completed_runtime_seconds(row: dict[str, object] | None) -> float | None:
    if not is_completed(row):
        return None
    try:
        return float(row["d4c_seconds"])
    except (TypeError, ValueError):
        return None


def row_speedup(row: dict[str, object], baseline_tps: float | None, baseline_seconds: float | None) -> float | None:
    try:
        speedup = safe_div(float(row["tps"]), baseline_tps) if row.get("tps") is not None else None
    except (TypeError, ValueError):
        speedup = None
    if speedup is None and row.get("method") == "mlp":
        speedup = safe_div(baseline_seconds, completed_runtime_seconds(row))
    return speedup


def load_model_rows(model: str) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for method in METHOD_SEQUENCE:
        path = RESULTS_DIR / model / method / "result.json"
        if not path.exists():
            continue
        try:
            rows[method] = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
    return rows


def render_model_summary(model: str, rows_by_method: dict[str, dict[str, object]]) -> str:
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    baseline_tps = completed_tps(rows_by_method.get("autoregressive"))
    baseline_seconds = completed_runtime_seconds(rows_by_method.get("autoregressive"))
    headers = ["method", "correct/total(%)", "tps", "speedup", "mal"] + [f"{idx}-alpha" for idx in range(12)]
    lines = [
        f"# {model}",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for method in METHOD_SEQUENCE:
        row = rows_by_method.get(method, {})
        cells = [
            method,
            format_number(row.get("correct_pct_total")),
            format_number(row.get("tps")),
            format_number(row_speedup(row, baseline_tps, baseline_seconds)) if row else "",
            format_number(row.get("mean_accept_length")) if method != "mlp" else "",
        ]
        if method == "mlp":
            cells.extend([""] * 12)
        else:
            cells.extend(format_number(row.get(f"n_alpha_{idx}")) for idx in range(12))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_model_summary(model: str) -> None:
    model_dir = RESULTS_DIR / model
    model_dir.mkdir(parents=True, exist_ok=True)
    content = render_model_summary(model, load_model_rows(model))
    (model_dir / f"{model}.md").write_text(content)


def unlink_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def write_result(job: Job, row: dict[str, object]) -> None:
    result_dir = job_result_dir(job)
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "result.json").write_text(json.dumps(row, ensure_ascii=False, indent=2))
    (result_dir / "result.md").write_text(
        "\n".join(
            [
                f"# {job.model}/{job.method}",
                "",
                f"- correct(%): {format_number(row.get('correct_pct'))}",
                f"- correct/total(%): {format_number(row.get('correct_pct_total'))}",
                f"- correct: {row.get('correct')}",
                f"- bugs: {row.get('bugs')} (evaluated)",
                f"- total_bugs: {row.get('total_bugs')}",
                f"- tps: {format_number(row.get('tps'))}",
                f"- mean_accept_length: {format_number(row.get('mean_accept_length'))}",
            ]
        )
        + "\n"
    )


def append_csv(path: Path, row: dict[str, object]) -> None:
    fieldnames = [
        "timestamp",
        "model",
        "method",
        "status",
        "vllm_script",
        "d4c_script",
        "vllm_exit_code",
        "d4c_exit_code",
        "startup_seconds",
        "d4c_seconds",
        "correct_pct",
        "correct_pct_total",
        "correct",
        "bugs",
        "evaluated_bugs",
        "total_bugs",
        "tps",
        "mean_accept_length",
        "generation_tokens",
        "decode_seconds",
        "accepted_tokens",
        "drafts",
        "accepted_by_pos",
        "n_alpha",
        "vllm_log",
        "d4c_log",
        "metrics_snapshot",
        "eval_csv",
        "error",
    ]
    exists = path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in fieldnames})


def run_command(script: Path, cwd: Path, log_path: Path, timeout_s: float | None, env: dict[str, str]) -> tuple[int | None, float, str | None]:
    start = time.time()
    with log_path.open("w") as log:
        proc = subprocess.Popen(["bash", str(script)], cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=env)
        try:
            exit_code = proc.wait(timeout=timeout_s)
            return exit_code, time.time() - start, None
        except subprocess.TimeoutExpired:
            stop_process_tree(proc)
            return proc.poll(), time.time() - start, f"timeout after {timeout_s}s"


def make_child_env(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    env["HF_HOME"] = args.hf_home
    env["HF_HUB_CACHE"] = str(Path(args.hf_home) / "hub")
    env["TRANSFORMERS_CACHE"] = str(Path(args.hf_home) / "hub")
    env.setdefault("HF_HUB_OFFLINE", "1")
    env["OPENAI_API_BASE"] = f"{VLLM_BASE_URL}/v1"
    env["OPENAI_BASE_URL"] = env["OPENAI_API_BASE"]
    env["OPENAI_API_KEY"] = "EMPTY"
    env["REMOTE_PROXY"] = args.remote_proxy
    env["MAX_TRY"] = str(args.max_try)
    env["TEMPERATURE"] = str(args.temperature)
    env["BATCH_SIZE"] = str(args.batch_size)
    env["D4C_MODE"] = args.d4c_mode
    if args.python_bin:
        env["PYTHON_BIN"] = args.python_bin
    if args.eval_pred:
        env["D4C_EVAL_PRED"] = str(Path(args.eval_pred).resolve())
    return env


def run_job(job: Job, args: argparse.Namespace, summary_csv: Path, summary_jsonl: Path) -> dict[str, object]:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    result_dir = job_result_dir(job)
    result_dir.mkdir(parents=True, exist_ok=True)
    vllm_log = result_dir / "vllm.log"
    d4c_log = result_dir / "d4c.log"
    metrics_snapshot = result_dir / "metrics.txt"
    eval_csv = result_dir / "eval.csv"
    row: dict[str, object] = {
        "timestamp": stamp,
        "model": job.model,
        "method": job.method,
        "status": "started",
        "vllm_script": str(job.vllm_script),
        "d4c_script": str(job.d4c_script),
        "vllm_log": str(vllm_log),
        "d4c_log": str(d4c_log),
        "metrics_snapshot": str(metrics_snapshot),
        "eval_csv": str(eval_csv),
        "error": "",
    }
    child_env = make_child_env(args)
    result_prefix = D4C_DIR / "result" / "defects4j" / f"{job.model}_{job.method}_pred"
    eval_prefix = D4C_DIR / "result" / "defects4j" / f"{job.model}_{job.method}_eval"
    child_env["D4C_RESULT_PATH"] = str(result_prefix)
    child_env["D4C_EVAL_PATH"] = str(eval_prefix)
    print(f"\n=== {job.model}/{job.method} ===", flush=True)
    completed = load_completed_result(job)
    if completed and not args.force:
        print(f"[skip] existing final result: {job_result_dir(job) / 'result.json'}", flush=True)
        append_csv(summary_csv, completed)
        append_jsonl(summary_jsonl, completed)
        return completed
    if not args.allow_existing_server and vllm_endpoint_reachable():
        row["status"] = "port_busy"
        row["error"] = f"{VLLM_BASE_URL} is already reachable before starting this job."
        append_csv(summary_csv, row)
        append_jsonl(summary_jsonl, row)
        write_result(job, row)
        write_model_summary(job.model)
        return row
    start = time.time()
    with vllm_log.open("w") as log:
        proc = subprocess.Popen(["bash", str(job.vllm_script)], cwd=str(job.vllm_script.parent), stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=child_env)
    try:
        ok = wait_for_vllm(proc, args.startup_timeout, args.poll_interval)
        row["startup_seconds"] = round(time.time() - start, 3)
        row["vllm_exit_code"] = proc.poll()
        if not ok:
            row["status"] = "vllm_start_failed"
            row["error"] = "vLLM did not become healthy before timeout, or exited early"
            return row
        served_model = fetch_served_model_name() or parse_custom_name(job.vllm_script) or args.remote_model
        child_env["REMOTE_MODEL"] = served_model
        row["remote_model"] = served_model
        if not args.keep_d4c_csv:
            stale_pred = d4c_named_csv(result_prefix, served_model, args.max_try, args.temperature)
            stale_eval = d4c_named_csv(eval_prefix, served_model, args.max_try, args.temperature)
            unlink_if_exists(stale_pred)
            unlink_if_exists(stale_eval)
            print(f"[clean] removed stale D4C CSVs for {job.model}/{job.method}", flush=True)
        print(f"正在跑 {job.model}/{job.method}，served_model={served_model}，batch_size={args.batch_size}", flush=True)
        d4c_exit, d4c_seconds, d4c_error = run_command(job.d4c_script, D4C_DIR, d4c_log, args.d4c_timeout, child_env)
        row["d4c_exit_code"] = d4c_exit
        row["d4c_seconds"] = round(d4c_seconds, 3)
        if d4c_error:
            row["error"] = d4c_error
        if args.eval_pred:
            eval_path = Path(args.eval_pred).resolve()
        else:
            eval_path = d4c_named_csv(eval_prefix, served_model, args.max_try, args.temperature).resolve()
        if eval_path.exists():
            if eval_path != eval_csv:
                eval_csv.write_text(eval_path.read_text())
            row.update(parse_eval_csv(eval_csv))
        time.sleep(args.metrics_delay)
        metrics_text = http_get_text(VLLM_METRICS_URL, timeout=10.0)
        if metrics_text:
            metrics_snapshot.write_text(metrics_text)
        row.update(summarize_metrics(metrics_text))
        row["status"] = "ok" if d4c_exit == 0 else "d4c_failed"
        print(f"[result] status={row['status']} correct(%)={row.get('correct_pct')} tps={row.get('tps')}", flush=True)
    except Exception as exc:
        row["status"] = "runner_error"
        row["error"] = repr(exc)
        print(f"[error] {job.model}/{job.method}: {exc!r}", flush=True)
    finally:
        stop_process_tree(proc, grace_s=args.stop_grace)
        row["vllm_exit_code"] = proc.poll()
        append_csv(summary_csv, row)
        append_jsonl(summary_jsonl, row)
        write_result(job, row)
        write_model_summary(job.model)
    return row


def append_jsonl(path: Path, row: dict[str, object]) -> None:
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_csv_filter(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    return {item.strip() for item in raw.split(",") if item.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run vLLM + D4C Defects4J benchmark sweep.")
    parser.add_argument("--models", help="comma-separated model directory names, without .sh")
    parser.add_argument("--methods", help="comma-separated methods: autoregressive,ngram,suffix,eagle3,mlp")
    parser.add_argument("--remote-model", default="gpt-4-0613")
    parser.add_argument("--remote-proxy", default="OpenAICompatible")
    parser.add_argument("--max-try", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--d4c-mode", choices=["agent", "agentless"], default="agent")
    parser.add_argument("--batch-size", type=int, default=8, help="D4C request concurrency for non-mlp runs")
    parser.add_argument("--mlp-batch-size", type=int, default=1, help="D4C request concurrency for mlp")
    parser.add_argument("--startup-timeout", type=float, default=900.0)
    parser.add_argument("--d4c-timeout", type=float, default=None)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--metrics-delay", type=float, default=5.0)
    parser.add_argument("--stop-grace", type=float, default=30.0)
    parser.add_argument("--hf-home", default=DEFAULT_HF_HOME)
    parser.add_argument("--python-bin", default=DEFAULT_D4C_PYTHON)
    parser.add_argument("--eval-pred", help="explicit D4C eval csv path to read")
    parser.add_argument("--allow-existing-server", action="store_true")
    parser.add_argument("--keep-d4c-csv", action="store_true", help="do not delete D4C pred/eval CSVs before rerunning an unfinished job")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_csv = RESULTS_DIR / "defects4j_vllm_sweep.csv"
    summary_jsonl = RESULTS_DIR / "defects4j_vllm_sweep.jsonl"
    summary_md = RESULTS_DIR / "defects4j_vllm_sweep.md"

    jobs = discover_jobs(parse_csv_filter(args.models), parse_csv_filter(args.methods))
    if not jobs:
        print("No matching jobs found.", file=sys.stderr)
        return 1
    print(f"Discovered {len(jobs)} jobs:")
    for job in jobs:
        print(f"  {job.model}/{job.method}: {job.vllm_script.name} -> {job.d4c_script}")
    if args.dry_run:
        return 0
    rows = []
    for job in jobs:
        args.batch_size = args.mlp_batch_size if job.method == "mlp" else 8
        rows.append(run_job(job, args, summary_csv, summary_jsonl))
        write_model_summary(job.model)
    summary_md.write_text("\n".join([f"# Defects4J sweep", ""] + [json.dumps(row, ensure_ascii=False) for row in rows]) + "\n")
    print(f"\nSummary CSV:  {summary_csv}")
    print(f"Summary JSON: {summary_jsonl}")
    print(f"Summary MD:   {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
