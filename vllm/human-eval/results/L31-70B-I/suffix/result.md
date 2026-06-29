# HumanEval vLLM Sweep Results

Generated at: `2026-06-22 08:24:10`

Metrics use the same global vLLM formulas as the CanItEdit sweep:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## L31-70B-I

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| suffix | 0.71 | 23.97 |  | 1.00 | 0.45 | 0.49 | 0.48 | 0.57 | 0.67 | 0.66 | 0.80 | 0.73 | 0.91 | 0.86 | 0.93 | 0.82 |
