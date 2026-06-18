#!/usr/bin/env bash
set -euo pipefail

D4C_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_DEFECTS4J_HOME="$D4C_DIR/defects4j-framework"

export DEFECTS4J_HOME="${DEFECTS4J_HOME:-$DEFAULT_DEFECTS4J_HOME}"
export REPAIRAGENT_ENV="${REPAIRAGENT_ENV:-/home/yijiali/tools/miniconda3/envs/repairagent}"
export JAVA_HOME="${JAVA_HOME:-/home/yijiali/tools/miniconda3/envs/repairagent/lib/jvm}"
export PATH="${REPAIRAGENT_ENV}/bin:${JAVA_HOME}/bin:${PATH}"
export PATH="${DEFECTS4J_HOME}/framework/bin:${PATH}"
export OPENAI_API_BASE="${OPENAI_API_BASE:-http://localhost:8081/v1}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-$OPENAI_API_BASE}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export D4C_TEST_TIMEOUT="${D4C_TEST_TIMEOUT:-180}"

REMOTE_MODEL="${REMOTE_MODEL:-${1:-gpt-4-0613}}"
REMOTE_PROXY="${REMOTE_PROXY:-OpenAICompatible}"
MAX_TRY="${MAX_TRY:-1}"
TEMPERATURE="${TEMPERATURE:-0}"
BATCH_SIZE="${BATCH_SIZE:-8}"
D4C_MODE="${D4C_MODE:-agent}"
RESULT_PREFIX="${D4C_RESULT_PATH:-result/defects4j/pred}"
EVAL_PREFIX="${D4C_EVAL_PATH:-result/defects4j/eval}"
PYTHON_BIN="${PYTHON_BIN:-$REPAIRAGENT_ENV/bin/python}"

cd "$D4C_DIR"

if ! command -v defects4j >/dev/null 2>&1; then
  echo "defects4j not found. Set DEFECTS4J_HOME to a Defects4J checkout." >&2
  exit 1
fi

echo "[d4c] python=$PYTHON_BIN"
echo "[d4c] java_home=$JAVA_HOME"
echo "[d4c] java=$(command -v java)"
echo "[d4c] perl=$(command -v perl)"
echo "[d4c] defects4j_home=$DEFECTS4J_HOME"
echo "[d4c] remote_model=$REMOTE_MODEL"
echo "[d4c] batch_size=$BATCH_SIZE"
echo "[d4c] mode=$D4C_MODE"
echo "[d4c] test_timeout=$D4C_TEST_TIMEOUT"

if [ "$D4C_MODE" = "agentless" ]; then
  GENERATOR_MODE="pure"
elif [ "$D4C_MODE" = "agent" ]; then
  GENERATOR_MODE="agent"
else
  echo "D4C_MODE must be 'agent' or 'agentless', got '$D4C_MODE'." >&2
  exit 1
fi

"$PYTHON_BIN" -m generator.defects4j \
  --api_key "$OPENAI_API_KEY" \
  --remote_model "$REMOTE_MODEL" \
  --max_try "$MAX_TRY" \
  --temperature "$TEMPERATURE" \
  --batch_size "$BATCH_SIZE" \
  --chat_mode remote_async \
  --remote_proxy "$REMOTE_PROXY" \
  --mode "$GENERATOR_MODE" \
  --result_path "$RESULT_PREFIX" \
  --eval_path "$EVAL_PREFIX"
