#!bash
method="eagle3"
TARGET_MODEL='Qwen/Qwen3-32B'
DRAFT_MODEL='RedHatAI/Qwen3-32B-speculator.eagle3'
FRAME_VERSION='vllm-0.11.0'
MAX_NUM_SEQS=150
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${DRAFT_MODEL##*/}_${FRAME_VERSION}_MNS${MAX_NUM_SEQS}"

NUM_SPEC_TOKENS=3

SPEC_CFG="{\"model\": \"$DRAFT_MODEL\", \"num_speculative_tokens\": $NUM_SPEC_TOKENS,\"method\":\"$method\"}"

GPU_NUMS=2
CUDA_VISIBLE_DEVICES=0,1 \
vllm serve $TARGET_MODEL \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --speculative_config "$SPEC_CFG" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
