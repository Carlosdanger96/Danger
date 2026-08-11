#!/bin/bash
# Converts and quantizes a Mistral model using llama.cpp.
# Usage: ./quantize_mistral.sh <path-to-hf-model> [output-dir]
set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <hf_model_dir> [output_dir]" >&2
  exit 1
fi

MODEL_DIR="$1"
OUT_DIR="${2:-$(pwd)}"
LLAMA_DIR="$(dirname "$0")/llama.cpp"

if [ ! -d "$LLAMA_DIR" ]; then
  echo "llama.cpp not found. Run setup_llama_cpp.sh first." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

F16_GGUF="$OUT_DIR/mistral-f16.gguf"
Q4_GGUF="$OUT_DIR/mistral-q4.gguf"

python3 "$LLAMA_DIR/convert-hf-to-gguf.py" "$MODEL_DIR" --outfile "$F16_GGUF" --outtype f16
"$LLAMA_DIR/quantize" "$F16_GGUF" "$Q4_GGUF" q4_K_M

echo "Quantized model written to $Q4_GGUF"
