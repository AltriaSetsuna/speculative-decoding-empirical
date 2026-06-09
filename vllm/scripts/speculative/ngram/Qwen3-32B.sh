#!bash


method='ngram'
SPEC_CFG="{\"num_speculative_tokens\": 5,\"method\":\"ngram\",\"prompt_lookup_max\":4}"


TARGET_MODEL='Qwen/Qwen3-32B'
# FRAME_VERSION="vllm-$(python3 -c 'import vllm; print(vllm.__version__)')"
FRAME_VERSION="vllm-0.12.0"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"


MAX_NUM_SEQS=10
GPU_NUMS=1
CUDA_VISIBLE_DEVICES=2 \
vllm serve $TARGET_MODEL \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
    --host 0.0.0.0 \
    --speculative_config "$SPEC_CFG" \
    --max_model_len 32768 \
    --gpu_memory_utilization 0.9 \
    --max-cudagraph-capture-size 1024
