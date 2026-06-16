@echo off
REM Thin ASCII launcher. All real logic lives in make_patch.ps1.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_patch.ps1"
pause
