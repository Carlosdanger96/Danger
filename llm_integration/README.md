# LLM Integration

This directory contains scripts and configuration for running a lightweight language model on the Pixel.

The general approach is to use TensorFlow Lite (or an alternative inference engine) to run the model offline. The actual model weights are not included in the repository.

Scripts will download the model, convert it to a mobile-friendly format, and place the files under `llm_integration/model/`.

For experimentation, run `setup_llama_cpp.sh` to build [llama.cpp](https://github.com/ggerganov/llama.cpp). Use `run_llama_cpp.sh <model>` to execute a downloaded GGUF model.
You can also convert and quantize a Mistral model using `quantize_mistral.sh <hf-model-dir> [out-dir]`. See `../docs/quantize_mistral.md` for details.
