#!bash


method='ngram'
SPEC_CFG="{\"num_speculative_tokens\": 5,\"method\":\"ngram\",\"prompt_lookup_max\":4}"


TARGET_MODEL='Qwen/Qwen3-Coder-30B-A3B-Instruct'
FRAME_VERSION='vllm-0.11.2'
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"


MAX_NUM_SEQS=3
GPU_NUMS=1
export VLLM_USE_V1=0
CUDA_VISIBLE_DEVICES=4 \
vllm serve $TARGET_MODEL \
    --trust_remote_code \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
    --host 0.0.0.0 \
    --speculative_config "$SPEC_CFG" \
    --max_model_len 8192 \
    --gpu_memory_utilization 0.9 \
    --no-enable-chunked-prefill \
