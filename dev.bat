@echo off
title AGORA Dev
set ROOT=%~dp0
set LOG=%ROOT%dev-log.txt

echo AGORA Dev Log > "%LOG%"
echo Started: %date% %time% >> "%LOG%"
echo ROOT: %ROOT% >> "%LOG%"
echo. >> "%LOG%"

echo Checking py... >> "%LOG%"
py --version >> "%LOG%" 2>&1
echo py exit: %errorlevel% >> "%LOG%"

echo Checking npm... >> "%LOG%"
rem npm is npm.cmd — without `call` the batch never returns from it
call npm --version >> "%LOG%" 2>&1
echo npm exit: %errorlevel% >> "%LOG%"

echo. >> "%LOG%"
echo [1/4] pip install... >> "%LOG%"
cd /d "%ROOT%server"
py -m pip install -e ".[dev]" >> "%LOG%" 2>&1
echo pip exit: %errorlevel% >> "%LOG%"
if errorlevel 1 goto :done

echo [2/4] npm install... >> "%LOG%"
cd /d "%ROOT%dashboard"
call npm install >> "%LOG%" 2>&1
echo npm exit: %errorlevel% >> "%LOG%"
if errorlevel 1 goto :done

echo [3/4] Starting API... >> "%LOG%"
start "AGORA API" cmd /k "cd /d %ROOT%server && py -m uvicorn app.main:app --reload"
timeout /t 3 /nobreak >nul

echo [4/4] Starting Dashboard... >> "%LOG%"
start "AGORA Dashboard" cmd /k "cd /d %ROOT%dashboard && npm run dev"

echo SUCCESS >> "%LOG%"
echo Log dosyasi: %LOG%
echo.
echo API       -^> http://localhost:8000/health
echo Dashboard -^> http://localhost:3000
echo.
echo Seed: py scripts\seed_events.py --count 10

:done
echo Bitti: %date% %time% >> "%LOG%"
echo.
echo Log: %LOG%
echo Okuyor...
type "%LOG%"
cmd /k
