# HumanEval vLLM Sweep Results

Generated at: `2026-06-15 10:46:40`

Metrics use the same global vLLM formulas as the CanItEdit sweep:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## L31-70B-I

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.73 | 21.22 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.74 | 20.96 | 0.99 | 2.40 | 0.72 | 0.78 | 0.78 | 0.83 | 0.86 |  |  |  |  |  |  |  |
| suffix | 0.71 | 23.97 | 1.13 | 1.00 | 0.45 | 0.49 | 0.48 | 0.57 | 0.67 | 0.66 | 0.80 | 0.73 | 0.91 | 0.86 | 0.93 | 0.82 |
| eagle3_ST | 0.73 | 29.93 | 1.41 | 1.27 | 0.64 | 0.61 | 0.64 |  |  |  |  |  |  |  |  |  |
| mlp | 0.73 | 25.94 | 1.22 |  |  |  |  |  |  |  |  |  |  |  |  |  |

## L31-8B-I

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.69 | 80.93 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.69 | 93.49 | 1.16 | 2.81 | 0.77 | 0.82 | 0.83 | 0.88 | 0.90 |  |  |  |  |  |  |  |
| suffix | 0.68 | 131.72 | 1.63 | 1.13 | 0.46 | 0.51 | 0.52 | 0.61 | 0.73 | 0.73 | 0.85 | 0.79 | 0.94 | 0.92 | 0.97 | 0.86 |
| eagle3_RedHatAI | 0.68 | 176.93 | 2.19 | 2.11 | 0.85 | 0.83 | 0.79 |  |  |  |  |  |  |  |  |  |

## Qwen3-30B-A3B-I-2507

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.96 | 77.46 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.95 | 77.00 | 0.99 | 2.57 | 0.73 | 0.82 | 0.84 | 0.76 | 0.89 |  |  |  |  |  |  |  |
| suffix | 0.96 | 79.96 | 1.03 | 0.91 | 0.38 | 0.46 | 0.52 | 0.62 | 0.77 | 0.76 | 0.90 | 0.84 | 0.95 | 0.93 | 0.97 | 0.87 |
| eagle3_RedHatAI | 0.95 | 75.12 | 0.97 | 2.53 | 0.78 | 0.78 | 0.78 | 0.77 | 0.77 |  |  |  |  |  |  |  |

## Qwen3-32B

| method | pass@1 | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 0.84 | 38.34 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 0.82 | 44.78 | 1.17 | 2.89 | 0.76 | 0.83 | 0.87 | 0.90 | 0.91 |  |  |  |  |  |  |  |
| suffix | 0.84 | 59.76 | 1.56 | 1.10 | 0.41 | 0.50 | 0.56 | 0.66 | 0.78 | 0.78 | 0.92 | 0.88 | 0.96 | 0.95 | 0.98 | 0.88 |
| eagle3_RedHatAI | 0.83 | 86.82 | 2.26 | 2.55 | 0.80 | 0.80 | 0.76 | 0.74 | 0.73 |  |  |  |  |  |  |  |
