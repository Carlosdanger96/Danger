#!/bin/bash
# Flashes the compiled OS image to the device.

set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <target_files.zip>" >&2
  exit 1
fi

IMAGE_ZIP=$1

if ! command -v fastboot >/dev/null; then
  echo "fastboot not found" >&2
  exit 1
fi

unzip -o "$IMAGE_ZIP" -d /tmp/os_image
cd /tmp/os_image

./flash-all.sh
