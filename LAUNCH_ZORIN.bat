@echo off
title ZORIN AI Assistant
cd /d "%~dp0"
echo ===================================================
echo             LAUNCHING ZORIN AI ASSISTANT
echo ===================================================
echo.
"%~dp0.venv\Scripts\python.exe" -m desktop.app
if %errorlevel% neq 0 (
    echo.
    echo ZORIN exited with error code %errorlevel%.
)
pause
