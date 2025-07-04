#!/bin/bash
# Fetches AOSP sources and applies project-specific patches.

set -e

if [ -z "$AOSP_DIR" ]; then
  AOSP_DIR=$PWD/aosp
fi

mkdir -p "$AOSP_DIR"
cd "$AOSP_DIR"

# Initialize repo
repo init -u https://android.googlesource.com/platform/manifest -b android-14.0.0_r1

# Sync sources (this may take a long time)
repo sync -c -j$(nproc)

# Apply patches from repository
PATCH_DIR="$(cd "$(dirname "$0")" && pwd)/patches"
if [ -d "$PATCH_DIR" ]; then
  for patch in "$PATCH_DIR"/*.patch; do
    [ -f "$patch" ] || continue
    echo "Applying $patch"
    git -C "$AOSP_DIR" apply "$patch"
  done
fi
