#!bash

speculative_method='mlp'
DRAFT_MODEL='ibm-ai-platform/llama3-8b-accelerator'
speculative_config="{\"model\": \"$DRAFT_MODEL\", \"method\": \"mlp_speculator\"}"
TARGET_MODEL='meta-llama/Meta-Llama-3.1-8B-Instruct'
FRAME_VERSION='vllm-0.11.2'
CUSTOM_NAME="${TARGET_MODEL##*/}_${FRAME_VERSION}_${speculative_method}"


MAX_NUM_SEQS=150
GPU_NUMS=1

VLLM_USE_V1=0 
CUDA_VISIBLE_DEVICES=2 \
vllm serve $TARGET_MODEL \
    --trust_remote_code \
    --hf_token "$HF_TOKEN"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
    --host 0.0.0.0 \
    --speculative_config "$speculative_config" \
    --gpu_memory_utilization 0.5 \
    --no-enable-chunked-prefill \
