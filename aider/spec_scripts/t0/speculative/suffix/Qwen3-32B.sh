#/bin/bash

method="suffix"
TARGET_MODEL='Qwen/Qwen3-32B'
FRAME_VERSION="vllm-0.12.0"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"
SPEC_CFG="{\"num_speculative_tokens\": 32,\"method\":\"$method\"}"


inference_type="speculative"
temperature=t0
run_name=run2

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
                        --threads 8 \
                        --exercises-dir polyglot-benchmark \
                        --read-model-settings t0_models.yaml \
                        --new 

    echo "" >> "$LOG_DIR/runtime.log"  # 追加空行
    echo "=== 任务结束时间: $(TZ='Asia/Shanghai' date '+%a %d %b %Y %I:%M:%S %p %Z') ===" >> "$LOG_DIR/time.log"
    echo "运行完成，时间已记录到：$LOG_DIR/runtime.log"

}
