#!/bin/bash
# Downloads and prepares the LLM for on-device use.

set -e

MODEL_DIR="$(dirname "$0")/model"
mkdir -p "$MODEL_DIR"

MODEL_URL="https://example.com/path/to/llm.tflite"
MODEL_FILE="$MODEL_DIR/llm.tflite"

if [ ! -f "$MODEL_FILE" ]; then
  echo "Downloading model..."
  curl -L "$MODEL_URL" -o "$MODEL_FILE"
fi

echo "Model placed in $MODEL_FILE"
