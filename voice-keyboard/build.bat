@echo off
rem Builds a single VoiceKeyboard.exe in the dist folder (no Python needed to run it).
cd /d "%~dp0"
if not exist .venv\ready call run.bat
.venv\Scripts\python -m pip install -q pyinstaller
.venv\Scripts\python -m vk.icon icon.ico
.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name VoiceKeyboard --icon icon.ico ^
  --hidden-import pystray._win32 ^
  --hidden-import pynput.keyboard._win32 ^
  --hidden-import pynput.mouse._win32 ^
  voice_keyboard.py
echo.
echo Done: dist\VoiceKeyboard.exe
pause
