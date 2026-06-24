# MT-Bench vLLM Sweep

`run_mtbench_sweep.py` mirrors `vllm/canitedit/run_canitedit_sweep.py` for MT-Bench.
It discovers `vllm/scripts/<model>.sh/*.sh`, starts each vLLM server, reads the
served model id from `http://localhost:8081/v1/models`, generates FastChat
MT-Bench answers through `gen_api_answer.py`, optionally runs `gen_judgment.py`,
captures `/metrics`, then writes CSV/JSONL/Markdown summaries under
`vllm/mtbench/results`.

Examples:

```bash
python3 vllm/mtbench/run_mtbench_sweep.py --dry-run
python3 vllm/mtbench/run_mtbench_sweep.py --models L31-8B-I --methods autoregressive --skip-judgment --fresh-output
python3 vllm/mtbench/run_mtbench_sweep.py --models Qwen3-32B --methods autoregressive,ngram,suffix,eagle3 --fresh-output
```

Judging uses FastChat's default single-answer MT-Bench flow and writes to
`FastChat/fastchat/llm_judge/data/mt_bench/model_judgment/<judge>_single.jsonl`.
Pass `--skip-judgment` when you only need answer-generation throughput and
speculative-decoding metrics, or when the judge API key is not configured.

For Qwen3 served model ids, the runner passes
`--chat-template-kwargs '{"enable_thinking": false}'` to FastChat answer
generation by default, so `Qwen/Qwen3-32B` and related speculative variants run
with thinking mode disabled. Use `--no-disable-qwen-thinking` to turn off this
automatic behavior, or `--chat-template-kwargs` to provide an explicit JSON
object for all answer-generation requests.
