#!bash

method='mlp'
DRAFT_MODEL='ibm-ai-platform/llama3-70b-accelerator'
SPEC_CFG="{\"model\": \"$DRAFT_MODEL\",\"draft_tensor_parallel_size\": 1}"
TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'
FRAME_VERSION="vllm-$(python -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"


MAX_NUM_SEQS=1
GPU_NUMS=4

VLLM_USE_V1=0 \
CUDA_VISIBLE_DEVICES=2,3,4,5 \
vllm serve $TARGET_MODEL \
    --trust_remote_code \
    --hf_token "$HF_TOKEN"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
    --host 0.0.0.0 \
    --speculative_config "$SPEC_CFG" \
    --max_model_len 32768 \
    --gpu_memory_utilization 0.8 \