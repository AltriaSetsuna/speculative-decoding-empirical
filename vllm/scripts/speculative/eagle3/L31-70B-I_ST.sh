#!/bin/bash
method="eagle3"
TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'
DRAFT_MODEL='/home/anonymous/project/SpecForge/outputs/Llama-3.1-70B-eagle3-ST-offline_7/epoch_0_step_7211'
FRAME_VERSION="vllm-$(python3 -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_ST_${FRAME_VERSION}"

SPEC_CFG="{\"model\": \"$DRAFT_MODEL\", \"num_speculative_tokens\": 3,\"method\":\"$method\"}"

GPU_NUMS=4
CUDA_VISIBLE_DEVICES=1,3,4,5 \
vllm serve $TARGET_MODEL \
    --dtype bfloat16 \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --speculative_config "$SPEC_CFG" \
    --max_num_seqs 256 \
    --port 8081 \
    --max_model_len 32768 \
    --gpu-memory-utilization 0.8 \
