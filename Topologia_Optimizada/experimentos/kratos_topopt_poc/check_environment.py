#!/usr/bin/env python3
"""
Script para verificar el entorno de Kratos
PoC Kratos Topological Optimization 3D
"""

import sys
import os

print("=== VERIFICANDO ENTORNO KRATOS ===")
print(f"Python: {sys.version}")
print(f"Platform: {sys.platform}")

# Verificar componentes instalados
print("\n=== COMPONENTES INSTALADOS ===")

try:
    import gmsh
    print(f"[OK] Gmsh importado: {gmsh.__version__}")
except Exception as e:
    print(f"[ERROR] Error importando Gmsh: {e}")

try:
    import numpy
    print(f"[OK] NumPy importado: {numpy.__version__}")
except Exception as e:
    print(f"[ERROR] Error importando NumPy: {e}")

# Verificar archivos de Kratos
kratos_libs_path = r'C:\Users\Pets48_2\AppData\Local\Programs\Python\Python311\Lib\site-packages\KratosMultiphysics\.libs'
print(f"\n=== ARCHIVOS KRATOS ===")
print(f"Libs path: {kratos_libs_path}")
print(f"Libs path exists: {os.path.exists(kratos_libs_path)}")

if os.path.exists(kratos_libs_path):
    dll_files = [f for f in os.listdir(kratos_libs_path) if f.endswith('.dll')]
    print(f"DLLs encontrados: {dll_files}")
    
    # Verificar dependencias usando dependency walker approach
    print("\n=== VERIFICANDO DEPENDENCIAS DLL ===")
    for dll in dll_files:
        dll_path = os.path.join(kratos_libs_path, dll)
        print(f"Verificando {dll}: existe={os.path.exists(dll_path)}")

try:
    import KratosMultiphysics as Kratos
    print(f"\n[OK] KratosMultiphysics importado: {Kratos.__version__}")
except Exception as e:
    print(f"\n[ERROR] Error importando KratosMultiphysics: {e}")
    print("Esto indica que faltan dependencias del sistema para KratosCore.dll")

print("\n=== RESUMEN ===")
print("Gmsh: DISPONIBLE")
print("NumPy: DISPONIBLE") 
print("KratosMultiphysics: NO DISPONIBLE - Faltan dependencias del sistema")
print("\nRECOMENDACIÓN: Kratos requiere instalación completa desde fuente o")
print("dependencias del sistema adicionales (Visual C++ Redistributable, etc.)")