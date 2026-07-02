@echo off
title PixelForge CNC
cd /d "%~dp0"
python run.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch. Make sure Python 3.8+ is installed.
    echo Install dependencies: pip install -r requirements.txt
    echo.
    pause
)
