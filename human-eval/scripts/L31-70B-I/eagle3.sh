#!/usr/bin/env bash
set -euo pipefail

export OPENAI_API_BASE="${OPENAI_API_BASE:-http://localhost:8081/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"

TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'
METHOD_NAME="eagle3"
HUMANEVAL_RUNNER="${HUMANEVAL_RUNNER:-/home/yijiali/speculative-decoding-empirical-main/human-eval/run_humaneval.py}"

"$HUMANEVAL_RUNNER" \
  --output-dir "out/${TARGET_MODEL##*/}/${METHOD_NAME}" \
  --num-samples-per-task "${HUMANEVAL_NUM_SAMPLES_PER_TASK:-1}" \
  --max-tokens "${HUMANEVAL_MAX_TOKENS:-4096}" \
  --temperature "${HUMANEVAL_TEMPERATURE:-0}" \
  --batch-size "${HUMANEVAL_BATCH_SIZE:-8}" \
  --top-p "${HUMANEVAL_TOP_P:-1}" \
  --k "${HUMANEVAL_K:-1}" \
  --n-workers "${HUMANEVAL_N_WORKERS:-4}" \
  --eval-timeout "${HUMANEVAL_EVAL_TIMEOUT:-3}"
