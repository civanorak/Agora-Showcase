@echo off
title AGORA E2E Tests
cd /d "%~dp0dashboard"
"C:\Program Files\nodejs\npx.cmd" playwright test
cmd /k
