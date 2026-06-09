#/bin/bash
run-name=run5
model-name=openai/Qwen3-8B_vllm-0.11.0



./benchmark/benchmark.py ${run-name} \
                        --model ${mdoel-name} \
                        --edit-format whole \
                        --threads 5 \
                        --exercises-dir polyglot-benchmark \
