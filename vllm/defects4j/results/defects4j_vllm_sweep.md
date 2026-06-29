# Defects4J vLLM Sweep Results

Generated at: `2026-06-22 08:48:50`

Metrics use the same global formulas as the Grafana dashboard:

- `tps = vllm:request_generation_tokens_sum / vllm:request_decode_time_seconds_sum`
- `mal = vllm:spec_decode_num_accepted_tokens_total / vllm:spec_decode_num_drafts_total`
- `0-alpha = accepted_pos_0 / drafts`; `N-alpha = accepted_pos_N / accepted_pos_N-1`
- `speedup = method_tps / autoregressive_tps` within the same model

## L31-70B-I

| method | correct/total(%) | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 19.68 | 23.34 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 18.99 | 39.09 | 1.67 | 3.77 | 0.88 | 0.91 | 0.92 | 0.94 | 0.95 |  |  |  |  |  |  |  |
| suffix | 19.22 | 39.57 | 1.70 | 3.55 | 0.64 | 0.76 | 0.78 | 0.82 | 0.89 | 0.87 | 0.95 | 0.93 | 0.98 | 0.95 | 0.98 | 0.95 |
| eagle3 | 19.91 | 19.29 | 0.83 | 0.35 | 0.28 | 0.22 | 0.22 |  |  |  |  |  |  |  |  |  |
| mlp | 19.22 | 20.59 | 0.88 |  |  |  |  |  |  |  |  |  |  |  |  |  |

## L31-8B-I

| method | correct/total(%) | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 7.09 | 75.67 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 7.09 | 134.59 | 1.78 | 3.23 | 0.77 | 0.90 | 0.91 | 0.92 | 0.93 |  |  |  |  |  |  |  |
| suffix | 6.86 | 207.43 | 2.74 | 3.18 | 0.59 | 0.75 | 0.77 | 0.81 | 0.88 | 0.87 | 0.95 | 0.93 | 0.98 | 0.96 | 0.98 | 0.96 |
| eagle3 | 7.32 | 117.65 | 1.55 | 1.56 | 0.71 | 0.71 | 0.68 |  |  |  |  |  |  |  |  |  |

## Qwen3-30B-A3B-I-2507

| method | correct/total(%) | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 18.08 | 94.30 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 18.08 | 128.15 | 1.36 | 3.38 | 0.84 | 0.88 | 0.89 | 0.91 | 0.91 |  |  |  |  |  |  |  |
| suffix | 18.08 | 144.40 | 1.53 | 3.14 | 0.62 | 0.76 | 0.76 | 0.79 | 0.85 | 0.84 | 0.93 | 0.91 | 0.96 | 0.93 | 0.97 | 0.94 |
| eagle3 |  | 52.07 | 0.55 | 1.57 | 0.71 | 0.71 | 0.70 |  |  |  |  |  |  |  |  |  |
| eagle3 | 18.54 | 76.79 | 0.81 | 1.61 | 0.64 | 0.63 | 0.65 | 0.68 | 0.68 |  |  |  |  |  |  |  |

## Qwen3-32B

| method | correct/total(%) | tps | speedup | mal | 0-alpha | 1-alpha | 2-alpha | 3-alpha | 4-alpha | 5-alpha | 6-alpha | 7-alpha | 8-alpha | 9-alpha | 10-alpha | 11-alpha |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| autoregressive | 18.54 | 36.78 | 1.00 |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ngram | 18.99 | 68.92 | 1.87 | 3.40 | 0.84 | 0.88 | 0.90 | 0.91 | 0.92 |  |  |  |  |  |  |  |
| suffix | 18.99 | 96.11 | 2.61 | 3.33 | 0.64 | 0.75 | 0.77 | 0.80 | 0.86 | 0.85 | 0.94 | 0.92 | 0.97 | 0.93 | 0.97 | 0.94 |
| eagle3 |  | 44.38 | 1.21 | 2.10 | 0.84 | 0.84 | 0.81 |  |  |  |  |  |  |  |  |  |
| eagle3 | 18.31 | 82.04 | 2.23 | 2.83 | 0.83 | 0.83 | 0.80 | 0.78 | 0.77 |  |  |  |  |  |  |  |

