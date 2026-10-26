@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create a Python virtual environment and install requirements.txt first.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8765 in Chrome or Edge.
".venv\Scripts\python.exe" server.py
pause
