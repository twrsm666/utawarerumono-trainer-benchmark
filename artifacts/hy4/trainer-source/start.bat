@echo off
chcp 65001 >nul
title Utawarerumono Trainer
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  pause
  exit /b 1
)
python "%~dp0utawa_trainer.py"
pause
