#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ECDICT_URL="${ECDICT_URL:-https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
fi

echo "Downloading ECDICT source data..."
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 3 --connect-timeout 20 --max-time 300 "$ECDICT_URL" -o "$TMP_DIR/ecdict.csv"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$TMP_DIR/ecdict.csv" "$ECDICT_URL"
else
  echo "curl or wget is required to download ECDICT." >&2
  exit 1
fi

echo "Building local word library..."
"$PYTHON_BIN" scripts/build_word_library.py "$TMP_DIR/ecdict.csv" app/data/words.jsonl

echo "Filling offline examples..."
"$PYTHON_BIN" scripts/fill_word_examples.py \
  --mode offline \
  --input app/data/words.jsonl \
  --output app/data/words.jsonl

echo "Word library updated: app/data/words.jsonl"
