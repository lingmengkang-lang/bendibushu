@echo off
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\launcher.ps1"
if errorlevel 1 (pause) else (timeout /t 3 >nul)
