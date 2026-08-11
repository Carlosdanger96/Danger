# Quantizing Mistral for Edge Devices

This guide explains how to convert and quantize the Mistral 7B model so it can run efficiently on constrained hardware like mobile phones or single‑board computers.

## Prerequisites

- **Python 3.10+** with `pip`
- [`transformers`](https://pypi.org/project/transformers/) and [`sentencepiece`](https://pypi.org/project/sentencepiece/) Python packages
- [`git-lfs`](https://git-lfs.github.com/) for downloading model weights from Hugging Face
- `cmake` and a C++ compiler for building [llama.cpp](https://github.com/ggerganov/llama.cpp)
- Sufficient disk space to store the original model (~13 GB)

## Steps

1. **Download the base model**
   ```bash
   git lfs install
   git clone https://huggingface.co/mistralai/Mistral-7B-v0.1
   ```
   This creates a directory `Mistral-7B-v0.1` containing the FP16 weights.

2. **Build `llama.cpp`**
   ```bash
   ./llm_integration/setup_llama_cpp.sh
   ```
   This clones `llama.cpp` under `llm_integration/llama.cpp` and compiles the tools.

3. **Convert to GGUF format**
   ```bash
   python3 llm_integration/llama.cpp/convert-hf-to-gguf.py \
       Mistral-7B-v0.1 --outfile mistral-f16.gguf --outtype f16
   ```
   The result `mistral-f16.gguf` is easier to quantize and loads faster.

4. **Quantize the model (GGUF)**
   ```bash
   llm_integration/llama.cpp/quantize \
       mistral-f16.gguf mistral-q4_K_M.gguf q4_K_M
   ```
   The `q4_K_M` quantization yields a good trade‑off between quality and size.
   You can use other types such as `q2_K` or `q3_K` for smaller models:
   ```bash
   llm_integration/quantize_mistral.sh Mistral-7B-v0.1 ./out q2_K
   ```
   The output file will include the quantization type (e.g. `mistral-q2_K.gguf`).

5. *(Optional)* **Quantize with AWQ**
   AWQ (Activation-aware Weight Quantization) can produce even smaller models
   while retaining quality. Install the `autoawq` package and run:
   ```bash
   python3 llm_integration/quantize_mistral_awq.py Mistral-7B-v0.1 awq_out --bits 2
   ```
   Replace `2` with the desired bit-width (2–8). The resulting directory
   `awq_out/` contains AWQ weights that compatible runtimes can load.

6. **Run the quantized model**
   ```bash
   llm_integration/run_llama_cpp.sh mistral-q4.gguf -t 6 -c 2048
   ```
   Adjust the thread count (`-t`) for your hardware.

## Tips

- You can experiment with other quantization types like `q5_K_M` or `q8_0` for
  higher accuracy at the cost of size and speed.
- Extremely low bit widths (e.g. "1.7-bit") are not currently supported in
  mainstream tooling. The smallest widely available option is 2-bit
  quantization using `q2_K` or the `--bits 2` AWQ setting.
- After quantization the original FP16 GGUF file can be deleted to save space.
- Smaller models such as `Mixtral-8x7B-Instruct` can be quantized in the same
  way; just change the source repository.

