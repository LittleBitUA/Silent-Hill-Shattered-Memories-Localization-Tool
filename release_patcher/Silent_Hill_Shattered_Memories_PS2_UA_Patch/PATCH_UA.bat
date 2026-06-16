@echo off
REM Thin ASCII launcher. All real logic lives in PATCH_UA.ps1.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0PATCH_UA.ps1" %*
pause
