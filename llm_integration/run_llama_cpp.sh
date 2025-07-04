#!/bin/bash
# Runs a model using llama.cpp after setup.

set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <model-file> [extra args...]" >&2
  exit 1
fi

MODEL=$1
shift

LLAMA_DIR="$(dirname "$0")/llama.cpp"
if [ ! -f "$LLAMA_DIR/main" ] && [ ! -f "$LLAMA_DIR/build/bin/main" ]; then
  echo "llama.cpp not built. Run setup_llama_cpp.sh first." >&2
  exit 1
fi

# Prefer build/bin/main if exists
LLAMA_BIN="$LLAMA_DIR/build/bin/main"
if [ ! -f "$LLAMA_BIN" ]; then
  LLAMA_BIN="$LLAMA_DIR/main"
fi

"$LLAMA_BIN" -m "$MODEL" "$@"
