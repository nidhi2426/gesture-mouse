#!/usr/bin/env bash
# One-step launcher for macOS / Linux: creates a venv, installs deps, runs.
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
python main.py "$@"
