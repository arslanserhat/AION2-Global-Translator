@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m aion2_global_translator
) else (
  py -3 -m aion2_global_translator
)
if errorlevel 1 pause
