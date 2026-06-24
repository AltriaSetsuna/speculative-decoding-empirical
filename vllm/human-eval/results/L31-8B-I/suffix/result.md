# HumanEval vLLM Sweep Results

Generated at: `2026-06-22 08:24:10`

Metrics use the same global vLLM formulas as the CanItEdit sweep:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## L31-8B-I

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| suffix | 0.68 | 131.72 |  | 1.13 | 0.46 | 0.51 | 0.52 | 0.61 | 0.73 | 0.73 | 0.85 | 0.79 | 0.94 | 0.92 | 0.97 | 0.86 |
