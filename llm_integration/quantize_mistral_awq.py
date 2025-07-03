#!/usr/bin/env python3
"""Quantize a Mistral model using AutoAWQ.

This script converts a Hugging Face Mistral model to AWQ (activation-aware weight
quantization) format for efficient inference with libraries such as
llama.cpp or awq loaders.

Usage:
    python3 quantize_mistral_awq.py <path-to-hf-model> [output-dir]

The script requires the `autoawq` Python package.
"""

import argparse
import os
import subprocess
from pathlib import Path

try:
    from awq import AutoAWQForCausalLM
    from transformers import AutoTokenizer
except ImportError as e:
    raise SystemExit(
        "autoawq not installed. Install with 'pip install autoawq transformers'."
    ) from e


def main():
    parser = argparse.ArgumentParser(description="Quantize Mistral with AWQ")
    parser.add_argument("hf_model", help="Path to downloaded Hugging Face model")
    parser.add_argument(
        "output", nargs="?", default="./awq_out", help="Directory for quantized model"
    )
    args = parser.parse_args()

    model_path = Path(args.hf_model).resolve()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading model from {model_path}...", flush=True)
    model = AutoAWQForCausalLM.from_pretrained(model_path, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)

    print("Quantizing with AWQ...", flush=True)
    model.quantize(
        tokenizer,
        quant_config={"zero_point": True, "bits": 4, "group_size": 128},
    )

    print(f"Saving quantized model to {out_dir}...", flush=True)
    model.save_quantized(out_dir)
    tokenizer.save_pretrained(out_dir)

    print("Done.")


if __name__ == "__main__":
    main()
