#!/usr/bin/env python
"""
DIAGNÓSTICO COMPLETO DEL ENTORNO WINDOWS PARA KRATOS MULTIPHYSICS
Este script recopila información del sistema, Python, Kratos y dependencias
para identificar el problema de carga de DLL.
"""

import sys
import os
import platform
import subprocess
import struct
from pathlib import Path

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def get_windows_info():
    """Obtener información detallada de Windows"""
    print_section("INFORMACIÓN DE WINDOWS")
    
    print(f"Versión de Windows: {platform.platform()}")
    print(f"Release: {platform.release()}")
    print(f"Versión: {platform.version()}")
    print(f"Arquitectura del sistema: {platform.machine()}")
    print(f"Procesador: {platform.processor()}")
    
    # Información adicional de Windows usando systeminfo
    try:
        result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'OS Name' in line or 'OS Version' in line or 'System Type' in line:
                    print(line.strip())
    except Exception as e:
        print(f"No se pudo ejecutar systeminfo: {e}")

def get_python_info():
    """Obtener información detallada de Python"""
    print_section("INFORMACIÓN DE PYTHON")
    
    print(f"Versión de Python: {sys.version}")
    print(f"Versión major.minor.micro: {sys.version_info}")
    print(f"Arquitectura de Python: {platform.architecture()[0]}")
    print(f"Arquitectura del executable: {struct.calcsize('P') * 8} bits")
    print(f"Ubicación del executable: {sys.executable}")
    print(f"Ubicación real de Python: {Path(sys.executable).resolve()}")
    
    print(f"\nDirectorio de instalación: {sys.prefix}")
    print(f"Directorio de ejecución: {sys.exec_prefix}")
    print(f"Directorio de site-packages: {site_packages()}")
    
    # PATH de Python
    print(f"\nPython PATH:")
    for p in sys.path[:5]:
        print(f"  - {p}")
    if len(sys.path) > 5:
        print(f"  ... y {len(sys.path) - 5} más")

def site_packages():
    """Encontrar site-packages dinámicamente"""
    from distutils.sysconfig import get_python_lib
    return get_python_lib()

def get_environment_vars():
    """Obtener variables de entorno relevantes"""
    print_section("VARIABLES DE ENTORNO")
    
    # PATH
    print("PATH (primeros 10 elementos):")
    path_entries = os.environ.get('PATH', '').split(os.pathsep)
    for i, p in enumerate(path_entries[:10]):
        print(f"  {i+1}. {p}")
    if len(path_entries) > 10:
        print(f"  ... y {len(path_entries) - 10} más")
    
    # Variables de Python
    python_vars = ['PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP']
    for var in python_vars:
        value = os.environ.get(var, 'NO DEFINIDA')
        print(f"\n{var}: {value}")

def get_kratos_info():
    """Obtener información de Kratos Multiphysics"""
    print_section("INFORMACIÓN DE KRATOS MULTIPHYSICS")
    
    try:
        import KratosMultiphysics
        print("[OK] KratosMultiphysics importado correctamente")
        print(f"Versión: {KratosMultiphysics.__version__ if hasattr(KratosMultiphysics, '__version__') else 'No disponible'}")
        print(f"Ubicación: {KratosMultiphysics.__file__}")
        print(f"Directorio: {Path(KratosMultiphysics.__file__).parent}")
    except ImportError as e:
        print(f"[ERROR] No se pudo importar KratosMultiphysics: {e}")
        # Intentar encontrar dónde está instalado
        try:
            import site
            site_packages_dirs = site.getsitepackages()
            print("\nBuscando Kratos en site-packages:")
            for sp_dir in site_packages_dirs:
                kratos_path = Path(sp_dir) / 'KratosMultiphysics'
                if kratos_path.exists():
                    print(f"  Encontrado en: {kratos_path}")
                    break
                else:
                    print(f"  No encontrado en: {sp_dir}")
        except Exception as e2:
            print(f"  No se pudo buscar en site-packages: {e2}")
        return None
    
    # Buscar archivos .pyd y .dll
    try:
        kratos_dir = Path(KratosMultiphysics.__file__).parent
        print(f"\nArchivos .pyd en {kratos_dir}:")
        pyd_files = list(kratos_dir.glob("*.pyd"))
        if pyd_files:
            for pyd in pyd_files[:10]:
                print(f"  - {pyd.name}")
            if len(pyd_files) > 10:
                print(f"  ... y {len(pyd_files) - 10} más")
        else:
            print("  No se encontraron archivos .pyd")
        
        print(f"\nArchivos .dll en {kratos_dir}:")
        dll_files = list(kratos_dir.glob("*.dll"))
        if dll_files:
            for dll in dll_files[:10]:
                print(f"  - {dll.name}")
            if len(dll_files) > 10:
                print(f"  ... y {len(dll_files) - 10} más")
        else:
            print("  No se encontraron archivos .dll")
            
        # Buscar en subdirectorios
        print(f"\nBuscando .dll en subdirectorios:")
        for dll in kratos_dir.rglob("*.dll"):
            print(f"  - {dll.relative_to(kratos_dir)}")
            
    except Exception as e:
        print(f"Error al buscar archivos: {e}")
    
    return KratosMultiphysics

def get_vc_runtime_info():
    """Obtener información de Visual C++ Runtime"""
    print_section("VISUAL C++ RUNTIME")
    
    # Usar PowerShell para obtener información de VC++ Redistributable
    try:
        ps_command = '''
        Get-WmiObject -Class Win32_Product | Where-Object { $_.Name -like "*Visual C++*" } | Select-Object Name, Version | Format-Table -AutoSize
        '''
        result = subprocess.run(['powershell', '-Command', ps_command], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("No se pudo obtener información con WMI")
    except Exception as e:
        print(f"Error al ejecutar PowerShell: {e}")
    
    # Método alternativo usando registry
    try:
        print("\nBuscando en registro (HKLM\\SOFTWARE\\Microsoft\\VisualStudio\\*\\VC\\Runtimes):")
        ps_command = '''
        Get-ChildItem "HKLM:\\SOFTWARE\\Microsoft\\VisualStudio" -Recurse -ErrorAction SilentlyContinue | 
        Where-Object { $_.Name -like "*VC*Runtimes*" } | 
        ForEach-Object { 
            $key = $_
            Get-ItemProperty $key.PSPath | 
            Select-Object @{N="Key";E={$key.Name}}, Installed, Version 
        } | Format-Table -AutoSize
        '''
        result = subprocess.run(['powershell', '-Command', ps_command], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout)
    except Exception as e:
        print(f"Error al consultar registro: {e}")

def check_dll_dependencies():
    """Verificar dependencias de DLL usando dumpbin si está disponible"""
    print_section("ANÁLISIS DE DEPENDENCIAS DLL")
    
    # Buscar dumpbin en Visual Studio
    dumpbin_paths = []
    vs_common_paths = [
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC",
        r"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Tools\MSVC",
        r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\MSVC",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC",
    ]
    
    for vs_path in vs_common_paths:
        if Path(vs_path).exists():
            for tool_dir in Path(vs_path).rglob("dumpbin.exe"):
                dumpbin_paths.append(str(tool_dir))
    
    if dumpbin_paths:
        print(f"dumpbin encontrado en: {dumpbin_paths[0]}")
        
        # Intentar analizar KratosCore.dll si existe
        try:
            import KratosMultiphysics
            kratos_dir = Path(KratosMultiphysics.__file__).parent
            kratos_core = kratos_dir / "KratosCore.dll"
            
            if kratos_core.exists():
                print(f"\nAnalizando dependencias de {kratos_core.name}:")
                result = subprocess.run([dumpbin_paths[0], '/DEPENDENTS', str(kratos_core)],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    print(f"Error ejecutando dumpbin: {result.stderr}")
            else:
                print(f"No se encontró KratosCore.dll en {kratos_dir}")
        except Exception as e:
            print(f"No se pudo analizar KratosCore.dll: {e}")
    else:
        print("dumpbin no encontrado. Visual Studio no está instalado o no en la ruta estándar.")
        print("Se recomienda instalar Visual Studio Build Tools para análisis de dependencias.")

def test_import_attempt():
    """Intentar importar Kratos y capturar el error exacto"""
    print_section("PRUEBA DE IMPORTACIÓN")
    
    print("Intentando: import KratosMultiphysics")
    try:
        import KratosMultiphysics
        print("[ÉXITO] KratosMultiphysics importado correctamente")
        print(f"Versión: {KratosMultiphysics.__version__ if hasattr(KratosMultiphysics, '__version__') else 'N/A'}")
        
        # Intentar importar aplicaciones adicionales
        print("\nIntentando: from KratosMultiphysics import StructuralMechanicsApplication")
        try:
            from KratosMultiphysics import StructuralMechanicsApplication
            print("[ÉXITO] StructuralMechanicsApplication importado")
        except ImportError as e:
            print(f"[ERROR] StructuralMechanicsApplication: {e}")
        
        print("\nIntentando: from KratosMultiphysics import OptimizationApplication")
        try:
            from KratosMultiphysics import OptimizationApplication
            print("[ÉXITO] OptimizationApplication importado")
        except ImportError as e:
            print(f"[ERROR] OptimizationApplication: {e}")
            
    except ImportError as e:
        print(f"[ERROR] Falló la importación: {e}")
        print(f"Tipo de error: {type(e).__name__}")
        
        # Información adicional del error
        import traceback
        print("\nTraceback completo:")
        traceback.print_exc()

def main():
    """Función principal"""
    print("="*70)
    print("  DIAGNÓSTICO DE ENTORNO WINDOWS PARA KRATOS MULTIPHYSICS")
    print("="*70)
    
    get_windows_info()
    get_python_info()
    get_environment_vars()
    kratos = get_kratos_info()
    get_vc_runtime_info()
    check_dll_dependencies()
    test_import_attempt()
    
    print_section("RESUMEN")
    print("Diagnóstico completado. Revisar los resultados arriba.")
    print("Guardar este output como diagnostico_entorno.txt para referencia futura.")

if __name__ == "__main__":
    main()
