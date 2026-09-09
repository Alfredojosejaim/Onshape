@echo off
REM Arranca el backend real (pywebview + core vendorizado) en modo dev.
REM Requiere: pip install -r requirements-backend.txt  y  npm run dev (puerto 3000)
python app_desktop.py --dev
