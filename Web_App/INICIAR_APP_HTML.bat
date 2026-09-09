@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
title Topologia Optimizada - Experimento HTML standalone

echo ======================================================================
echo   TOPOLOGIA OPTIMIZADA - EXPERIMENTO HTML STANDALONE (pywebview)
echo      Core vendorizado en core_vendor ^| Original intacto
echo ======================================================================
echo.

:: ----------------------------------------------------------------------
:: 1. DETECCION DEL ENTORNO PYTHON (reusa el .venv maduro del core)
:: ----------------------------------------------------------------------
echo [1/3] Verificando entorno Python...
set "PYTHON_CMD="
if exist "%~dp0..\Topologia_Optimizada\.venv\Scripts\python.exe" (
    "%~dp0..\Topologia_Optimizada\.venv\Scripts\python.exe" --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=%~dp0..\Topologia_Optimizada\.venv\Scripts\python.exe"
)
if not defined PYTHON_CMD if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
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
echo Instala Python 3.10+ o usa el .venv de Topologia_Optimizada.
echo.
pause
exit /b 1

:: ----------------------------------------------------------------------
:: 2. VALIDACION DE DEPENDENCIAS (pywebview + stack cientifico vendorizado)
:: NOTA: se usa goto en vez de bloques if (...) porque las rutas con
:: ".." rompen el parseo de bloques multilinea en cmd.exe.
:: ----------------------------------------------------------------------
:deps_check
echo.
echo [2/3] Verificando dependencias...
"%PYTHON_CMD%" -c "import webview" >nul 2>nul
if errorlevel 1 goto :no_webview
"%PYTHON_CMD%" -c "import numpy, scipy" >nul 2>nul
if errorlevel 1 goto :no_scistack
echo        pywebview + numpy/scipy disponibles.
goto :html_check

:no_webview
echo.
echo [ERROR] Falta pywebview (ventana nativa WebView2).
echo Python usado: %PYTHON_CMD%
echo Instala con:
echo   "%PYTHON_CMD%" -m pip install -r "%~dp0requirements-experiment.txt"
echo.
pause
exit /b 1

:no_scistack
echo.
echo [ERROR] Falta el stack cientifico [numpy/scipy] del core vendorizado.
echo Instala con:
echo   "%PYTHON_CMD%" -m pip install -r "%~dp0..\Topologia_Optimizada\requirements.txt"
echo Nota: cadquery/gmsh solo se exigen al importar STEP o mallar.
echo.
pause
exit /b 1

:: ----------------------------------------------------------------------
:: 3. UI HTML (dist o modo dev)
:: ----------------------------------------------------------------------
:html_check
echo.
echo [3/3] Verificando UI HTML...
if "%1"=="--dev" goto :launch
if exist "html\dist\index.html" goto :launch
echo        AVISO: html\dist\index.html no existe.
echo        Opciones:
echo          A - Construir ahora: cd html, npm install, npm run build  [recomendado]
echo          B - Iniciar en modo --dev: usa vite en localhost:5173
echo.
choice /C AB /M "Elegir A=build ahora, B=iniciar en modo --dev"
if errorlevel 2 goto :launch_dev
echo        Construyendo UI...
pushd html
if exist "node_modules" goto :have_modules
call npm install
if errorlevel 1 goto :npm_fail
:have_modules
call npm run build
if errorlevel 1 goto :npm_fail
popd
goto :launch

:npm_fail
popd
echo.
echo [ERROR] Fallo npm install/build. Prueba modo --dev.
echo.
pause
exit /b 1

:launch
echo.
echo ======================================================================
echo   INICIANDO EXPERIMENTO HTML...
echo ======================================================================
echo.
"%PYTHON_CMD%" app_desktop.py %*
goto :end

:launch_dev
echo.
echo ======================================================================
echo   INICIANDO EN MODO DEV [--dev contra vite :5173]...
echo   Recuerda tener corriendo:  cd html ^&^& npm run dev
echo ======================================================================
echo.
"%PYTHON_CMD%" app_desktop.py --dev

:end
if errorlevel 1 goto :app_fail
endlocal
exit /b 0

:app_fail
echo.
echo [ERROR] La app experimental se detuvo de forma inesperada.
echo Revisa el mensaje de arriba [suele ser OpenGL/GPU o dist faltante].
echo.
pause
exit /b 1
