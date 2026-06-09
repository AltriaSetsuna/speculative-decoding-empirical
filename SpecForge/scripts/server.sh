
CUDA_VISIBLE_DEVICES=2,3,4,5 \
python3 -m sglang.launch_server \
	--model meta-llama/Llama-3.1-70B-Instruct \
	--mem-fraction-static 0.75 \
	--cuda-graph-max-bs 128 \
	--tp 4 \
	--trust-remote-code \
	--host 0.0.0.0 \
	--port 30000 \
	--dtype bfloat16


#!bash


TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'


MAX_NUM_SEQS=256
GPU_NUMS=4

CUDA_VISIBLE_DEVICES=2,3,4,5 \
vllm serve $TARGET_MODEL \
    --trust_remote_code \
    --hf_token "$HF_TOKEN"\
    --seed 42 \
    --tensor_parallel_size ${GPU_NUMS} \
    --max_num_seqs $MAX_NUM_SEQS \
    --port 30000 \
    --host 0.0.0.0 \
    --gpu_memory_utilization 0.8 \
    --max_model_len 32768 \