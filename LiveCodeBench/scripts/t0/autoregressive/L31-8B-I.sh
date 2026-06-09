#!bin/bash

TARGET_MODEL='meta-llama/Llama-3.1-8B-Instruct'
FRAME_VERSION="vllm-0.12.0"
CUSTOM_NAME="${TARGET_MODEL##*/}_${FRAME_VERSION}"




inference_type="autoregressive"
temperature=t0


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname $(dirname "$(dirname "$SCRIPT_DIR")"))
LOG_DIR="$ROOT_DIR/output/$temperature/$inference_type/${FRAME_VERSION}/${TARGET_MODEL##*/}"
mkdir -p "$LOG_DIR"


SCENARIO=codegeneration
RELEASE_VERSION=release_v6

{
    echo "model_name: $TARGET_MODEL \n FRAME_VERSION: $FRAME_VERSION \n inference_type: $inference_type \n temperautre: $temperature" >> "$LOG_DIR/time.log"
    echo "=== 任务开始时间: $(date) ===" >> "$LOG_DIR/time.log"

    # 使用 /usr/bin/time 记录时间到日志文件（追加模式，自定义格式）
    # 命令的 stdout 和 stderr 输出到控制台（调试信息）
    if ! /usr/bin/time -o "$LOG_DIR/runtime.log" -av \
        python -m lcb_runner.runner.main   \
            --model $CUSTOM_NAME \
            --scenario $SCENARIO \
            --release_version $RELEASE_VERSION \
            --custom_output_save_name $LOG_DIR \
            --n 1 \
            --max_token 4096 \
            --temperature 0 \
            --seed 42 \
            --multiprocess 8\
            ; then
        echo "命令执行失败，请检查输出。" >&2
        exit 1
    fi
    echo "" >> "$LOG_DIR/runtime.log"  # 追加空行
    echo "=== 任务结束时间: $(date) ===" >> "$LOG_DIR/time.log"

    echo "运行完成，时间已记录到：$LOG_DIR/runtime.log"


}