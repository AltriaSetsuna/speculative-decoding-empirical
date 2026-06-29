#!/usr/bin/env -S uv run --script
# /// script
# requires-python = "==3.12.*"
# dependencies = [
#     "fire",
#     "litellm>=1.75.9",
#     "numpy",
#     "tqdm",
# ]
# ///
"""Generate HumanEval samples from an OpenAI-compatible endpoint and score them."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from litellm import completion

from human_eval.data import HUMAN_EVAL, read_problems, write_jsonl
from human_eval.evaluation import evaluate_functional_correctness


DEFAULT_API_BASE = "http://localhost:8081/v1"


CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)


def request_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 120.0) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', 'EMPTY')}",
            "Content-Type": "application/json",
            "User-Agent": "humaneval-vllm-runner/1.0",
        },
        method="GET" if payload is None else "POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def discover_model(api_base: str) -> str:
    body = request_json(f"{api_base.rstrip('/')}/models", timeout=10.0)
    models = body.get("data") or []
    if not models:
        raise RuntimeError(f"no models returned by {api_base}/models")
    model_id = models[0].get("id")
    if not model_id:
        raise RuntimeError(f"first model entry has no id: {models[0]!r}")
    return str(model_id)


def complete_prompt(
    api_base: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    timeout: float,
) -> str:
    response = completion(
        model=model,
        api_base=api_base,
        api_key=os.environ.get("OPENAI_API_KEY", "EMPTY"),
        custom_llm_provider="openai",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        timeout=timeout,
        n=1,
        stream=False,
        chat_template_kwargs={"enable_thinking": False},
    )
    choices = response.choices or []
    if not choices:
        raise RuntimeError(f"completion response has no choices: {response!r}")
    return str(choices[0].message.content or "")


def extract_code(completion: str, entry_point: str) -> str:
    """Extract Python from common chat-model Markdown responses."""
    blocks = CODE_BLOCK_RE.findall(completion)
    if blocks:
        for block in blocks:
            if re.search(rf"^\s*def\s+{re.escape(entry_point)}\s*\(", block, re.MULTILINE):
                return block.strip("\n")
        return blocks[0].strip("\n")
    return completion.strip("\n")


def normalize_completion(completion: str, entry_point: str) -> str:
    """Convert chat/instruct output into the function-body continuation HumanEval expects."""
    code = extract_code(completion, entry_point)
    try:
        module = ast.parse(code)
    except SyntaxError:
        return code.rstrip() + "\n"

    lines = code.splitlines()
    prelude_imports: list[str] = []

    def is_string_expr(node: ast.AST) -> bool:
        value = getattr(node, "value", None)
        if not isinstance(node, ast.Expr):
            return False
        return (
            isinstance(value, ast.Str)
            or (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            )
        )

    def last_lineno(node: ast.AST) -> int:
        end_lineno = getattr(node, "end_lineno", None)
        if end_lineno is not None:
            return end_lineno
        return max(getattr(child, "lineno", getattr(node, "lineno", 1)) for child in ast.walk(node))

    for node in module.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            stop = last_lineno(node)
            prelude_imports.extend(lines[node.lineno - 1 : stop])
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry_point:
            body_nodes = node.body
            if body_nodes and is_string_expr(body_nodes[0]):
                body_nodes = body_nodes[1:]
            start = body_nodes[0].lineno - 1 if body_nodes else node.lineno
            stop = last_lineno(body_nodes[-1]) if body_nodes else node.lineno
            body_lines = textwrap.dedent("\n".join(lines[start:stop])).splitlines()
            body = "\n".join([*prelude_imports, *body_lines])
            return textwrap.indent(textwrap.dedent(body).rstrip() + "\n", "    ")

    return code.rstrip() + "\n"


def generate_samples(args: argparse.Namespace, sample_path: Path) -> dict[str, Any]:
    problems = read_problems(args.problem_file)
    model = args.model or discover_model(args.api_base)
    samples = []
    started = time.time()
    failures = 0
    total_samples = len(problems) * args.num_samples_per_task
    completed = 0

    def generate_one(task_id: str, problem: dict[str, Any]) -> dict[str, str]:
        completion = complete_prompt(
            args.api_base,
            model,
            problem["prompt"],
            args.max_tokens,
            args.temperature,
            args.top_p,
            args.request_timeout,
        )
        normalized_completion = normalize_completion(completion, problem["entry_point"])
        return {
            "task_id": task_id,
            "completion": normalized_completion,
            "raw_completion": completion,
        }

    with ThreadPoolExecutor(max_workers=args.batch_size) as executor:
        futures = [
            executor.submit(generate_one, task_id, problem)
            for task_id, problem in problems.items()
            for _ in range(args.num_samples_per_task)
        ]
        for future in as_completed(futures):
            try:
                sample = future.result()
            except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
                failures += 1
                if failures > args.max_failures:
                    raise RuntimeError(f"too many generation failures; latest: {exc!r}") from exc
                sample = {"task_id": "", "completion": ""}
                print(f"[warn] generation failed: {exc!r}", flush=True)

            if sample["task_id"]:
                samples.append(sample)
            completed += 1
            if completed % args.progress_every == 0 or completed == total_samples:
                print(f"[generate] {completed}/{total_samples} samples", flush=True)

    write_jsonl(str(sample_path), samples)
    seconds = time.time() - started
    return {
        "model": model,
        "tasks": len(problems),
        "samples": len(samples),
        "generation_failures": failures,
        "generation_seconds": seconds,
        "samples_per_second": len(samples) / seconds if seconds > 0 else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and evaluate HumanEval completions.")
    parser.add_argument("--api-base", default=os.environ.get("OPENAI_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--model", default=os.environ.get("HUMANEVAL_MODEL"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--problem-file", default=HUMAN_EVAL)
    parser.add_argument("--num-samples-per-task", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--request-timeout", type=float, default=120.0)
    parser.add_argument("--max-failures", type=int, default=0)
    parser.add_argument("--k", default="1")
    parser.add_argument("--n-workers", type=int, default=4)
    parser.add_argument("--eval-timeout", type=float, default=3.0)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--skip-eval", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_path = output_dir / "samples.jsonl"
    summary_path = output_dir / "summary.json"

    generation = generate_samples(args, sample_path)
    pass_at_k: dict[str, float] = {}
    eval_seconds = None
    if not args.skip_eval:
        started = time.time()
        ks = [int(item.strip()) for item in args.k.split(",") if item.strip()]
        pass_at_k = evaluate_functional_correctness(
            str(sample_path),
            ks,
            args.n_workers,
            args.eval_timeout,
            args.problem_file,
        )
        eval_seconds = time.time() - started

    summary = {
        **generation,
        "pass_at_k": pass_at_k,
        "evaluation_seconds": eval_seconds,
        "sample_file": str(sample_path),
        "result_file": str(sample_path) + "_results.jsonl",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
