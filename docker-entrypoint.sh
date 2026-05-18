#!/bin/sh
# Fix volume permissions at runtime, then drop to appuser.
# Mounted volumes (Railway, etc.) are owned by root with restrictive perms,
# which would prevent appuser from creating the SQLite db or asset files.
set -e

DATA_DIR="${AD_ENGINE_DATA_DIR:-/app/data}"
ASSET_DIR="${OPENAI_IMAGE_OUTPUT_DIR:-/app/data/generated_assets}"

mkdir -p "$DATA_DIR" "$ASSET_DIR"
chown -R appuser:appuser "$DATA_DIR"

exec gosu appuser "$@"
