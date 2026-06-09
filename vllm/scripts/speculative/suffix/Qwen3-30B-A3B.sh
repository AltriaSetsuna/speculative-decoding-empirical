#!bash


method="suffix"
TARGET_MODEL='Qwen/Qwen3-30B-A3B'
FRAME_VERSION="vllm-$(python3 -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"
SPEC_CFG="{\"num_speculative_tokens\": 32,\"method\":\"$method\"}"


MAX_NUM_SEQS=10
GPU_NUMS=2

CUDA_VISIBLE_DEVICES=2,3 \
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
    --max_model_len 32768 \
    --max-cudagraph-capture-size 1024
