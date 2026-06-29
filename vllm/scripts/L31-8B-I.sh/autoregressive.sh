#!bash


TARGET_MODEL='meta-llama/Llama-3.1-8B-Instruct'
FRAME_VERSION="vllm-$(python -c 'import vllm; print(vllm.__version__)')"
CUSTOM_NAME="${TARGET_MODEL##*/}_${FRAME_VERSION}"


MAX_NUM_SEQS=8
GPU_NUMS=1

CUDA_VISIBLE_DEVICES=2 \
vllm serve $TARGET_MODEL \
    --trust_remote_code \
    --hf_token "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"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --served-model-name "$CUSTOM_NAME" \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 8081 \
    --max_model_len 32768 \
