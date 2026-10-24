@echo off
rem Voice Keyboard launcher: sets itself up on first run, then starts in the tray.
cd /d "%~dp0"
if not exist .venv\ready (
  echo First run: setting up Voice Keyboard, this takes a minute...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 (
    echo Python was not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install --upgrade pip -q
  .venv\Scripts\python -m pip install -r requirements.txt -q || (pause & exit /b 1)
  echo ok> .venv\ready
)
start "" .venv\Scripts\pythonw.exe voice_keyboard.py
