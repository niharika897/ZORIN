@echo off
title ZORIN Device Agent
cd /d "%~dp0"
echo Starting ZORIN Device Agent (PC Node)...
.\.venv\Scripts\python.exe start_device_agent.py
pause
