#!bash


TARGET_MODEL='Qwen/Qwen3-32B'
FRAME_VERSION="vllm-$(python3 -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${TARGET_MODEL##*/}_${FRAME_VERSION}"


MAX_NUM_SEQS=10
GPU_NUMS=2

CUDA_VISIBLE_DEVICES=3,5 \
vllm serve $TARGET_MODEL \
    --dtype bfloat16 \
    --trust_remote_code \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
    --host 0.0.0.0 \
    --max_model_len 32768 \
    --gpu_memory_utilization 0.9 \
