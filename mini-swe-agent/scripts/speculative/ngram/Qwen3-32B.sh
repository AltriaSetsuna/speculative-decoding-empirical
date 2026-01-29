#!/bin/bash


method='ngram'
SPEC_CFG="{\"num_speculative_tokens\": 5,\"method\":\"ngram\",\"prompt_lookup_max\":4}"


TARGET_MODEL='Qwen/Qwen3-32B'
FRAME_VERSION="vllm-0.12.0"
CUSTOM_NAME="${method}/${TARGET_MODEL##*/}_${FRAME_VERSION}"


inference_type="speculative"
temperature=t0

# 定义日志目录
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")
LOG_DIR="$ROOT_DIR/results/$temperature/$inference_type/$method/$FRAME_VERSION/${TARGET_MODEL##*/}"
mkdir -p "$LOG_DIR"
echo "日志目录: $LOG_DIR"

# 运行命令
{
    echo "model_name: $TARGET_MODEL \n FRAME_VERSION: $FRAME_VERSION \n inference_type: $inference_type \n SPEC_CFG: $SPEC_CFG\n" >> "$LOG_DIR/time.log"
    echo "=== 任务开始时间: $(date) ===" >> "$LOG_DIR/time.log"
    echo "任务 PID (内部): $$" # 记录子 Shell 的 PID，方便调试
    
    # 运行核心命令
    # 注意：/usr/bin/time 的 -a 参数非常重要，确保追加而不覆盖
    if ! /usr/bin/time -o "$LOG_DIR/time.log" -av \
        mini-extra swebench \
        --subset verified \
        --split test \
        --output "$LOG_DIR" \
        --workers 8 \
        --model "$CUSTOM_NAME" \
        ; then
        
        echo "❌ 命令执行失败！" >&2
        echo "FAILURE" >> "$LOG_DIR/time.log"
        exit 1
    fi

    echo "" >> "$LOG_DIR/time.log"
    echo "=== 任务结束时间: $(date) ===" >> "$LOG_DIR/time.log"
    echo "✅ 运行完成"

} 
# > "$LOG_DIR/console_output.log" 2>&1 &

# # 获取后台进程 PID
# PID=$!

# # 关键：与终端分离，防止 SSH 断开被杀
# disown $PID

# echo "任务已成功提交到后台！"
# echo "--------------------------------"
# echo "进程 PID       : $PID"
# echo "控制台实时日志 : $LOG_DIR/console_output.log"
# echo "时间/资源统计  : $LOG_DIR/time.log"
# echo "--------------------------------"
# echo "你可以放心地断开 SSH 连接了。"