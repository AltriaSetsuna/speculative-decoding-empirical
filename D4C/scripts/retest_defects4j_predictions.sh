#!/usr/bin/env bash
set -euo pipefail

D4C_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_DEFECTS4J_HOME="$D4C_DIR/defects4j-framework"

export DEFECTS4J_HOME="${DEFECTS4J_HOME:-$DEFAULT_DEFECTS4J_HOME}"
export REPAIRAGENT_ENV="${REPAIRAGENT_ENV:-/home/yijiali/tools/miniconda3/envs/repairagent}"
export JAVA_HOME="${JAVA_HOME:-/home/yijiali/tools/miniconda3/envs/repairagent/lib/jvm}"
export PATH="${REPAIRAGENT_ENV}/bin:${JAVA_HOME}/bin:${PATH}"
export PATH="${DEFECTS4J_HOME}/framework/bin:${PATH}"

PYTHON_BIN="${PYTHON_BIN:-$REPAIRAGENT_ENV/bin/python}"
PRED_PATH="${1:?usage: retest_defects4j_predictions.sh PRED_CSV EVAL_CSV}"
EVAL_PATH="${2:?usage: retest_defects4j_predictions.sh PRED_CSV EVAL_CSV}"

cd "$D4C_DIR"
"$PYTHON_BIN" -m evaluate --test True --data defects4j --pred "$PRED_PATH" --eval "$EVAL_PATH"
