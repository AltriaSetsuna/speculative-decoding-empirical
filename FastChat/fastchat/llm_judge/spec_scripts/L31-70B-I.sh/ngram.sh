python3 /home/yijiali/project/FastChat/fastchat/llm_judge/gen_api_answer.py \
    --model ngram/Llama-3.1-70B-Instruct_vllm-0.12.0 \
    --openai-api-base http://localhost:8081/v1 \
    --parallel 8 \
    --force-temperature 0.0  