#!/usr/bin/env bash
set -euo pipefail

export OPENAI_API_BASE="${OPENAI_API_BASE:-http://localhost:8081/v1}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"

method="mlp"
TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'
FRAME_VERSION="vllm-0.9.2"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"

/home/yijiali/speculative-decoding-empirical-main/CanItEdit/benchmark/generate_completions.py \
                          --model-type chat \
                          --model "openai/${CUSTOM_NAME}" \
                          --output-dir "out/${TARGET_MODEL##*/}/${method}" \
                          --batch-size 1 \
                          --temperature 0 \
                          --completion-limit 1
