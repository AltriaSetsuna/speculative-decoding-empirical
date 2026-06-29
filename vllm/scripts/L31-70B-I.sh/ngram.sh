#!bash

export HF_HUB_OFFLINE=1

method='ngram'
SPEC_CFG="{\"num_speculative_tokens\": 5,\"method\":\"ngram\",\"prompt_lookup_max\":4}"


TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'
FRAME_VERSION="vllm-$(python3 -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"


MAX_NUM_SEQS=8
GPU_NUMS=4
CUDA_VISIBLE_DEVICES=2,3,4,5 \
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
    --max-cudagraph-capture-size 128 \
