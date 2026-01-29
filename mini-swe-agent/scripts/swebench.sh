#!bash

TARGET_MODEL='Qwen/Qwen3-30B-A3B'
DRAFT_MODEL='Tengyunw/qwen3_30b_moe_eagle3'
FRAME_VERSION='sglang-latest'
MAX_NUM_SEQS=3
SPEC_STEPS=3
CUSTOM_NAME="${TARGET_MODEL##*/}_${DRAFT_MODEL##*/}_${FRAME_VERSION}_MNS${MAX_NUM_SEQS}_SPEC_STEPS${SPEC_STEPS}"

LOG_DIR="results/$CUSTOM_NAME"
mkdir -p "$LOG_DIR"

# 使用 /usr/bin/time 记录时间到日志文件（追加模式，自定义格式）
# 命令的 stdout 和 stderr 输出到控制台（调试信息）
if ! /usr/bin/time -o "$LOG_DIR/runtime.log" -av \
    mini-extra swebench \
        --subset verified \
        --split test \
        --output "$LOG_DIR" \
        --workers 3 \
        --model "$CUSTOM_NAME" \
        --specify \
        ; then
    echo "命令执行失败，请检查输出。" >&2
    exit 1
fi
echo "" >> "$LOG_DIR/runtime.log"  # 追加空行
echo "运行完成，时间已记录到：$LOG_DIR/runtime.log"
