@echo off
REM Build a standalone app folder for Windows.
cd /d "%~dp0"
if not exist .venv ( py -3 -m venv .venv )
call .venv\Scripts\activate.bat
pip install -q -r requirements-build.txt
pyinstaller --noconfirm --clean --onedir --name GestureMouse --collect-all mediapipe main.py
copy /y config.json dist\GestureMouse\ >nul
echo Built: dist\GestureMouse\GestureMouse.exe  (test it with --selftest and --dry-run)
