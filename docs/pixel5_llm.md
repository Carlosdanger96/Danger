# Optimizing a Verizon-Locked Pixel 5 for On-Device LLMs

This guide summarizes best practices for running language models on a Pixel 5 that cannot be rooted or have its bootloader unlocked.

## Bootloader and Root Access
- Verizon Pixel 5 units have the OEM unlocking toggle disabled by design.
- As of 2025 there are no public exploits to unlock or root these models.
- Development therefore focuses on user-space tools only.

## Recommended Runtime Environments
- **Termux** provides a lightweight Linux shell for compiling and running tools like `llama.cpp`. This typically offers the best CPU performance.
- **MLC Chat** is an Android app that bundles optimized kernels and a simple UI. Performance is similar to Termux on CPU-only devices.
- Python-based environments such as Pydroid 3 work but have higher overhead.

## Suggested Models
- Small models (\<=7B parameters) quantized to 4-bit are most practical on 8 GB of RAM.
- `Phi-2` (2.7B) and `TinyLlama` (1.1B) offer a good balance of quality and speed.

## Example Termux Workflow
```bash
pkg install git clang make cmake
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp && make -j4
./main -m ~/phi2-2.7B.Q4_K_M.gguf -t 4 -c 2048
```
This downloads and builds `llama.cpp` then runs the model with reasonable defaults.
You can also run `../llm_integration/setup_llama_cpp.sh` followed by `../llm_integration/run_llama_cpp.sh <model>` if you have cloned the repository on the device.

For the latest quantization techniques, see `docs/quantize_mistral.md` which covers converting Mistral with AWQ for even smaller models.

For more details see the README in the repository root.
