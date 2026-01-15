#!/usr/bin/env bash
set -e

DEST_DIR="twemoji/72x72"
TMP_DIR="twemoji_tmp"

echo "Downloading jdecked/twemoji ZIP..."

# ZIP をダウンロード
wget -O twemoji.zip \
  https://github.com/jdecked/twemoji/archive/refs/heads/main.zip

echo "Unzipping..."
unzip -q twemoji.zip -d "$TMP_DIR"

echo "Extracting PNGs..."
mkdir -p "$DEST_DIR"

# PNG をコピー
cp "$TMP_DIR"/twemoji-main/assets/72x72/*.png "$DEST_DIR"/

echo "Cleaning up..."
rm -rf "$TMP_DIR" twemoji.zip

echo "Done!"
echo "Saved to: $DEST_DIR"
