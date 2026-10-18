@echo off
REM One-step launcher for Windows: creates a venv, installs deps, runs.
cd /d "%~dp0"
if not exist .venv ( py -3 -m venv .venv )
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python main.py %*
