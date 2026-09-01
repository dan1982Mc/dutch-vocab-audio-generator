@echo off
setlocal

if not exist .venv\Scripts\pythonw.exe (
    echo Virtual environment not found.
    echo Run these commands first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Launch the GUI without opening a separate Command Prompt window.
.venv\Scripts\pythonw.exe app.py
