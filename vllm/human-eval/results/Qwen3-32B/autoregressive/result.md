# HumanEval vLLM Sweep Results

Generated at: `2026-06-22 08:24:10`

Metrics use the same global vLLM formulas as the CanItEdit sweep:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## Qwen3-32B

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.84 | 38.34 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
