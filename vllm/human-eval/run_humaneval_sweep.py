#!/usr/bin/env python3
"""
Run vLLM deployment scripts one by one, execute the matching HumanEval script,
record vLLM speculative-decoding metrics, and stop the vLLM server before the
next run.

The script pairs:
  vllm/scripts/<model>.sh/<method-ish>.sh
with:
  human-eval/scripts/<model>/<method>.sh
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import signal
import shutil
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
HUMANEVAL_DIR = ROOT / "human-eval"
HUMANEVAL_SCRIPTS_DIR = HUMANEVAL_DIR / "scripts"
RESULTS_DIR = ROOT / "vllm" / "human-eval" / "results"
DEFAULT_HF_HOME = "/nasdata/yijiali/.cache/huggingface"

VLLM_BASE_URL = "http://localhost:8081"
VLLM_MODELS_URL = f"{VLLM_BASE_URL}/v1/models"
VLLM_METRICS_URL = f"{VLLM_BASE_URL}/metrics"
GRAFANA_URL = "http://localhost:3000/"


@dataclass(frozen=True)
class Job:
    model: str
    method: str
    vllm_script: Path
    humaneval_script: Path


METHOD_ORDER = {
    "autoregressive": 0,
    "ngram": 1,
    "suffix": 2,
    "eagle3": 3,
    "mlp": 4,
}
METHOD_SEQUENCE = ["autoregressive", "ngram", "suffix", "eagle3", "mlp"]


def normalize_method(script_name: str) -> str:
    stem = Path(script_name).stem.lower()
    if stem.startswith("eagle3"):
        return "eagle3"
    if stem in {"suffix", "suiffix"}:
        return "suffix"
    if stem == "ngram":
        return "ngram"
    if stem == "autoregressive":
        return "autoregressive"
    return stem


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
            humaneval_script = HUMANEVAL_SCRIPTS_DIR / model / f"{method}.sh"
            if humaneval_script.exists():
                jobs.append(Job(model, method, vllm_script, humaneval_script))
            else:
                print(
                    f"[skip] no HumanEval script for {model}/{method}: {humaneval_script}",
                    flush=True,
                )
    return jobs


def http_get_text(url: str, timeout: float = 5.0) -> str | None:
    try:
        req = Request(url, headers={"User-Agent": "humaneval-vllm-sweep/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return resp.read().decode("utf-8", errors="replace")
    except (OSError, URLError, TimeoutError):
        return None
    return None


def vllm_endpoint_reachable() -> bool:
    return bool(
        http_get_text(VLLM_MODELS_URL, timeout=2.0)
        or http_get_text(f"{VLLM_BASE_URL}/health", timeout=2.0)
    )


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
        match = re.match(
            r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{([^}]*)\})?\s+([-+0-9.eE]+)$",
            line,
        )
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
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.{digits}f}"


def summarize_metrics(metrics_text: str | None) -> dict[str, object]:
    metrics = parse_prometheus_metrics(metrics_text)
    generation_tokens = metric_sum(metrics, "vllm:request_generation_tokens_sum")
    decode_seconds = metric_sum(metrics, "vllm:request_decode_time_seconds_sum")
    accepted_tokens = metric_sum(metrics, "vllm:spec_decode_num_accepted_tokens_total")
    drafts = metric_sum(metrics, "vllm:spec_decode_num_drafts_total")

    accepted_by_pos: dict[int, float] = {}
    n_alpha: dict[str, float | None] = {}
    for pos in range(14):
        value = metric_sum(
            metrics,
            "vllm:spec_decode_num_accepted_tokens_per_pos_total",
            position=str(pos),
        )
        if value is not None:
            accepted_by_pos[pos] = value

    for pos in range(14):
        numerator = accepted_by_pos.get(pos)
        denominator = drafts if pos == 0 else accepted_by_pos.get(pos - 1)
        n_alpha[str(pos)] = safe_div(numerator, denominator)

    return {
        "tps": safe_div(generation_tokens, decode_seconds),
        "tps_source": "vllm:request_generation_tokens_sum/vllm:request_decode_time_seconds_sum",
        "mean_accept_length": safe_div(accepted_tokens, drafts),
        "mean_accept_length_source": "vllm:spec_decode_num_accepted_tokens_total/vllm:spec_decode_num_drafts_total",
        "n_alpha": json.dumps(n_alpha, ensure_ascii=False, sort_keys=True),
        "n_alpha_source": "pos0=accepted_pos_0/drafts; posN=accepted_pos_N/accepted_pos_N-1",
        "generation_tokens": generation_tokens,
        "decode_seconds": decode_seconds,
        "accepted_tokens": accepted_tokens,
        "drafts": drafts,
        "accepted_by_pos": json.dumps(accepted_by_pos, ensure_ascii=False, sort_keys=True),
        **{f"n_alpha_{pos}": n_alpha[str(pos)] for pos in range(14)},
    }


def row_sort_key(row: dict[str, object]) -> tuple[str, int, str]:
    method = str(row.get("method") or "")
    return (str(row.get("model") or ""), METHOD_ORDER.get(method, 100), method)


def method_label(row: dict[str, object]) -> str:
    method = str(row.get("method") or "")
    script_name = Path(str(row.get("vllm_script") or "")).stem
    if method == "eagle3":
        return script_name
    return method


def metric_headers() -> list[str]:
    return ["pass@1", "tps", "speedup", "mal"] + [f"{idx}-alpha" for idx in range(12)]


def completed_tps(row: dict[str, object] | None) -> float | None:
    if row is None or not is_completed(row):
        return None
    try:
        return float(row["tps"])
    except (TypeError, ValueError):
        return None


def completed_runtime_seconds(row: dict[str, object] | None) -> float | None:
    if row is None or not is_completed(row):
        return None
    try:
        return float(row["humaneval_seconds"])
    except (TypeError, ValueError):
        return None


def row_speedup(row: dict[str, object], baseline_tps: float | None, baseline_seconds: float | None) -> float | None:
    tps = row.get("tps")
    try:
        speedup = safe_div(float(tps), baseline_tps) if tps is not None else None
    except (TypeError, ValueError):
        speedup = None
    if speedup is None and row.get("method") == "mlp":
        runtime_seconds = completed_runtime_seconds(row)
        speedup = safe_div(baseline_seconds, runtime_seconds)
    return speedup


def render_markdown_tables(rows: list[dict[str, object]]) -> str:
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# HumanEval vLLM Sweep Results",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "Metrics use the same global vLLM formulas as the CanItEdit sweep:",
        "",
        "- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`",
        "- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`",
        "- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`",
        "- `speedup = method_tps / autoregressive_tps` within the same model",
        "",
    ]
    by_model: dict[str, list[dict[str, object]]] = {}
    for row in sorted(rows, key=row_sort_key):
        by_model.setdefault(str(row.get("model") or "unknown"), []).append(row)

    headers = ["method"] + metric_headers()
    for model, model_rows in by_model.items():
        baseline_tps = None
        baseline_seconds = None
        for row in model_rows:
            if row.get("method") == "autoregressive":
                baseline_tps = completed_tps(row)
                baseline_seconds = completed_runtime_seconds(row)
                break

        lines.extend([f"## {model}", "", "| " + " | ".join(headers) + " |"])
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in model_rows:
            tps = row.get("tps")
            speedup = row_speedup(row, baseline_tps, baseline_seconds)
            if row.get("method") == "mlp":
                cells = [
                    method_label(row),
                    format_number(row.get("pass@1")),
                    format_number(tps),
                    format_number(speedup),
                    "",
                ]
                cells.extend([""] * 12)
                if row.get("status") != "ok":
                    cells[1] = str(row.get("status") or "")
                lines.append("| " + " | ".join(cells) + " |")
                continue
            cells = [
                method_label(row),
                format_number(row.get("pass@1")),
                format_number(tps),
                format_number(speedup),
                format_number(row.get("mean_accept_length")),
            ]
            cells.extend(format_number(row.get(f"n_alpha_{idx}")) for idx in range(12))
            if row.get("status") != "ok":
                cells[1] = str(row.get("status") or "")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def write_markdown(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(render_markdown_tables(rows))


def render_fixed_model_table(model: str, rows_by_method: dict[str, dict[str, object]]) -> str:
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    headers = ["method"] + metric_headers()
    baseline_tps = completed_tps(rows_by_method.get("autoregressive"))
    baseline_seconds = completed_runtime_seconds(rows_by_method.get("autoregressive"))
    lines = [
        f"# {model}",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for method in METHOD_SEQUENCE:
        row = rows_by_method.get(method)
        cells = [method]
        if row is not None and is_completed(row):
            tps = row.get("tps")
            speedup = row_speedup(row, baseline_tps, baseline_seconds)
            if method == "mlp":
                cells.extend(
                    [
                        format_number(row.get("pass@1")),
                        format_number(tps),
                        format_number(speedup),
                        "",
                    ]
                )
                cells.extend([""] * 12)
                lines.append("| " + " | ".join(cells) + " |")
                continue
            cells.extend(
                [
                    format_number(row.get("pass@1")),
                    format_number(tps),
                    format_number(speedup),
                    format_number(row.get("mean_accept_length")),
                ]
            )
            cells.extend(format_number(row.get(f"n_alpha_{idx}")) for idx in range(12))
        else:
            cells.extend([""] * (len(headers) - 1))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def job_result_dir(job: Job) -> Path:
    return RESULTS_DIR / job.model / job.method


def job_completed_path(job: Job) -> Path:
    return job_result_dir(job) / "result.json"


def is_completed(row: dict[str, object]) -> bool:
    if row.get("status") != "ok":
        return False
    if row.get("humaneval_exit_code") != 0:
        return False
    try:
        return row.get("tps") is not None and float(row["tps"]) > 0
    except (TypeError, ValueError):
        return False


def load_completed_job(job: Job) -> dict[str, object] | None:
    path = job_completed_path(job)
    if not path.exists():
        return None
    try:
        row = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if is_completed(row):
        return row
    return None


def write_job_artifacts(job: Job, row: dict[str, object]) -> None:
    result_dir = job_result_dir(job)
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "result.json").write_text(json.dumps(row, ensure_ascii=False, indent=2))
    (result_dir / "result.md").write_text(render_markdown_tables([row]))


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


def write_model_summary(model: str) -> None:
    model_dir = RESULTS_DIR / model
    model_dir.mkdir(parents=True, exist_ok=True)
    rows_by_method = load_model_rows(model)
    (model_dir / f"{model}.md").write_text(render_fixed_model_table(model, rows_by_method))


def append_csv(path: Path, row: dict[str, object]) -> None:
    fieldnames = [
        "timestamp",
        "model",
        "method",
        "status",
        "vllm_script",
        "humaneval_script",
        "vllm_exit_code",
        "humaneval_exit_code",
        "startup_seconds",
        "humaneval_seconds",
        "grafana_reachable",
        "pass@1",
        "pass@10",
        "pass@100",
        "generated_samples",
        "generation_failures",
        "generation_seconds",
        "evaluation_seconds",
        "humaneval_sample_file",
        "humaneval_result_file",
        "tps",
        "tps_source",
        "mean_accept_length",
        "mean_accept_length_source",
        "n_alpha",
        "n_alpha_source",
        "n_alpha_0",
        "n_alpha_1",
        "n_alpha_2",
        "n_alpha_3",
        "n_alpha_4",
        "n_alpha_5",
        "n_alpha_6",
        "n_alpha_7",
        "n_alpha_8",
        "n_alpha_9",
        "n_alpha_10",
        "n_alpha_11",
        "n_alpha_12",
        "n_alpha_13",
        "generation_tokens",
        "decode_seconds",
        "accepted_tokens",
        "drafts",
        "accepted_by_pos",
        "vllm_log",
        "humaneval_log",
        "metrics_snapshot",
        "humaneval_output_dir",
        "error",
    ]
    exists = path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key) for key in fieldnames})


def append_jsonl(path: Path, row: dict[str, object]) -> None:
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_target_model(script: Path) -> str | None:
    text = script.read_text(errors="replace")
    match = re.search(r"^\s*TARGET_MODEL=(['\"])(.*?)\1", text, flags=re.MULTILINE)
    return match.group(2) if match else None


def humaneval_output_dir(job: Job) -> Path | None:
    target_model = parse_target_model(job.humaneval_script)
    if not target_model:
        return None
    return HUMANEVAL_DIR / "out" / target_model.rsplit("/", 1)[-1] / job.method


def maybe_clear_humaneval_output(job: Job, fresh_output: bool) -> str | None:
    if not fresh_output:
        return None
    output_dir = humaneval_output_dir(job)
    if output_dir is None:
        return "could not parse TARGET_MODEL for fresh output cleanup"
    if output_dir.exists():
        shutil.rmtree(output_dir)
        return f"removed existing output dir: {output_dir}"
    return f"output dir already clean: {output_dir}"


def parse_humaneval_summary(output_dir: Path | None) -> dict[str, object]:
    if output_dir is None:
        return {}
    summary_path = output_dir / "summary.json"
    if not summary_path.exists():
        return {}
    try:
        summary = json.loads(summary_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    pass_at_k = summary.get("pass_at_k") or {}
    return {
        "pass@1": pass_at_k.get("pass@1"),
        "pass@10": pass_at_k.get("pass@10"),
        "pass@100": pass_at_k.get("pass@100"),
        "generated_samples": summary.get("samples"),
        "generation_failures": summary.get("generation_failures"),
        "generation_seconds": summary.get("generation_seconds"),
        "evaluation_seconds": summary.get("evaluation_seconds"),
        "humaneval_sample_file": summary.get("sample_file"),
        "humaneval_result_file": summary.get("result_file"),
    }


def run_command(
    script: Path,
    cwd: Path,
    log_path: Path,
    timeout_s: float | None,
    env: dict[str, str],
) -> tuple[int | None, float, str | None]:
    start = time.time()
    with log_path.open("w") as log:
        proc = subprocess.Popen(
            ["bash", str(script)],
            cwd=str(cwd),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
        try:
            exit_code = proc.wait(timeout=timeout_s)
            return exit_code, time.time() - start, None
        except subprocess.TimeoutExpired:
            stop_process_tree(proc)
            return proc.poll(), time.time() - start, f"timeout after {timeout_s}s"


def run_job(job: Job, args: argparse.Namespace, summary_csv: Path, summary_jsonl: Path) -> dict[str, object]:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    result_dir = job_result_dir(job)
    result_dir.mkdir(parents=True, exist_ok=True)
    vllm_log = result_dir / "vllm.log"
    humaneval_log = result_dir / "humaneval.log"
    metrics_snapshot = result_dir / "metrics.txt"
    output_dir = humaneval_output_dir(job)

    row: dict[str, object] = {
        "timestamp": stamp,
        "model": job.model,
        "method": job.method,
        "status": "started",
        "vllm_script": str(job.vllm_script),
        "humaneval_script": str(job.humaneval_script),
        "vllm_log": str(vllm_log),
        "humaneval_log": str(humaneval_log),
        "metrics_snapshot": str(metrics_snapshot),
        "humaneval_output_dir": str(output_dir) if output_dir else "",
        "error": "",
    }
    child_env = make_child_env(args.hf_home)

    print(f"\n=== {job.model}/{job.method} ===", flush=True)
    if not args.force:
        completed = load_completed_job(job)
        if completed:
            completed["skipped"] = True
            print("[skip] completed result already exists", flush=True)
            write_model_summary(job.model)
            return completed

    if not args.allow_existing_server and vllm_endpoint_reachable():
        row["status"] = "port_busy"
        row["error"] = (
            f"{VLLM_BASE_URL} is already reachable before starting this job. "
            "Stop the existing vLLM server or pass --allow-existing-server."
        )
        print(f"[fail] {row['error']}", flush=True)
        append_csv(summary_csv, row)
        append_jsonl(summary_jsonl, row)
        write_job_artifacts(job, row)
        write_model_summary(job.model)
        return row

    cleanup_note = maybe_clear_humaneval_output(job, args.fresh_output)
    if cleanup_note:
        print(f"[output] {cleanup_note}", flush=True)

    start = time.time()
    with vllm_log.open("w") as log:
        proc = subprocess.Popen(
            ["bash", str(job.vllm_script)],
            cwd=str(job.vllm_script.parent),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=child_env,
        )

    try:
        ok = wait_for_vllm(proc, args.startup_timeout, args.poll_interval)
        row["startup_seconds"] = round(time.time() - start, 3)
        row["vllm_exit_code"] = proc.poll()
        if not ok:
            row["status"] = "vllm_start_failed"
            row["error"] = "vLLM did not become healthy before timeout, or exited early"
            print(f"[fail] vLLM not healthy: {job.model}/{job.method}", flush=True)
            return row

        print("[ok] vLLM healthy; running HumanEval", flush=True)
        row["grafana_reachable"] = bool(http_get_text(GRAFANA_URL, timeout=3.0))

        humaneval_exit, humaneval_seconds, humaneval_error = run_command(
            job.humaneval_script,
            HUMANEVAL_DIR,
            humaneval_log,
            args.humaneval_timeout,
            child_env,
        )
        row["humaneval_exit_code"] = humaneval_exit
        row["humaneval_seconds"] = round(humaneval_seconds, 3)
        if humaneval_error:
            row["error"] = humaneval_error

        row.update(parse_humaneval_summary(output_dir))
        time.sleep(args.metrics_delay)
        metrics_text = http_get_text(VLLM_METRICS_URL, timeout=10.0)
        if metrics_text:
            metrics_snapshot.write_text(metrics_text)
        else:
            row["error"] = (str(row.get("error") or "") + "; metrics endpoint unavailable").strip("; ")

        row.update(summarize_metrics(metrics_text))
        row["vllm_exit_code"] = proc.poll()
        row["status"] = "ok" if humaneval_exit == 0 else "humaneval_failed"
        if row["status"] == "ok" and row.get("tps") is None:
            row["status"] = "no_metrics"
            row["error"] = (
                str(row.get("error") or "")
                + "; HumanEval finished but vLLM token metrics were empty."
            ).strip("; ")

        print(
            "[result] "
            f"status={row['status']} "
            f"pass@1={row.get('pass@1')} "
            f"tps={row.get('tps')} "
            f"mean_accept_length={row.get('mean_accept_length')}",
            flush=True,
        )
    except Exception as exc:
        row["status"] = "runner_error"
        row["error"] = repr(exc)
        print(f"[error] {job.model}/{job.method}: {exc!r}", flush=True)
    finally:
        stop_process_tree(proc, grace_s=args.stop_grace)
        row["vllm_exit_code"] = proc.poll()
        append_csv(summary_csv, row)
        append_jsonl(summary_jsonl, row)
        write_job_artifacts(job, row)
        write_model_summary(job.model)
        print("[stop] vLLM stopped; moving on", flush=True)
        return row


def parse_csv_filter(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    return {item.strip() for item in raw.split(",") if item.strip()}


def make_child_env(hf_home: str) -> dict[str, str]:
    env = os.environ.copy()
    env["HF_HOME"] = hf_home
    env["HF_HUB_CACHE"] = str(Path(hf_home) / "hub")
    env["TRANSFORMERS_CACHE"] = str(Path(hf_home) / "hub")
    env.setdefault("HF_HUB_OFFLINE", "1")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Run vLLM + HumanEval benchmark sweep.")
    parser.add_argument("--models", help="comma-separated model directory names, without .sh")
    parser.add_argument(
        "--methods",
        help="comma-separated methods: autoregressive,ngram,suffix,eagle3,mlp",
    )
    parser.add_argument("--startup-timeout", type=float, default=900.0)
    parser.add_argument("--humaneval-timeout", type=float, default=None)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--metrics-delay", type=float, default=5.0)
    parser.add_argument("--stop-grace", type=float, default=30.0)
    parser.add_argument("--hf-home", default=DEFAULT_HF_HOME)
    parser.add_argument(
        "--force",
        action="store_true",
        help="rerun jobs even if human-eval/results/<model>/<method>/result.json is complete",
    )
    parser.add_argument(
        "--fresh-output",
        action="store_true",
        help="remove the matching human-eval/out/<model>/<method> directory before each job",
    )
    parser.add_argument(
        "--allow-existing-server",
        action="store_true",
        help="do not fail if localhost:8081 is reachable before starting a job",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_csv = RESULTS_DIR / "humaneval_vllm_sweep.csv"
    summary_jsonl = RESULTS_DIR / "humaneval_vllm_sweep.jsonl"
    summary_md = RESULTS_DIR / "humaneval_vllm_sweep.md"

    jobs = discover_jobs(parse_csv_filter(args.models), parse_csv_filter(args.methods))
    if not jobs:
        print("No matching jobs found.", file=sys.stderr)
        return 1

    print(f"Discovered {len(jobs)} jobs:")
    for job in jobs:
        print(f"  {job.model}/{job.method}: {job.vllm_script.name} -> {job.humaneval_script}")

    if args.dry_run:
        return 0

    rows: list[dict[str, object]] = []
    for job in jobs:
        rows.append(run_job(job, args, summary_csv, summary_jsonl))
        write_markdown(summary_md, rows)

    print(f"\nSummary CSV:  {summary_csv}")
    print(f"Summary JSON: {summary_jsonl}")
    print(f"Summary MD:   {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
