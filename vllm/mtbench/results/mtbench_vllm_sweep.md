# MT-Bench vLLM Sweep Results

Generated at: `2026-06-23 01:48:05`

Metrics use the same global formulas as the Grafana dashboard:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## Qwen3-30B-A3B-I-2507

| method | score | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive |  | 77.34 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram |  | 65.69 | 0.85 | 1.82 | 0.60 | 0.71 | 0.76 | 0.80 | 0.81 |  |  |  |  |  |  |  |
| suffix |  | 57.19 | 0.74 | 0.40 | 0.24 | 0.31 | 0.40 | 0.48 | 0.75 | 0.62 | 0.82 | 0.69 | 0.88 | 0.87 | 0.95 | 0.80 |
| eagle3_RedHatAI |  | 50.66 | 0.66 | 1.27 | 0.61 | 0.64 | 0.68 |  |  |  |  |  |  |  |  |  |


## Qwen3-32B

| method | score | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive |  | 37.01 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram |  | 37.00 | 1.00 | 1.72 | 0.60 | 0.68 | 0.73 | 0.78 | 0.77 |  |  |  |  |  |  |  |
| suffix |  | 39.81 | 1.08 | 0.44 | 0.27 | 0.31 | 0.39 | 0.47 | 0.65 | 0.58 | 0.84 | 0.64 | 0.88 | 0.81 | 0.94 | 0.70 |
| eagle3_RedHatAI |  | 63.47 | 1.71 | 1.56 | 0.71 | 0.71 | 0.68 |  |  |  |  |  |  |  |  |  |
