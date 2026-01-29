#!/bin/bash



method="suffix"
TARGET_MODEL='meta-llama/Llama-3.1-8B-Instruct'
FRAME_VERSION="vllm-$(python -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"
SPEC_CFG="{\"num_speculative_tokens\": 32,\"method\":\"$method\"}"


NUM_SPEC_TOKENS=32
MAX_NUM_SEQS=8


GPU_NUMS=1
CUDA_VISIBLE_DEVICES=1 \
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
    --max_cudagraph_capture_size 1024
