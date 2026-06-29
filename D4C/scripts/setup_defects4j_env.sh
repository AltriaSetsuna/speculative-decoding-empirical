#!/usr/bin/env bash
set -euo pipefail

D4C_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_DEFECTS4J_HOME="$D4C_DIR/defects4j-framework"
export DEFECTS4J_HOME="${DEFECTS4J_HOME:-$DEFAULT_DEFECTS4J_HOME}"
export PATH="${DEFECTS4J_HOME}/framework/bin:${PATH}"

if ! command -v defects4j >/dev/null 2>&1; then
  echo "defects4j not found. Set DEFECTS4J_HOME to a Defects4J checkout." >&2
  exit 1
fi

if ! command -v java >/dev/null 2>&1; then
  echo "java not found. Run through conda env repairagent or set JAVA_HOME/PATH." >&2
  exit 1
fi

cd "$D4C_DIR"

echo "[setup] python: $(command -v python)"
python --version
echo "[setup] java: $(command -v java)"
java -version 2>&1 | head -n 2
echo "[setup] defects4j: $(command -v defects4j)"
defects4j info -p Chart >/dev/null

echo "[setup] ensuring D4C Defects4J checkouts exist under $D4C_DIR/defects4j"
python checkout.py
