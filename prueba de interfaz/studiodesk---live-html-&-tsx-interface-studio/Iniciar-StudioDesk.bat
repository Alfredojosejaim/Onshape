@echo off
REM ============================================
REM  StudioDesk - Iniciador (doble clic)
REM  Arranca la app en http://localhost:3000
REM ============================================
setlocal
cd /d "%~dp0"
title StudioDesk - Live HTML ^& TSX Studio

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js no esta instalado.
  echo Descargalo desde https://nodejs.org/ ^(LTS^) e intentalo de nuevo.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo [1/3] Instalando dependencias ^(npm install^)...
  call npm install
  if errorlevel 1 (
    echo [ERROR] Fallo npm install.
    pause
    exit /b 1
  )
) else (
  echo [1/3] Dependencias OK.
)

if not exist ".env.local" (
  echo [2/3] Creando .env.local...
  if exist ".env.example" (
    copy /y ".env.example" ".env.local" >nul
  ) else (
    echo GEMINI_API_KEY=MY_GEMINI_API_KEY> ".env.local"
  )
  echo.
  echo  AVISO: edita .env.local y pon tu GEMINI_API_KEY antes de usar la IA.
  echo.
) else (
  echo [2/3] .env.local OK.
)

echo [3/3] Arrancando StudioDesk en http://localhost:3000 ...
echo Cierra esta ventana para detener la app.
echo.
start "" "http://localhost:3000"
call npm run dev
pause
