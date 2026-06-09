
TARGET_MODEL='Qwen/Qwen3-8B'
FRAME_VERSION='sglang-latest'
MAX_NUM_SEQS=150
CUSTOM_NAME="${TARGET_MODEL##*/}_${FRAME_VERSION}_MNS${MAX_NUM_SEQS}"

# CUDA_VISIBLE_DEVICES=0,1
# TARGET_MODEL='Qwen/Qwen3-32B'
# CUSTOM_NAME="${TARGET_MODEL}"


SCENARIO=codegeneration
RELEASE_VERSION=release_v2



LOG_DIR="output/${CUSTOM_NAME}"
mkdir -p "$LOG_DIR"

# 使用 /usr/bin/time 记录时间到日志文件（追加模式，自定义格式）
# 命令的 stdout 和 stderr 输出到控制台（调试信息）
if ! /usr/bin/time -o "$LOG_DIR/runtime.log" -av \
    python -m lcb_runner.runner.main   \
           --model $CUSTOM_NAME \
           --scenario $SCENARIO \
           --release_version $RELEASE_VERSION \
           --n 10 \
           --max_token 3000 \
           --evaluate \
           --tensor_parallel_size 2 \
           --temperature 0.2 \
           --seed 42 \
        ; then
    echo "命令执行失败，请检查输出。" >&2
    exit 1
fi
echo "" >> "$LOG_DIR/runtime.log"  # 追加空行
echo "运行完成，时间已记录到：$LOG_DIR/runtime.log"