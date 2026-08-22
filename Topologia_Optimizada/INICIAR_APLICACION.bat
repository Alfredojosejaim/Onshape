@echo off
setlocal

cd /d "%~dp0"
title Topologia Optimizada - Servidor local

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
    echo [ERROR] No se encontro Python.
    echo Instala Python 3.10 o superior y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

set "MKCERT_CMD="
if exist "mkcert.exe" set "MKCERT_CMD=mkcert.exe"
if not defined MKCERT_CMD (
    where mkcert >nul 2>nul
    if not errorlevel 1 set "MKCERT_CMD=mkcert"
)
if not defined MKCERT_CMD (
    echo [ERROR] No se encontro mkcert.
    echo Descargalo desde https://github.com/FiloSottile/mkcert/releases
    echo y copia mkcert.exe en esta carpeta o agregalo al PATH.
    echo.
    pause
    exit /b 1
)

if not exist "certs" mkdir "certs"
if not exist "certs\localhost.pem" (
    echo Instalando la CA local de mkcert y generando certificados HTTPS...
    %MKCERT_CMD% -install
    if errorlevel 1 (
        echo [AVISO] No se pudo instalar la CA automaticamente.
        echo         El navegador puede mostrar una advertencia de confianza.
    )
    %MKCERT_CMD% -cert-file "certs\localhost.pem" -key-file "certs\localhost-key.pem" localhost 127.0.0.1 ::1
    if errorlevel 1 (
        echo [ERROR] No se pudieron generar los certificados HTTPS.
        pause
        exit /b 1
    )
)

if not exist ".env" (
    echo [AVISO] No existe el archivo .env.
    echo Copia .env.example como .env y completa las credenciales de Onshape.
    echo.
)

echo Iniciando Topologia Optimizada...
echo Servidor: https://localhost:8000
echo Presiona Ctrl+C para detener la aplicacion.
echo.

set "SSL_CERTFILE=%CD%\certs\localhost.pem"
set "SSL_KEYFILE=%CD%\certs\localhost-key.pem"
start "" "https://localhost:8000"
%PYTHON_CMD% api_server.py

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion se detuvo con errores.
    echo Comprueba que las dependencias esten instaladas en el entorno Python.
    echo.
    pause
)

endlocal
