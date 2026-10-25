@echo off
rem Runs Human Typer from source (needs Python from python.org).
cd /d "%~dp0"
start "" pythonw human_typer.py || start "" pyw human_typer.py
