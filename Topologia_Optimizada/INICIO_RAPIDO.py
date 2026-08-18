#!/usr/bin/env python3
"""
🚀 GUÍA RÁPIDA DE INICIO - Topología Optimizada
"""

import os
import sys

def print_banner():
    banner = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   ⚙️  SISTEMA DE OPTIMIZACIÓN TOPOLÓGICA INTEGRADO                  ║
║       FeatureScript + App Extension + TopOpt Backend                 ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def main():
    print_banner()
    
    print_section("✅ VERIFICACIÓN DE INSTALACIÓN")
    
    try:
        import fastapi
        print("  ✓ FastAPI instalado")
    except:
        print("  ✗ FastAPI no instalado")
    
    try:
        import numpy
        print("  ✓ NumPy instalado")
    except:
        print("  ✗ NumPy no instalado")
    
    try:
        import scipy
        print("  ✓ SciPy instalado")
    except:
        print("  ✗ SciPy no instalado")
    
    try:
        from topopt_solver import TopOptSolver
        print("  ✓ TopOptSolver cargable")
    except Exception as e:
        print(f"  ✗ TopOptSolver error: {e}")
    
    try:
        from geometry_processor import GeometryProcessor
        print("  ✓ GeometryProcessor cargable")
    except Exception as e:
        print(f"  ✗ GeometryProcessor error: {e}")
    
    print_section("📋 COMPONENTES CREADOS")
    
    components = {
        "master_topology_input.fs": "FeatureScript para Onshape",
        "app-extension.html": "Panel lateral interactivo",
        "api_server.py": "Backend FastAPI principal",
        "topopt_solver.py": "Motor TopOpt SIMP",
        "geometry_processor.py": "Procesador de STEP/geometría",
        "test_api.py": "Suite de tests automáticos",
        "manifest.json": "Configuración de App Extension",
        "pyproject.toml": "Definición de dependencias",
    }
    
    for filename, description in components.items():
        exists = "✓" if os.path.exists(filename) else "✗"
        print(f"  [{exists}] {filename}")
        print(f"      └─ {description}\n")
    
    print_section("🚀 PASO 1: CONFIGURAR CREDENCIALES")
    
    print("""
  Edita el archivo .env y completa:
  
  ONSHAPE_ACCESS_KEY=tu_access_key_aqui
  ONSHAPE_SECRET_KEY=tu_secret_key_aqui
  DID=document_id_aqui
  WID=workspace_id_aqui
  MID=part_studio_id_aqui
  
  Obtén tus credenciales en: https://cad.onshape.com/api
""")
    
    print_section("🚀 PASO 2: INICIAR EL SERVIDOR")
    
    print("""
  En una terminal, ejecuta:
  
  $ python api_server.py
  
  Deberías ver:
  
  ============================================================
    🚀 INICIANDO SERVIDOR DE OPTIMIZACIÓN TOPOLÓGICA
  ============================================================
  ✓ Credenciales de Onshape configuradas correctamente
  
  📚 Documentación disponible en:
    - API Docs: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
  ============================================================
""")
    
    print_section("🚀 PASO 3: VERIFICAR INSTALACIÓN (OPCIONAL)")
    
    print("""
  En otra terminal, ejecuta los tests:
  
  $ python test_api.py
  
  Esto verifica:
  - ✓ Conectividad del servidor
  - ✓ Aceptación de solicitudes de optimización
  - ✓ Monitoreo de estado con polling
  - ✓ Documentación de API
  - ✓ Listado de trabajos
""")
    
    print_section("🚀 PASO 4: REGISTRAR APP EXTENSION EN ONSHAPE")
    
    print("""
  1. Abre Onshape
  2. Settings → App Extensions → Create New
  3. Completa:
     - Name: "Optimización Topológica"
     - App URL: http://localhost:8001/app-extension.html
       (O usa ngrok si necesitas URL pública)
  
  4. Habilitar para Part Studios
  5. Guardar
""")
    
    print_section("🚀 PASO 5: USAR EN ONSHAPE")
    
    print("""
  1. Abre un Part Studio
  2. Insert → Custom feature → "Master Topology Input"
  3. Selecciona:
     - Caras de anclaje (azules - máx 10)
     - Cara de carga (roja - 1 cara)
     - Dirección de carga (X, Y, Z)
     - Magnitud de carga
     - Fracción de volumen (0.30 recomendado)
     - Número máximo de iteraciones (50-100)
  
  4. Confirma el feature
  5. En el panel "Optimización Topológica":
     - Los datos se cargan automáticamente
     - Clica "Optimizar"
     - Monitorea el progreso 0-100%
     - Descarga resultado cuando esté listo
""")
    
    print_section("📊 ENDPOINTS DE LA API")
    
    endpoints = {
        "POST /api/optimize": "Inicia optimización (retorna jobId)",
        "GET /api/optimize/status?jobId=X": "Consulta estado y progreso",
        "GET /api/jobs": "Lista todos los trabajos",
        "GET /health": "Verifica disponibilidad del servidor",
        "GET /api/docs": "Documentación de API (Swagger)",
        "GET /docs": "Documentación interactiva (en navegador)",
    }
    
    for endpoint, description in endpoints.items():
        print(f"  {endpoint}")
        print(f"      └─ {description}\n")
    
    print_section("📚 DOCUMENTACIÓN ADICIONAL")
    
    docs = {
        "README_COMPLETO.md": "Guía completa del sistema",
        "INTEGRACION_APP_EXTENSION.md": "Instrucciones detalladas de integración",
        "documentacion_tecnica.md": "Especificación técnica original",
    }
    
    for filename, description in docs.items():
        if os.path.exists(filename):
            print(f"  ✓ {filename}")
            print(f"      └─ {description}\n")
    
    print_section("🔧 COMANDOS ÚTILES")
    
    print("""
  # Iniciar servidor
  $ python api_server.py
  
  # Ejecutar tests
  $ python test_api.py
  
  # Ver documentación interactiva en navegador
  $ start http://localhost:8000/docs
  
  # Probar endpoint con curl (después de iniciar servidor)
  $ curl http://localhost:8000/health
  
  # Instalar dependencias adicionales si es necesario
  $ pip install -e .[topopt]
  
  # Ver estructura del proyecto
  $ tree  # o 'ls -la' en PowerShell
""")
    
    print_section("⚠️  NOTAS IMPORTANTES")
    
    print("""
  1. PUERTO 8000: Asegúrate de que no esté en uso
     - Si está ocupado: "Address already in use"
     - Cambiar puerto: uvicorn.run(..., port=8001)
  
  2. CREDENCIALES: Nunca commits credenciales a git
     - .env está en .gitignore
     - Usa variables de entorno en producción
  
  3. ONSHAPE OFFLINE: Sin conexión a Onshape, algunos endpoints fallarán
     - Verifica: GET /health te dirá si credenciales son válidas
  
  4. DESARROLLO LOCAL:
     - App Extension debe ser accesible desde navegador
     - Usa ngrok o servicio similar para URL pública si es necesario
  
  5. RENDIMIENTO:
     - Primeras optimizaciones pueden ser lentas (FEA + solver)
     - Después se cachean resultados
     - Ajusta nelx/nely para más o menos precisión
""")
    
    print_section("✅ CHECKLIST DE INICIO")
    
    checklist = [
        ("□ python api_server.py funciona sin errores", "CRÍTICO"),
        ("□ GET /health retorna status: 'ok'", "CRÍTICO"),
        ("□ Credenciales en .env son correctas", "CRÍTICO"),
        ("□ App Extension registrada en Onshape", "IMPORTANTE"),
        ("□ Feature 'Master Topology Input' cargado", "IMPORTANTE"),
        ("□ python test_api.py pasa todos los tests", "RECOMENDADO"),
        ("□ Panel lateral visible en Part Studio", "RECOMENDADO"),
    ]
    
    for item, priority in checklist:
        print(f"  {item:<50} [{priority}]")
    
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🎉 ¡Sistema listo para optimizar estructuras en Onshape! 🎉".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "═"*68 + "╝")
    print("\n")

if __name__ == "__main__":
    main()
