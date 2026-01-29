#!/bin/bash

mini-extra swebench         \
        --subset swe-gym       \
        --split train      \
        --output "results/test"  \
        --workers 3      \
        --model "eagle3/Llama-3.1-70B-Instruct__vllm-0.11.2"     \
        --debug