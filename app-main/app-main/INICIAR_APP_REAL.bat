@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
title Topologia Optimizada - App Desktop (pywebview)

echo ======================================================================
echo   TOPOLOGIA OPTIMIZADA - APP DESKTOP (pywebview)
echo      Core vendorizado + React UI
echo ======================================================================
echo.

:: ----------------------------------------------------------------------
:: 1. DETECCION DEL ENTORNO PYTHON
:: ----------------------------------------------------------------------
echo [1/4] Verificando entorno Python...
set "PYTHON_CMD="
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=%~dp0venv\Scripts\python.exe"
)
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD goto :no_python
for /f "tokens=*" %%v in ('"%PYTHON_CMD%" --version 2^>^&1') do echo        Detectado: %%v ^(%PYTHON_CMD%^)
goto :deps_check

:no_python
echo.
echo [ERROR CRITICO] No se encontro Python en el sistema.
echo Instala Python 3.10+ o crea un entorno virtual.
echo.
pause
exit /b 1

:: ----------------------------------------------------------------------
:: 2. VALIDACION DE DEPENDENCIAS PYTHON
:: ----------------------------------------------------------------------
:deps_check
echo.
echo [2/4] Verificando dependencias Python...
"%PYTHON_CMD%" -c "import webview" >nul 2>nul
if errorlevel 1 goto :no_webview
"%PYTHON_CMD%" -c "import numpy, scipy" >nul 2>nul
if errorlevel 1 goto :no_scistack
echo        pywebview + numpy/scipy disponibles.
goto :env_check

:no_webview
echo.
echo [ERROR] Falta pywebview (ventana nativa WebView2).
echo Python usado: %PYTHON_CMD%
echo Instala con:
echo   "%PYTHON_CMD%" -m pip install -r "%~dp0requirements-backend.txt"
echo.
pause
exit /b 1

:no_scistack
echo.
echo [ERROR] Falta el stack cientifico [numpy/scipy].
echo Instala con:
echo   "%PYTHON_CMD%" -m pip install -r "%~dp0requirements-backend.txt"
echo.
pause
exit /b 1

:: ----------------------------------------------------------------------
:: 3. CONFIGURACION DE ENTORNO
:: ----------------------------------------------------------------------
:env_check
echo.
echo [3/4] Configurando entorno...
if not exist ".env" (
    echo        Creando archivo .env desde .env.example...
    copy .env.example .env >nul 2>nul
    if errorlevel 1 (
        echo        WARNING: No se pudo crear .env, usando valores por defecto
    )
) else (
    echo        Archivo .env ya existe
)
echo        Entorno configurado.
goto :ui_check

:: ----------------------------------------------------------------------
:: 4. UI REACT (dist o modo dev)
:: ----------------------------------------------------------------------
:ui_check
echo.
echo [4/4] Verificando UI React...
if "%1"=="--dev" goto :launch_dev
if exist "dist\index.html" goto :launch
echo        AVISO: dist\index.html no existe.
echo        Opciones:
echo          A - Construir ahora: npm run build  [recomendado]
echo          B - Iniciar en modo --dev: usa vite en localhost:3000
echo.
choice /C AB /M "Elegir A=build ahora, B=iniciar en modo --dev"
if errorlevel 2 goto :launch_dev
echo        Construyendo UI...
if exist "node_modules" goto :have_modules
call npm install
if errorlevel 1 goto :npm_fail
:have_modules
call npm run build
if errorlevel 1 goto :npm_fail
goto :launch

:npm_fail
echo.
echo [ERROR] Fallo npm install/build. Prueba modo --dev.
echo.
pause
exit /b 1

:launch
echo.
echo ======================================================================
echo   INICIANDO APP DESKTOP (modo produccion)...
echo ======================================================================
echo.
"%PYTHON_CMD%" app_desktop.py
goto :end

:launch_dev
echo.
echo ======================================================================
echo   INICIANDO EN MODO DEV [--dev contra vite :3000]...
echo   Recuerda tener corriendo:  npm run dev
echo ======================================================================
echo.
"%PYTHON_CMD%" app_desktop.py --dev

:end
if errorlevel 1 goto :app_fail
endlocal
exit /b 0

:app_fail
echo.
echo [ERROR] La app se detuvo de forma inesperada.
echo Revisa el mensaje de arriba [suele ser OpenGL/GPU o dist faltante].
echo.
pause
exit /b 1
