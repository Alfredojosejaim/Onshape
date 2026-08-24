@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
title Topologia Optimizada - Servidor Local HTTPS

echo ======================================================================
echo   TOPOLOGIA OPTIMIZADA - INICIADOR DE SERVIDOR LOCAL (HTTPS)
echo ======================================================================
echo.

:: ----------------------------------------------------------------------
:: 1. DETECCION DEL ENTORNO PYTHON
:: ----------------------------------------------------------------------
echo [1/5] Verificando entorno Python...
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
:: 2. OBTENCION Y VERIFICACION DE INTEGRIDAD DE MKCERT (AUTOCONTENIDO)
:: ----------------------------------------------------------------------
echo.
echo [2/5] Verificando binario mkcert autocontenido...
set "MKCERT_EXE=%~dp0mkcert.exe"

if not exist "%MKCERT_EXE%" (
    echo        mkcert no encontrado en el proyecto. Iniciando descarga oficial...
    
    :: Detectar arquitectura
    set "MKCERT_URL="
    set "MKCERT_EXPECTED_HASH="
    
    if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
        set "MKCERT_URL=https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-windows-amd64.exe"
        set "MKCERT_EXPECTED_HASH=d2660b50a9ed59eada480750561c96abc2ed4c9a38c6a24d93e30e0977631398"
    ) else if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
        set "MKCERT_URL=https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-windows-arm64.exe"
        set "MKCERT_EXPECTED_HASH=41b7149021da3dc73815c48b61fe45a188be9682136e6587c6999a099a5e42ce"
    ) else (
        set "MKCERT_URL=https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-windows-386.exe"
        set "MKCERT_EXPECTED_HASH=a9ef86a4e3bbda9fb2a4dcf9f5e1823eb91f5820bb291a131b742880c10fdf44"
    )
    
    echo        Descargando desde: !MKCERT_URL!
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13; Invoke-WebRequest -Uri '!MKCERT_URL!' -OutFile 'mkcert.tmp' -UseBasicParsing"
    if errorlevel 1 (
        echo.
        echo [ERROR CRITICO] Fallo la descarga de mkcert desde GitHub.
        echo Verifica tu conexion a internet o descarga manualmente mkcert v1.4.4.
        if exist "mkcert.tmp" del /f /q "mkcert.tmp" >nul 2>&1
        echo.
        pause
        exit /b 1
    )
    
    echo        Verificando firma SHA-256...
    for /f "usebackq delims=" %%h in (`powershell -NoProfile -Command "(Get-FileHash -Path 'mkcert.tmp' -Algorithm SHA256).Hash.ToLower()"` ) do set "MKCERT_ACTUAL_HASH=%%h"
    
    if /i not "!MKCERT_ACTUAL_HASH!"=="!MKCERT_EXPECTED_HASH!" (
        echo.
        echo [ERROR DE INTEGRIDAD] El hash SHA-256 de mkcert descargado no coincide.
        echo Esperado: !MKCERT_EXPECTED_HASH!
        echo Obtenido: !MKCERT_ACTUAL_HASH!
        echo El archivo descargado puede estar corrupto o adulterado.
        if exist "mkcert.tmp" del /f /q "mkcert.tmp" >nul 2>&1
        echo.
        pause
        exit /b 1
    )
    
    move /y "mkcert.tmp" "%MKCERT_EXE%" >nul
    echo        mkcert v1.4.4 verificado e instalado correctamente en el proyecto.
) else (
    echo        mkcert.exe encontrado en el directorio del proyecto.
)

:: ----------------------------------------------------------------------
:: 3. INSTALACION DE CA LOCAL DE CONFIANZA
:: ----------------------------------------------------------------------
echo.
echo [3/5] Verificando Autoridad Certificadora Local (mkcert CA)...
"%MKCERT_EXE%" -install
if errorlevel 1 (
    echo.
    echo [ERROR CRITICO] No se pudo instalar la CA local de mkcert en el sistema.
    echo Asegurate de ejecutar este script con los permisos necesarios para instalar certificados.
    echo.
    pause
    exit /b 1
)

:: ----------------------------------------------------------------------
:: 4. GENERACION Y VALIDACION DE CERTIFICADOS TLS
:: ----------------------------------------------------------------------
echo.
echo [4/5] Comprobando certificados HTTPS para localhost...
if not exist "%~dp0certs" mkdir "%~dp0certs"

set "CERT_FILE=%~dp0certs\localhost.pem"
set "KEY_FILE=%~dp0certs\localhost-key.pem"

set "NEED_GENERATE=0"
if not exist "%CERT_FILE%" set "NEED_GENERATE=1"
if not exist "%KEY_FILE%" set "NEED_GENERATE=1"

if "!NEED_GENERATE!"=="1" (
    echo        Generando certificados TLS para localhost, 127.0.0.1, ::1...
    "%MKCERT_EXE%" -cert-file "%CERT_FILE%" -key-file "%KEY_FILE%" localhost 127.0.0.1 ::1
    if errorlevel 1 (
        echo.
        echo [ERROR CRITICO] Fallo la generacion de certificados HTTPS con mkcert.
        echo.
        pause
        exit /b 1
    )
) else (
    echo        Certificados existentes encontrados y validados.
)

if not exist "%CERT_FILE%" (
    echo [ERROR CRITICO] El archivo de certificado %CERT_FILE% no existe.
    pause
    exit /b 1
)
if not exist "%KEY_FILE%" (
    echo [ERROR CRITICO] El archivo de clave privada %KEY_FILE% no existe.
    pause
    exit /b 1
)

:: ----------------------------------------------------------------------
:: 5. CONFIGURACION DE ENTORNO Y ARRANQUE DE FASTAPI CON HTTPS
:: ----------------------------------------------------------------------
echo.
echo [5/5] Iniciando servidor FastAPI con soporte HTTPS...

if not exist ".env" (
    if exist ".env.example" (
        echo        [AVISO] No se encontro .env. Creando copia a partir de .env.example...
        copy ".env.example" ".env" >nul
        echo        Recuerda configurar tus credenciales de Onshape en el archivo .env.
    )
)

set "SSL_CERTFILE=%CERT_FILE%"
set "SSL_KEYFILE=%KEY_FILE%"

echo.
echo ======================================================================
echo   SERVIDOR HTTPS LISTO Y ACTIVO
echo   URL Local:     https://localhost:8000
echo   App Extension: https://localhost:8000/
echo   App 3D Viewer: https://localhost:8000/app
echo ======================================================================
echo.
echo Abriendo navegador en https://localhost:8000 ...
start "" "https://localhost:8000"

%PYTHON_CMD% api_server.py

if errorlevel 1 (
    echo.
    echo [ERROR] El servidor FastAPI se detuvo de forma inesperada.
    echo Comprueba que las dependencias esten instaladas y los puertos esten libres.
    echo.
    pause
    exit /b 1
)

endlocal
