# CanItEdit vLLM Sweep Results

Generated at: `2026-06-15 10:46:24`

Metrics use the same global formulas as the Grafana dashboard:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## L31-70B-I

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.53 | 20.36 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.60 | 34.89 | 1.71 | 4.05 | 0.90 | 0.94 | 0.95 | 0.96 | 0.97 |  |  |  |  |  |  |  |
| suffix | 0.60 | 40.47 | 1.99 | 3.93 | 0.61 | 0.75 | 0.83 | 0.87 | 0.95 | 0.93 | 0.96 | 0.92 | 0.98 | 0.97 | 0.98 | 0.95 |
| eagle3_ST | 0.57 | 26.36 | 1.29 | 1.09 | 0.57 | 0.58 | 0.58 |  |  |  |  |  |  |  |  |  |
| mlp | 0.54 | 20.91 | 1.03 |  |  |  |  |  |  |  |  |  |  |  |  |  |

## L31-8B-I

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.43 | 78.89 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.44 | 161.74 | 2.05 | 4.01 | 0.89 | 0.93 | 0.95 | 0.96 | 0.96 |  |  |  |  |  |  |  |
| suffix | 0.45 | 228.63 | 2.90 | 3.54 | 0.58 | 0.73 | 0.82 | 0.85 | 0.95 | 0.93 | 0.97 | 0.91 | 0.98 | 0.97 | 0.98 | 0.95 |
| eagle3_RedHatAI | 0.45 | 166.95 | 2.12 | 2.18 | 0.85 | 0.85 | 0.85 |  |  |  |  |  |  |  |  |  |

## Qwen3-30B-A3B-I-2507

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.54 | 80.20 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.55 | 124.21 | 1.55 | 3.83 | 0.87 | 0.91 | 0.94 | 0.95 | 0.96 |  |  |  |  |  |  |  |
| suffix | 0.54 | 146.62 | 1.83 | 2.93 | 0.54 | 0.71 | 0.77 | 0.84 | 0.93 | 0.89 | 0.96 | 0.92 | 0.97 | 0.96 | 0.98 | 0.91 |
| eagle3_RedHatAI | 0.54 | 82.64 | 1.03 | 3.00 | 0.86 | 0.84 | 0.81 | 0.80 | 0.80 |  |  |  |  |  |  |  |

## Qwen3-32B

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.58 | 37.09 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.61 | 82.77 | 2.23 | 4.07 | 0.90 | 0.94 | 0.95 | 0.96 | 0.97 |  |  |  |  |  |  |  |
| suffix | 0.60 | 113.21 | 3.05 | 4.11 | 0.62 | 0.76 | 0.85 | 0.87 | 0.95 | 0.94 | 0.97 | 0.92 | 0.98 | 0.97 | 0.98 | 0.96 |
| eagle3_RedHatAI | 0.60 | 94.85 | 2.56 | 3.32 | 0.88 | 0.88 | 0.85 | 0.84 | 0.83 |  |  |  |  |  |  |  |
