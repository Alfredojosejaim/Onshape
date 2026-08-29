@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
title Topologia Optimizada - App Desktop

echo ======================================================================
echo   TOPOLOGIA OPTIMIZADA - APP NATIVA DE ESCRITORIO (PySide6 + VTK)
echo      Viewport 3D acelerado por GPU
echo ======================================================================
echo.

:: ----------------------------------------------------------------------
:: 1. DETECCION DEL ENTORNO PYTHON
:: ----------------------------------------------------------------------
echo [1/2] Verificando entorno Python...
set "PYTHON_CMD="
if exist "runtime\python\python.exe" (
    "runtime\python\python.exe" --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=runtime\python\python.exe"
)
if not defined PYTHON_CMD if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=.venv\Scripts\python.exe"
)
if not defined PYTHON_CMD if exist "python.exe" set "PYTHON_CMD=python.exe"
if not defined PYTHON_CMD (
    where py >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo.
    echo [ERROR CRITICO] No se encontro Python en el sistema.
    echo Por favor instala Python 3.10 o superior y asegurate de agregarlo al PATH.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do echo        Detectado: %%v

:: ----------------------------------------------------------------------
:: 2. VALIDACION DE DEPENDENCIAS DE ESCRITORIO
:: ----------------------------------------------------------------------
echo.
echo [2/2] Verificando dependencias PySide6 y VTK...
%PYTHON_CMD% -c "import PySide6, vtk" >nul 2>nul
if errorlevel 1 goto :missing
echo        PySide6 y VTK disponibles.

echo.
echo ======================================================================
echo   INICIANDO APP DE ESCRITORIO...
echo ======================================================================
echo.
%PYTHON_CMD% main.py

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion de escritorio se detuvo de forma inesperada.
    echo Comprueba que PySide6 y VTK esten instalados.
    echo.
    pause
    exit /b 1
)

endlocal
exit /b 0

:missing
echo.
echo [ERROR] Faltan dependencias de escritorio (PySide6 y/o VTK).
echo Instala con: pip install -r requirements.txt
echo.
pause
exit /b 1
