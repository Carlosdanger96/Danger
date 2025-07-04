#!/bin/bash
# Clones and builds llama.cpp for running models locally.

set -e

LLAMA_DIR="$(dirname "$0")/llama.cpp"
if [ ! -d "$LLAMA_DIR" ]; then
  git clone https://github.com/ggerganov/llama.cpp.git "$LLAMA_DIR"
fi

cd "$LLAMA_DIR"
make -j$(nproc)

echo "llama.cpp built in $LLAMA_DIR"
