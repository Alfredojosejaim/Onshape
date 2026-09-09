@echo off
REM Lanza el experimento HTML sin tocar el core.
cd /d %~dp0
python app_hybrid.py %*
