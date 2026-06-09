#!/bin/bash
method="eagle3"
TARGET_MODEL='Qwen/Qwen3-30B-A3B-Instruct-2507'
DRAFT_MODEL='RedHatAI/Qwen3-30B-A3B-Instruct-2507-speculator.eagle3'
FRAME_VERSION="vllm-$(python3 -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${DRAFT_MODEL%%/*}_${FRAME_VERSION}"

SPEC_CFG="{\"model\": \"$DRAFT_MODEL\", \"num_speculative_tokens\": 5,\"method\":\"$method\"}"


MAX_NUM_SEQS=10
GPU_NUMS=2
CUDA_VISIBLE_DEVICES=2,3 \
vllm serve $TARGET_MODEL \
    --dtype bfloat16 \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --speculative_config "$SPEC_CFG" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
    --max_model_len 32768 \
    --gpu-memory-utilization 0.9 \
