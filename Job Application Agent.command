#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

if [ ! -x ".venv/bin/python" ]; then
  echo "First launch: installing local dependencies..."
  PYTHON=$(command -v python3 || command -v python || true)
  if [ -z "$PYTHON" ]; then
    echo "Python 3.10+ was not found. Install Python and run this launcher again."
    exit 1
  fi
  "$PYTHON" run.py --install
fi

echo "Starting Job Application Agent. Keep this window open while using it."
exec ".venv/bin/python" run.py
