@echo off
title ZORIN Multi-Device Server
cd /d "%~dp0"
echo Starting ZORIN Multi-Device Server...
.\.venv\Scripts\python.exe start_server.py
pause
