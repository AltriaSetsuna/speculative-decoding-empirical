#!bash


TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'
FRAME_VERSION='vllm-0.12.0'
CUSTOM_NAME="${TARGET_MODEL##*/}_${FRAME_VERSION}"


MAX_NUM_SEQS=8
GPU_NUMS=2

CUDA_VISIBLE_DEVICES=0,1 \
vllm serve $TARGET_MODEL \
    --trust_remote_code \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8888 \
    --host 0.0.0.0 \
    --gpu_memory_utilization 0.95 \
    --max_model_len 15000 \
