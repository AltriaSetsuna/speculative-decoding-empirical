#!/bin/bash
method="ngram"
TARGET_MODEL='Qwen/Qwen3-8B'
FRAME_VERSION="vllm-$(python3 -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"
SPEC_CFG="{\"num_speculative_tokens\": 5,\"method\":\"ngram\",\"prompt_lookup_max\":4}"


MAX_NUM_SEQS=8


GPU_NUMS=1
CUDA_VISIBLE_DEVICES=4 \
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
