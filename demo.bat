@echo off
title AGORA Demo
set "ROOT=%~dp0"

:: Demo mode — enables demo-key bypass and demo-only signatures (D-INT-4 / M3)
set "AGORA_DEMO_MODE=1"

:: Kill any ghost python or node processes to release file locks on agora.db (Windows hygiene)
echo  Cleaning up old processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1

:: Clear old database to start with 0 events
if exist "%ROOT%server\agora.db" (
    echo  Cleaning old demo database...
    del /f /q "%ROOT%server\agora.db"
)

echo.
echo  AGORA Demo Starting... [DEMO MODE]
echo.

:: API
start "AGORA API" cmd /k "cd /d %ROOT%server && set "AGORA_DEMO_MODE=1" && py -m pip install -e .[dev] -q && py -m uvicorn app.main:app --reload"

:: Dashboard
start "AGORA Dashboard" cmd /k "cd /d %ROOT%dashboard && npm install --silent && npm run dev"

:: Bekle — API boot alıyor
echo  Waiting for API to boot...
timeout /t 8 /nobreak >nul

echo  Demo is ready! Open http://localhost:3000 in your browser.
echo  Use the buttons on the dashboard to simulate AI Agent traffic.
echo.

cmd /k
