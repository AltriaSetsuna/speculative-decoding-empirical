#/bin/bash

method='mlp'
DRAFT_MODEL='ibm-ai-platform/llama3-70b-accelerator'
SPEC_CFG="{\"model\": \"$DRAFT_MODEL\",\"draft_tensor_parallel_size\": 1}"
TARGET_MODEL='meta-llama/Llama-3.1-70B-Instruct'
FRAME_VERSION="vllm-0.9.2"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"


inference_type="speculative"
temperature=t0
run_name=${method}_${TARGET_MODEL##*/}

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname $(dirname $(dirname "$(dirname "$SCRIPT_DIR")")))
LOG_DIR="$ROOT_DIR/output/$temperature/$inference_type/$method/${FRAME_VERSION}/${TARGET_MODEL##*/}"
mkdir -p "$LOG_DIR"

{

    echo "model_name: $TARGET_MODEL \n FRAME_VERSION: $FRAME_VERSION \n inference_type: $inference_type \n temperautre: $temperature" SPEC_CFG: $SPEC_CFG >> "$LOG_DIR/time.log"
    echo "=== 任务开始时间: $(TZ='Asia/Shanghai' date '+%a %d %b %Y %I:%M:%S %p %Z') ===" >> "$LOG_DIR/time.log"

    ./benchmark/benchmark.py ${run_name} \
                        --model "openai/${CUSTOM_NAME}" \
                        --edit-format whole \
                        --exercises-dir polyglot-benchmark \
                        --read-model-settings t0_models.yaml \
                        --new 

    echo "" >> "$LOG_DIR/runtime.log"  # 追加空行
    echo "=== 任务结束时间: $(TZ='Asia/Shanghai' date '+%a %d %b %Y %I:%M:%S %p %Z') ===" >> "$LOG_DIR/time.log"
    echo "运行完成，时间已记录到：$LOG_DIR/runtime.log"

}
