#!/usr/bin/env python3
"""
Script para probar carga directa de DLL KratosCore
"""

import sys
import os
import ctypes

kratos_libs = r'C:\Users\Pets48_2\AppData\Local\Programs\Python\Python311\Lib\site-packages\KratosMultiphysics\.libs'

print("=== PRUEBA DE CARGA DIRECTA DE DLL ===")
print(f"Directorio de DLLs: {kratos_libs}")
print(f"Directorio existe: {os.path.exists(kratos_libs)}")

# Agregar directorio al PATH
os.environ['PATH'] = kratos_libs + os.pathsep + os.environ.get('PATH', '')
print("Directorio agregado al PATH")

# Usar os.add_dll_directory
os.add_dll_directory(kratos_libs)
print("Directorio agregado con os.add_dll_directory")

# Intentar cargar la DLL directamente
kratos_dll_path = os.path.join(kratos_libs, 'KratosCore.dll')
print(f"Intentando cargar: {kratos_dll_path}")
print(f"Archivo existe: {os.path.exists(kratos_dll_path)}")

try:
    kratos = ctypes.CDLL(kratos_dll_path)
    print("[OK] KratosCore.dll cargado exitosamente")
except Exception as e:
    print(f"[ERROR] Error cargando KratosCore.dll: {e}")
    print("Esto indica que faltan dependencias de la DLL en sí")