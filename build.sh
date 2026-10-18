#!/usr/bin/env bash
# Build a standalone app folder for THIS operating system (macOS / Linux).
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements-build.txt
pyinstaller --noconfirm --clean --onedir --name GestureMouse --collect-all mediapipe main.py
cp config.json dist/GestureMouse/
echo "Built: dist/GestureMouse/GestureMouse  (test it with --selftest and --dry-run)"
