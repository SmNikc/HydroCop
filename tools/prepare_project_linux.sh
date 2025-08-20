#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STREAM_FILE="${SCRIPT_DIR}/published_code.txt"
ROOT="/opt/hydrometeo"
mkdir -p "$ROOT"
python3 "${SCRIPT_DIR}/apply_published_code_GidroMeteo.py" --input "$STREAM_FILE" --root "$ROOT" --eol lf
