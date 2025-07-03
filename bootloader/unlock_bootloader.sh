#!/bin/bash
# Unlocks the Pixel bootloader. WARNING: this will wipe the device.

set -e

if ! command -v fastboot >/dev/null; then
  echo "fastboot not found. Please install Android platform-tools." >&2
  exit 1
fi

echo "\nRebooting to bootloader..."
adb reboot bootloader

sleep 5

echo "\nUnlocking bootloader..."
fastboot flashing unlock

cat <<MSG
\nBootloader unlocked. You must confirm the unlock on the device screen.\n\nAfter unlocking, the device will reboot and perform a factory reset.\nMSG
