#!/bin/bash
# Builds the custom AOSP image.

set -e

if [ -z "$AOSP_DIR" ]; then
  AOSP_DIR=$PWD/aosp
fi

cd "$AOSP_DIR"

source build/envsetup.sh
lunch aosp_sailfish-userdebug

# Example: disable verity for userdebug build
export TARGET_AVB_ENABLE=false

make -j$(nproc) otapackage

OUTPUT_DIR="$(dirname "$0")/out"
mkdir -p "$OUTPUT_DIR"
cp out/target/product/*/obj/PACKAGING/target_files_intermediates/*.zip "$OUTPUT_DIR"/ || true
