#!bash

TARGET_MODEL='Qwen/Qwen3-14B-FP8'
VLLM_VERSION='vllm-0.11.0'
CUSTOM_NAME="${TARGET_MODEL##*/}_$VLLM_VERSION"

LOG_DIR="debug/$CUSTOM_NAME"
mkdir -p "$LOG_DIR"

# 使用 /usr/bin/time 记录时间到日志文件（追加模式，自定义格式）
# 命令的 stdout 和 stderr 输出到控制台（调试信息）
INSTANCE_ID=5

if ! /usr/bin/time -o "$LOG_DIR/runtime.log" -av \
    mini-extra swebench-single \
        --subset verified \
        --split test \
        -i $INSTANCE_ID \
        --output "$LOG_DIR/${INSTANCE_ID}.json" \
        --model "$CUSTOM_NAME" ; then
    echo "命令执行失败，请检查输出。" >&2
    exit 1
fi
echo "" >> "$LOG_DIR/runtime.log"  # 追加空行
echo "运行完成，时间已记录到：$LOG_DIR/runtime.log"

