@echo off
chcp 65001 >nul
python "%~dp0file_organizer.py"
if errorlevel 1 pause
