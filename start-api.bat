@echo off
title AGORA API
cd /d "%~dp0server"
py -m pip install -e ".[dev]"
py -m uvicorn app.main:app --reload
cmd /k
