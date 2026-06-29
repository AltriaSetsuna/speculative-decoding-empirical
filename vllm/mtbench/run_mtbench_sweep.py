#!/usr/bin/env python3
"""
Run vLLM deployment scripts one by one, generate MT-Bench answers through
FastChat's OpenAI-compatible API path, optionally run LLM-as-a-judge, collect
vLLM speculative-decoding metrics, and stop the vLLM server before the next run.

The script pairs discovered vLLM scripts:
  vllm/scripts/<model>.sh/<method-ish>.sh
with FastChat's MT-Bench data and tools under:
  FastChat/fastchat/llm_judge

Unlike the historical FastChat spec_scripts in this repository, this runner
reads the served model name from the live vLLM /v1/models endpoint. That keeps
answer generation aligned with whatever CUSTOM_NAME the launch script used.
"""

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
FASTCHAT_DIR = ROOT / "FastChat"
LLM_JUDGE_DIR = FASTCHAT_DIR / "fastchat" / "llm_judge"
RESULTS_DIR = ROOT / "vllm" / "mtbench" / "results"
DEFAULT_HF_HOME = "/nasdata/yijiali/.cache/huggingface"
DEFAULT_FASTCHAT_PYTHON = FASTCHAT_DIR / ".venv" / "bin" / "python"

VLLM_BASE_URL = "http://localhost:8081"
VLLM_MODELS_URL = f"{VLLM_BASE_URL}/v1/models"
VLLM_METRICS_URL = f"{VLLM_BASE_URL}/metrics"
GRAFANA_URL = "http://localhost:3000/"


@dataclass(frozen=True)
class Job:
    model: str
    method: str
    vllm_script: Path


METHOD_ORDER = {
    "autoregressive": 0,
    "ngram": 1,
    "suffix": 2,
    "eagle3": 3,
    "mlp": 4,
}
METHOD_SEQUENCE = ["autoregressive", "ngram", "suffix", "eagle3", "mlp"]


MetricKey = Tuple[str, Tuple[Tuple[str, str], ...]]


def method_supported(model: str, method: str) -> bool:
    return method != "mlp" or model == "L31-70B-I"


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
            if not method_supported(model, method):
                continue
            if methods and method not in methods:
                continue
            jobs.append(Job(model, method, vllm_script))
    return jobs


def http_get_text(url: str, timeout: float = 5.0) -> str | None:
    try:
        req = Request(url, headers={"User-Agent": "mtbench-vllm-sweep/1.0"})
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


def parse_csv_filter(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    return {item.strip() for item in raw.split(",") if item.strip()}


def make_child_env(hf_home: str) -> dict[str, str]:
    env = os.environ.copy()
    env["HF_HOME"] = hf_home
    env["HF_HUB_CACHE"] = str(Path(hf_home) / "hub")
    env["TRANSFORMERS_CACHE"] = str(Path(hf_home) / "hub")
    env["PYTHONPATH"] = (
        str(FASTCHAT_DIR)
        if not env.get("PYTHONPATH")
        else f"{FASTCHAT_DIR}{os.pathsep}{env['PYTHONPATH']}"
    )
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("OPENAI_API_KEY", "EMPTY")
    return env


def check_python_modules(python_bin: str, modules: list[str], env: dict[str, str]) -> list[str]:
    missing: list[str] = []
    for module in modules:
        proc = subprocess.run(
            [python_bin, "-c", f"import {module}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        if proc.returncode != 0:
            missing.append(module)
    return missing


def required_python_modules(skip_judgment: bool) -> list[str]:
    modules = ["anthropic", "openai", "shortuuid", "torch", "tqdm", "transformers"]
    if not skip_judgment:
        modules.extend(["numpy"])
    return modules


def served_model_id() -> str | None:
    raw = http_get_text(VLLM_MODELS_URL, timeout=5.0)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    model_id = first.get("id")
    return str(model_id) if model_id else None


def answer_model_id(job: Job, api_model: str) -> str:
    return f"{job.model}__{job.method}"


def should_disable_qwen_thinking(model_name: str) -> bool:
    return "qwen3" in model_name.lower()


def answer_file_for(model_id: str) -> Path:
    return LLM_JUDGE_DIR / "data" / "mt_bench" / "model_answer" / f"{model_id}.jsonl"


def judgment_file(judge_model: str) -> Path:
    return LLM_JUDGE_DIR / "data" / "mt_bench" / "model_judgment" / f"{judge_model}_single.jsonl"


def question_count(bench_name: str = "mt_bench") -> int:
    path = LLM_JUDGE_DIR / "data" / bench_name / "question.jsonl"
    try:
        return sum(1 for line in path.read_text().splitlines() if line.strip())
    except OSError:
        return 0


def parse_answer_summary(answer_file: Path) -> dict[str, object]:
    if not answer_file.exists():
        return {}
    num_answers = 0
    total_turns = 0
    total_chars = 0
    total_errors = 0
    try:
        with answer_file.open() as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                num_answers += 1
                choices = data.get("choices")
                if not isinstance(choices, list):
                    continue
                for choice in choices:
                    if not isinstance(choice, dict):
                        continue
                    turns = choice.get("turns")
                    if not isinstance(turns, list):
                        continue
                    total_turns += len(turns)
                    for turn in turns:
                        text = "" if turn is None else str(turn)
                        total_chars += len(text)
                        if text == "$ERROR$":
                            total_errors += 1
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        "mtbench_answers": num_answers,
        "mtbench_total_turns": total_turns,
        "mtbench_total_chars": total_chars,
        "mtbench_error_turns": total_errors,
        "mtbench_expected_questions": question_count(),
    }


def parse_judgment_summary(path: Path, model_id: str) -> dict[str, object]:
    if not path.exists():
        return {}
    scores: list[float] = []
    turn_1: list[float] = []
    turn_2: list[float] = []
    judged = 0
    invalid = 0
    try:
        with path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("model") != model_id:
                    continue
                judged += 1
                score = data.get("score")
                try:
                    score_float = float(score)
                except (TypeError, ValueError):
                    invalid += 1
                    continue
                if score_float == -1:
                    invalid += 1
                    continue
                scores.append(score_float)
                if data.get("turn") == 1:
                    turn_1.append(score_float)
                elif data.get("turn") == 2:
                    turn_2.append(score_float)
    except (OSError, json.JSONDecodeError):
        return {}

    def mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    return {
        "mtbench_score": mean(scores),
        "mtbench_turn1_score": mean(turn_1),
        "mtbench_turn2_score": mean(turn_2),
        "mtbench_judgments": judged,
        "mtbench_valid_judgments": len(scores),
        "mtbench_invalid_judgments": invalid,
    }


def run_command(
    command: list[str],
    cwd: Path,
    log_path: Path,
    timeout_s: float | None,
    env: dict[str, str],
    input_text: str | None = None,
) -> tuple[int | None, float, str | None]:
    start = time.time()
    stdin = subprocess.PIPE if input_text is not None else subprocess.DEVNULL
    with log_path.open("w") as log:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=stdin,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
            env=env,
        )
        try:
            proc.communicate(input=input_text, timeout=timeout_s)
            return proc.returncode, time.time() - start, None
        except subprocess.TimeoutExpired:
            stop_process_tree(proc)
            return proc.poll(), time.time() - start, f"timeout after {timeout_s}s"


def run_answer_generation(
    api_model: str,
    answer_file: Path,
    args: argparse.Namespace,
    log_path: Path,
    env: dict[str, str],
) -> tuple[int | None, float, str | None]:
    answer_file.parent.mkdir(parents=True, exist_ok=True)
    if args.fresh_output and answer_file.exists():
        answer_file.unlink()
    command = [
        args.python,
        str(LLM_JUDGE_DIR / "gen_api_answer.py"),
        "--model",
        api_model,
        "--answer-file",
        str(answer_file),
        "--openai-api-base",
        f"{VLLM_BASE_URL}/v1",
        "--parallel",
        str(args.parallel),
        "--force-temperature",
        str(args.force_temperature),
        "--max-tokens",
        str(args.max_tokens),
    ]
    if args.question_begin is not None:
        command.extend(["--question-begin", str(args.question_begin)])
    if args.question_end is not None:
        command.extend(["--question-end", str(args.question_end)])
    chat_template_kwargs = None
    if args.chat_template_kwargs:
        chat_template_kwargs = args.chat_template_kwargs
    elif args.disable_qwen_thinking and should_disable_qwen_thinking(api_model):
        chat_template_kwargs = '{"enable_thinking": false}'
    if chat_template_kwargs:
        command.extend(["--chat-template-kwargs", chat_template_kwargs])
    return run_command(command, LLM_JUDGE_DIR, log_path, args.answer_timeout, env)


def run_judgment(
    model_id: str,
    args: argparse.Namespace,
    log_path: Path,
    env: dict[str, str],
) -> tuple[int | None, float, str | None]:
    path = judgment_file(args.judge_model)
    if args.fresh_judgment and path.exists():
        path.unlink()
    command = [
        args.python,
        str(LLM_JUDGE_DIR / "gen_judgment.py"),
        "--bench-name",
        "mt_bench",
        "--judge-file",
        "data/judge_prompts.jsonl",
        "--judge-model",
        args.judge_model,
        "--mode",
        "single",
        "--model-list",
        model_id,
        "--parallel",
        str(args.judge_parallel),
    ]
    if args.first_n_judgments is not None:
        command.extend(["--first-n", str(args.first_n_judgments)])
    return run_command(command, LLM_JUDGE_DIR, log_path, args.judge_timeout, env, input_text="\n")


def row_sort_key(row: dict[str, object]) -> tuple[str, int, str]:
    method = str(row.get("method") or "")
    return (
        str(row.get("model") or ""),
        METHOD_ORDER.get(method, 100),
        method,
    )


def metric_headers() -> list[str]:
    return ["score", "tps", "speedup", "mal"] + [f"{idx}-alpha" for idx in range(12)]


def is_completed(row: dict[str, object]) -> bool:
    if row.get("status") != "ok":
        return False
    if row.get("answer_exit_code") != 0:
        return False
    try:
        return row.get("tps") is not None and float(row["tps"]) > 0
    except (TypeError, ValueError):
        return False


def completed_tps(row: dict[str, object] | None) -> float | None:
    if row is None or not is_completed(row):
        return None
    try:
        return float(row["tps"])
    except (TypeError, ValueError):
        return None


def row_speedup(row: dict[str, object], baseline_tps: float | None) -> float | None:
    try:
        tps = float(row["tps"])
    except (KeyError, TypeError, ValueError):
        return None
    return safe_div(tps, baseline_tps)


def method_label(row: dict[str, object]) -> str:
    method = str(row.get("method") or "")
    script_name = Path(str(row.get("vllm_script") or "")).stem
    if method == "eagle3":
        return script_name
    return method


def render_markdown_tables(rows: list[dict[str, object]]) -> str:
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# MT-Bench vLLM Sweep Results",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "Metrics use the same global formulas as the Grafana dashboard:",
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
        for row in model_rows:
            if row.get("method") == "autoregressive":
                baseline_tps = completed_tps(row)
                break

        lines.extend([f"## {model}", "", "| " + " | ".join(headers) + " |"])
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in model_rows:
            cells = [
                method_label(row),
                format_number(row.get("mtbench_score")),
                format_number(row.get("tps")),
                format_number(row_speedup(row, baseline_tps)),
                format_number(row.get("mean_accept_length")),
            ]
            cells.extend(format_number(row.get(f"n_alpha_{idx}")) for idx in range(12))
            if row.get("status") != "ok":
                cells[1] = str(row.get("status") or "")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)


def render_fixed_model_table(model: str, rows_by_method: dict[str, dict[str, object]]) -> str:
    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    headers = ["method"] + metric_headers()
    baseline_tps = completed_tps(rows_by_method.get("autoregressive"))
    lines = [
        f"# {model}",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for method in METHOD_SEQUENCE:
        if not method_supported(model, method):
            continue
        row = rows_by_method.get(method)
        cells = [method]
        if row is not None and is_completed(row):
            cells.extend(
                [
                    format_number(row.get("mtbench_score")),
                    format_number(row.get("tps")),
                    format_number(row_speedup(row, baseline_tps)),
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


def load_result_json(path: Path) -> dict[str, object] | None:
    try:
        row = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return row if isinstance(row, dict) else None


def load_completed_job(job: Job) -> dict[str, object] | None:
    row = load_result_json(job_completed_path(job))
    if row is not None and is_completed(row):
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
        if not method_supported(model, method):
            continue
        row = load_result_json(RESULTS_DIR / model / method / "result.json")
        if row is not None:
            rows[method] = row
    return rows


def load_all_result_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(RESULTS_DIR.glob("*/*/result.json")):
        model = path.parent.parent.name
        method = path.parent.name
        if not method_supported(model, method):
            continue
        row = load_result_json(path)
        if row is not None:
            rows.append(row)
    return sorted(rows, key=row_sort_key)


def write_model_summary(model: str) -> None:
    model_dir = RESULTS_DIR / model
    model_dir.mkdir(parents=True, exist_ok=True)
    rows_by_method = load_model_rows(model)
    (model_dir / f"{model}.md").write_text(render_fixed_model_table(model, rows_by_method))


def refresh_markdown_artifacts(summary_md: Path) -> list[dict[str, object]]:
    rows = load_all_result_rows()
    models: set[str] = set()
    for row in rows:
        model = str(row.get("model") or "")
        method = str(row.get("method") or "")
        if not model or not method_supported(model, method):
            continue
        result_dir = RESULTS_DIR / model / method
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / "result.md").write_text(render_markdown_tables([row]))
        models.add(model)
    for model in sorted(models):
        write_model_summary(model)
    summary_md.write_text(render_markdown_tables(rows))
    return rows


def append_csv(path: Path, row: dict[str, object]) -> None:
    fieldnames = [
        "timestamp",
        "model",
        "method",
        "status",
        "vllm_script",
        "api_model",
        "answer_model_id",
        "vllm_exit_code",
        "answer_exit_code",
        "judge_exit_code",
        "startup_seconds",
        "answer_seconds",
        "judge_seconds",
        "grafana_reachable",
        "mtbench_score",
        "mtbench_turn1_score",
        "mtbench_turn2_score",
        "mtbench_judgments",
        "mtbench_valid_judgments",
        "mtbench_invalid_judgments",
        "mtbench_answers",
        "mtbench_total_turns",
        "mtbench_total_chars",
        "mtbench_error_turns",
        "mtbench_expected_questions",
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
        "answer_log",
        "judge_log",
        "metrics_snapshot",
        "answer_file",
        "judgment_file",
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


def append_error(row: dict[str, object], message: str | None) -> None:
    if not message:
        return
    row["error"] = (str(row.get("error") or "") + f"; {message}").strip("; ")


def run_job(job: Job, args: argparse.Namespace, summary_csv: Path, summary_jsonl: Path) -> dict[str, object]:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    result_dir = job_result_dir(job)
    result_dir.mkdir(parents=True, exist_ok=True)
    vllm_log = result_dir / "vllm.log"
    answer_log = result_dir / "answer.log"
    judge_log = result_dir / "judge.log"
    metrics_snapshot = result_dir / "metrics.txt"

    row: dict[str, object] = {
        "timestamp": stamp,
        "model": job.model,
        "method": job.method,
        "status": "started",
        "vllm_script": str(job.vllm_script),
        "vllm_log": str(vllm_log),
        "answer_log": str(answer_log),
        "judge_log": str(judge_log),
        "metrics_snapshot": str(metrics_snapshot),
        "error": "",
    }
    child_env = make_child_env(args.hf_home)

    print(f"\n=== {job.model}/{job.method} ===", flush=True)

    if not args.force:
        completed = load_completed_job(job)
        if completed:
            answer_file = Path(str(completed.get("answer_file") or ""))
            judge_path = Path(str(completed.get("judgment_file") or ""))
            completed.update(parse_answer_summary(answer_file))
            completed.update(parse_judgment_summary(judge_path, str(completed.get("answer_model_id") or "")))
            completed["skipped"] = True
            print("[skip] completed result already exists", flush=True)
            write_job_artifacts(job, completed)
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

        api_model = served_model_id()
        if not api_model:
            row["status"] = "vllm_model_missing"
            row["error"] = "vLLM is healthy but /v1/models did not return a model id"
            print(f"[fail] {row['error']}", flush=True)
            return row

        answer_id = answer_model_id(job, api_model)
        answer_path = answer_file_for(answer_id)
        judge_path = judgment_file(args.judge_model)
        row.update(
            {
                "api_model": api_model,
                "answer_model_id": answer_id,
                "answer_file": str(answer_path),
                "judgment_file": str(judge_path),
            }
        )

        print(f"[ok] vLLM healthy; generating MT-Bench answers as {answer_id}", flush=True)
        row["grafana_reachable"] = bool(http_get_text(GRAFANA_URL, timeout=3.0))

        answer_exit, answer_seconds, answer_error = run_answer_generation(
            api_model, answer_path, args, answer_log, child_env
        )
        row["answer_exit_code"] = answer_exit
        row["answer_seconds"] = round(answer_seconds, 3)
        append_error(row, answer_error)
        row.update(parse_answer_summary(answer_path))

        if answer_exit == 0 and not args.skip_judgment:
            judge_exit, judge_seconds, judge_error = run_judgment(
                answer_id, args, judge_log, child_env
            )
            row["judge_exit_code"] = judge_exit
            row["judge_seconds"] = round(judge_seconds, 3)
            append_error(row, judge_error)
            row.update(parse_judgment_summary(judge_path, answer_id))
        else:
            row["judge_exit_code"] = None
            row["judge_seconds"] = 0.0
            if args.skip_judgment:
                append_error(row, "judgment skipped")

        time.sleep(args.metrics_delay)
        metrics_text = http_get_text(VLLM_METRICS_URL, timeout=10.0)
        if metrics_text:
            metrics_snapshot.write_text(metrics_text)
        else:
            append_error(row, "metrics endpoint unavailable")

        row.update(summarize_metrics(metrics_text))
        row["vllm_exit_code"] = proc.poll()
        row["status"] = "ok" if answer_exit == 0 else "answer_failed"
        if answer_exit == 0 and not args.skip_judgment and row.get("judge_exit_code") != 0:
            row["status"] = "judge_failed"
        if row["status"] == "ok" and row.get("tps") is None:
            row["status"] = "no_metrics"
            append_error(
                row,
                "MT-Bench finished but vLLM token metrics were empty. "
                "Most likely the answer file already existed and requests were skipped.",
            )

        print(
            "[result] "
            f"status={row['status']} "
            f"score={row.get('mtbench_score')} "
            f"answers={row.get('mtbench_answers')} "
            f"tps={row.get('tps')} "
            f"mean_accept_length={row.get('mean_accept_length')} "
            f"n_alpha={row.get('n_alpha')}",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run vLLM + MT-Bench benchmark sweep.")
    parser.add_argument("--models", help="comma-separated model directory names, without .sh")
    parser.add_argument(
        "--methods",
        help="comma-separated methods: autoregressive,ngram,suffix,eagle3,mlp",
    )
    parser.add_argument("--startup-timeout", type=float, default=900.0)
    parser.add_argument("--answer-timeout", type=float, default=None)
    parser.add_argument("--judge-timeout", type=float, default=None)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--metrics-delay", type=float, default=5.0)
    parser.add_argument("--stop-grace", type=float, default=30.0)
    parser.add_argument("--hf-home", default=DEFAULT_HF_HOME)
    parser.add_argument(
        "--python",
        default=str(DEFAULT_FASTCHAT_PYTHON),
        help="Python interpreter used for FastChat answer generation and judging",
    )
    parser.add_argument("--parallel", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--force-temperature", type=float, default=0.0)
    parser.add_argument(
        "--disable-qwen-thinking",
        dest="disable_qwen_thinking",
        action="store_true",
        default=True,
        help="send chat_template_kwargs={\"enable_thinking\": false} for Qwen3 served models",
    )
    parser.add_argument(
        "--no-disable-qwen-thinking",
        dest="disable_qwen_thinking",
        action="store_false",
        help="do not add Qwen3 chat_template_kwargs automatically",
    )
    parser.add_argument(
        "--chat-template-kwargs",
        help="JSON object forwarded to every answer-generation request",
    )
    parser.add_argument("--question-begin", type=int)
    parser.add_argument("--question-end", type=int)
    parser.add_argument("--judge-model", default="gpt-4")
    parser.add_argument("--judge-parallel", type=int, default=1)
    parser.add_argument("--first-n-judgments", type=int)
    parser.add_argument(
        "--skip-judgment",
        action="store_true",
        default=True,
        help="only generate MT-Bench answers and vLLM metrics; do not call the judge model",
    )
    parser.add_argument(
        "--fresh-judgment",
        action="store_true",
        help="remove the judge output file before judging this job",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rerun jobs even if vllm/mtbench/results/<model>/<method>/result.json is complete",
    )
    parser.add_argument(
        "--fresh-output",
        action="store_true",
        help="remove the matching FastChat model_answer file before each job",
    )
    parser.add_argument(
        "--allow-existing-server",
        action="store_true",
        help="do not fail if localhost:8081 is reachable before starting a job",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_csv = RESULTS_DIR / "mtbench_vllm_sweep.csv"
    summary_jsonl = RESULTS_DIR / "mtbench_vllm_sweep.jsonl"
    summary_md = RESULTS_DIR / "mtbench_vllm_sweep.md"

    jobs = discover_jobs(parse_csv_filter(args.models), parse_csv_filter(args.methods))
    if not jobs:
        print("No matching jobs found.", file=sys.stderr)
        return 1

    print(f"Discovered {len(jobs)} jobs:")
    for job in jobs:
        print(f"  {job.model}/{job.method}: {job.vllm_script.name}")

    if args.dry_run:
        return 0

    child_env = make_child_env(args.hf_home)
    missing = check_python_modules(
        args.python, required_python_modules(args.skip_judgment), child_env
    )
    if missing:
        print(
            "FastChat MT-Bench dependencies are missing from "
            f"{args.python}: {', '.join(missing)}",
            file=sys.stderr,
        )
        print(
            'Install them in that environment, for example: pip install -e "FastChat[llm_judge]"',
            file=sys.stderr,
        )
        return 1

    refresh_markdown_artifacts(summary_md)
    for job in jobs:
        run_job(job, args, summary_csv, summary_jsonl)
        refresh_markdown_artifacts(summary_md)

    print(f"\nSummary CSV:  {summary_csv}")
    print(f"Summary JSON: {summary_jsonl}")
    print(f"Summary MD:   {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
