#!/usr/bin/env bash

export OPENAI_API_BASE="http://localhost:8081/v1"
export OPENAI_API_KEY="EMPTY"
export HF_HUB_OFFLINE=1

method="eagle3"
TARGET_MODEL='Qwen/Qwen3-30B-A3B-Instruct-2507'
DRAFT_MODEL='RedHatAI/Qwen3-30B-A3B-Instruct-2507-speculator.eagle3'
FRAME_VERSION="vllm-0.12.0"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${DRAFT_MODEL%%/*}_${FRAME_VERSION}"

/home/yijiali/speculative-decoding-empirical-main/CanItEdit/benchmark/generate_completions.py \
                          --model-type chat \
                          --model "openai/${CUSTOM_NAME}" \
                          --output-dir "out/${TARGET_MODEL##*/}/${method}" \
                          --batch-size 8 \
                          --temperature 0 \
                          --completion-limit 1
