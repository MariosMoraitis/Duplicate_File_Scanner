#!/usr/bin/env bash
# Start Duplicate File Scanner (run ./install.sh once first).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ ! -x .venv/bin/python ]]; then
    echo "Virtual environment not found. Please run ./install.sh first." >&2
    exit 1
fi

exec .venv/bin/python src/app.py "$@"