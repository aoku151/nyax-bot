#!/usr/bin/env bash
set -e

DEST_DIR="twemoji/72x72"
mkdir -p "$DEST_DIR"

echo "Downloading Twemoji PNGs (jdecked/twemoji)..."

wget -r -np -nH --cut-dirs=3 \
  -A png \
  https://github.com/jdecked/twemoji/raw/main/assets/72x72/ \
  -P "$DEST_DIR"

echo "Done!"
echo "Saved to: $DEST_DIR"
