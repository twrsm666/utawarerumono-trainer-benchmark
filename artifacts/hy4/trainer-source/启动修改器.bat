@echo off
chcp 65001 >nul
title Utawarerumono Trainer
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  echo Please install Python 3.8+ from python.org and check "Add to PATH".
  pause
  exit /b 1
)
echo.
echo   Utawarerumono: Mask of Deception - Offline Trainer
echo   Starting local server, browser will open automatically.
echo   Close this window to quit.
echo.
python "%~dp0utawa_trainer.py"
echo.
pause
