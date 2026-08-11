# Danger

This project aims to create a custom operating system for Google Pixel devices that enables running a large language model directly on the phone. The goal is to provide on-device AI capabilities without relying on cloud services.

The repository contains early scripts and documentation for building the OS image, integrating the LLM, and flashing the custom OS onto the device. Development is still in the early stages, so expect many features to evolve over time.

## Code Overview

This repository will be organized into the following parts:

- **bootloader/** – scripts and configuration for unlocking and modifying the Pixel's bootloader.
- **aosp_build/** – instructions and patches for compiling the Android Open Source Project with custom changes.
- **llm_integration/** – code for deploying a lightweight language model onto the device, including model files and inference libraries.
- **flashing_tools/** – utilities for packaging the OS image and flashing it to the phone.
- **docs/** – additional documentation on development setup and usage.

The repository now contains initial scripts in each directory to help kickstart development. These scripts handle bootloader unlocking, fetching and building AOSP, downloading an example LLM model, and flashing the resulting image.

## Getting Started

To eventually build the custom OS you will need:

- An unlocked Pixel bootloader with USB debugging enabled.
- A Linux machine configured with Android build dependencies.
- Familiarity with ADB and Fastboot command line tools.

Once development begins, the general workflow will involve:

1. Cloning AOSP sources and applying patches in `aosp_build/`.
2. Compiling the system image and kernel.
3. Integrating an offline LLM in `llm_integration/` (e.g., via TensorFlow Lite).
4. Packaging the result and flashing it with tools from `flashing_tools/`.
5. Use `setup_llama_cpp.sh` and `run_llama_cpp.sh` in `llm_integration/` to build and test `llama.cpp` models.

## Learning More

New contributors are encouraged to read Google's [building for devices](https://source.android.com/setup/build) guide and explore the source within each directory as it is created. Useful topics to research next include:

- Android boot process and partition layout.
- Fastboot commands for flashing images.
- Optimizing small language models for mobile hardware.

As the repository grows, the `/docs` directory will contain detailed walkthroughs and examples.


Additional device-specific tips can be found in docs/pixel5_llm.md.
See docs/quantize_mistral.md for Mistral quantization instructions, including an AWQ example script.
