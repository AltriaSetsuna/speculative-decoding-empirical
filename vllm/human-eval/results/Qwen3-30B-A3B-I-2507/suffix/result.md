# HumanEval vLLM Sweep Results

Generated at: `2026-06-14 16:00:09`

Metrics use the same global vLLM formulas as the CanItEdit sweep:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## Qwen3-30B-A3B-I-2507

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| suffix | 0.96 | 79.96 |  | 0.91 | 0.38 | 0.46 | 0.52 | 0.62 | 0.77 | 0.76 | 0.90 | 0.84 | 0.95 | 0.93 | 0.97 | 0.87 |
