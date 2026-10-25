@echo off
rem Builds HumanTyper.exe in the dist folder.
cd /d "%~dp0"
python -m pip install -q pyinstaller pillow
python make_icon.py icon.ico
pyinstaller --noconfirm --onefile --windowed --name HumanTyper --icon icon.ico --add-data "icon.ico;." human_typer.py
echo Done: dist\HumanTyper.exe
pause
