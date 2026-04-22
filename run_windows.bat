@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "MAIN_PY=%SCRIPT_DIR%main.py"

if not exist "%PYTHON_EXE%" (
    echo Virtual environment not found.
    echo Create it first with: py -3.9 -m venv .venv
    exit /b 1
)

"%PYTHON_EXE%" "%MAIN_PY%"
