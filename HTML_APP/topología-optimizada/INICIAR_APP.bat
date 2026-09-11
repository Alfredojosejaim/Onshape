@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Topologia Optimizada - App de escritorio

echo ======================================================================
echo   TOPOLOGIA OPTIMIZADA - APP DE ESCRITORIO (pywebview, sin navegador)
echo ======================================================================
echo.

set "MISSING=0"
set "PYTHON_CMD="

:: ----------------------------------------------------------------------
:: 1. PYTHON 3.10+
:: ----------------------------------------------------------------------
echo [1/6] Python...
:: SELF-CONTAINED: primero el .venv local del proyecto (backend\.venv, .venv),
:: luego el PATH. Sin rutas de otros PCs.
if exist "%~dp0backend\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0backend\.venv\Scripts\python.exe"
) else (
    if exist "%~dp0.venv\Scripts\python.exe" (
        set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)
if not defined PYTHON_CMD (
    echo   [FALTA] Python 3.10+ no encontrado: ni backend\.venv, ni .venv, ni PATH.
    echo   INSTALAR:
    echo     1. Descarga Python 3.11 64-bit desde https://www.python.org/downloads/
    echo     2. En el instalador marca "Add python.exe to PATH" y reabre esta ventana.
    echo     Opcional aislado: python -m venv backend\.venv ^& backend\.venv\Scripts\pip install -r backend\requirements.txt
    set "MISSING=1"
    goto :report
)
for /f "tokens=*" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do echo   OK: %%v ^(%PYTHON_CMD%^)
"%PYTHON_CMD%" -c "import sys; raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo   [FALTA] Se necesita Python 3.10 o superior; el detectado es anterior.
    echo   INSTALAR: Python 3.11 64-bit desde https://www.python.org/downloads/
    set "MISSING=1"
    goto :report
)

:: ----------------------------------------------------------------------
:: 2. PIP
:: ----------------------------------------------------------------------
echo.
echo [2/6] pip...
"%PYTHON_CMD%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo   [FALTA] pip no disponible para %PYTHON_CMD%.
    echo   INSTALAR:
    echo     "%PYTHON_CMD%" -m ensurepip --upgrade
    echo     "%PYTHON_CMD%" -m pip install --upgrade pip
    set "MISSING=1"
    goto :report
)
echo   OK: pip disponible.

:: ----------------------------------------------------------------------
:: 3+4. PAQUETES PYTHON (una sola sonda: ~0.5s en vez de ~10s con pip show)
:: ----------------------------------------------------------------------
echo.
:: FAST-CHECK (reversible): backend\check_env.py hace todos los chequeos en
:: un solo proceso stdlib (importlib.metadata, sin importar DLLs pesadas).
:: Para volver atras: restaurar los bloques antiguos desde git.
"%PYTHON_CMD%" "%~dp0backend\check_env.py"
if errorlevel 1 (
    set "MISSING=1"
    goto :report
)

:: ----------------------------------------------------------------------
:: 5. NODE/NPM + node_modules (solo para construir dist)
:: ----------------------------------------------------------------------
echo.
echo [5/6] Node y dependencias frontend...
if "%1"=="--dev" (
    echo   Modo --dev: se omite el chequeo de build ^(usa vite en :3000^).
    goto :node_dev_check
)
where node >nul 2>nul
if errorlevel 1 (
    echo   [FALTA] Node.js no encontrado y hace falta para construir dist\index.html.
    echo   INSTALAR: Node.js LTS 20+ desde https://nodejs.org/ ^(incluye npm^), luego:
    echo     npm install
    echo     npm run build
    set "MISSING=1"
    goto :report
)
where npm >nul 2>nul
if errorlevel 1 (
    echo   [FALTA] npm no encontrado ^(reinstala Node.js LTS desde https://nodejs.org/^).
    set "MISSING=1"
    goto :report
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo   OK: Node %%v
if not exist "node_modules" (
    echo   [FALTA] Carpeta node_modules no existe ^(dependencias frontend sin instalar^).
    echo   INSTALAR:
    echo     npm install
    set "MISSING=1"
    goto :report
)
echo   OK: node_modules presente.
goto :dist_check

:node_dev_check
where npm >nul 2>nul
if errorlevel 1 (
    echo   [FALTA] npm no encontrado; para --dev necesitas Node.js LTS desde https://nodejs.org/
    echo   y en otra terminal: npm install ^& npm run dev
    set "MISSING=1"
    goto :report
)
if not exist "node_modules" (
    echo   [FALTA] node_modules no existe. INSTALAR: npm install
    set "MISSING=1"
    goto :report
)

:: ----------------------------------------------------------------------
:: 6. dist\index.html
:: ----------------------------------------------------------------------
:dist_check
echo.
echo [6/6] UI compilada (dist)...
if "%1"=="--dev" goto :launch_dev
if not exist "dist\index.html" (
    echo   [FALTA] dist\index.html no existe ^(la UI no esta compilada^).
    echo   INSTALAR/CONSTRUIR:
    echo     npm install
    echo     npm run build
    set "MISSING=1"
    goto :report
)
echo   OK: dist\index.html presente.

echo.
echo ======================================================================
echo   TODO LISTO - INICIANDO VENTANA NATIVA (sin navegador)
echo ======================================================================
echo.
"%PYTHON_CMD%" backend\app_desktop.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] La app se detuvo. Causas tipicas:
    echo   - WebView2 Runtime ausente - INSTALAR desde https://go.microsoft.com/fwlink/p/?LinkId=2124703
    echo   - GPU/OpenGL - actualiza drivers o prueba: "%PYTHON_CMD%" backend\app_desktop.py --dev
    echo     con "npm run dev" corriendo en otra terminal.
    pause
    exit /b 1
)
goto :end

:launch_dev
echo.
echo   MODO DEV: en otra terminal ejecuta: npm run dev
echo   y esta ventana abrira http://localhost:3000/ sin navegador externo.
echo.
"%PYTHON_CMD%" backend\app_desktop.py --dev
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo abrir el modo dev. Verifica que "npm run dev" este corriendo.
    pause
    exit /b 1
)
goto :end

:report
echo.
echo ======================================================================
echo   FALTA ALGO (ver lineas [FALTA] arriba). Instala lo indicado,
echo   cierra y vuelve a abrir este .bat.
echo ======================================================================
pause
exit /b 1

:end
endlocal
exit /b 0
