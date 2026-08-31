# Dependencias para Kratos Multiphysics

> ⚠️ **DOCUMENTO HISTÓRICO — DESACTUALIZADO**
> Este documento registra las dificultades iniciales para integrar KratosMultiphysics
> en Windows (agosto 2026) y concluye erróneamente que Kratos era "IMPOSIBLE" para
> uso standalone. **Ese diagnóstico fue superado**: Kratos está hoy plenamente
> integrado como motor FEA del proyecto (ver `core/kratos_adapter.py`) y validado
> de punta a punta con resolución amgcl + fallback a skyline_lu.
> Estado actual y evidencia: ver `RESUMEN_IMPLEMENTACION.md`.

## Fecha de Documentación
2026-08-26

## Estado de Instalación
❌ **KRATOS NO FUNCIONAL** - Se han instalado las dependencias del sistema principales pero el problema persiste

### Pasos Realizados:
1. ✅ Instalación de KratosMultiphysics via pip
2. ✅ Instalación de aplicaciones Kratos via pip
3. ✅ Instalación de Visual C++ Redistributable (vc_redist.x64.exe)
4. ✅ Configuración de PATH y os.add_dll_directory()
5. ❌ KratosCore.dll aún no puede cargarse

### Diagnóstico Final:
**Error:** `Could not find module 'KratosCore.dll' (or one of its dependencies)`

**Conclusión:** KratosCore.dll tiene dependencias internas complejas que no se resuelven con Visual C++ Redistributable estándar. Requiere:
- Instalación completa desde fuente con todas las dependencias de desarrollo
- O un entorno de desarrollo específico
- O distribución binaria diferente a la de pip

**Viabilidad para standalone:** ❌ IMPOSIBLE - Demasiado complejo para usuario final

## Sistema Operativo
Windows

## Dependencias del Sistema Requeridas

### 1. Visual C++ Redistributable
Kratos requiere Visual C++ Redistributable para cargar las DLLs necesarias.

**Versiones requeridas:**
- Microsoft Visual C++ 2015-2022 Redistributable (x64)

**Método de instalación:**
```powershell
# Via winget
winget install Microsoft.VC++2015-2022Redist-x64

# O descargar desde:
# https://aka.ms/vs/17/release/vc_redist.x64.exe
```

**Estado actual:** 
- ✅ INSTALADO (vc_redist.x64.exe instalado silenciosamente)
- ❌ PERO KRATOS SIGUE SIN FUNCIONAR después de la instalación

**Resultado:** Instalar Visual C++ Redistributable NO resolvió el problema DLL load failed

## Dependencias Python

### Paquetes Principales
```bash
pip install KratosMultiphysics==10.4.3
pip install KratosStructuralMechanicsApplication==10.4.3
pip install KratosOptimizationApplication==10.4.3
pip install KratosLinearSolversApplication==10.4.3
```

### Dependencias Automáticas
- numpy>=1.20.0
- scipy>=1.7.0
- matplotlib>=3.3.0

### Herramientas de Malla
```bash
pip install gmsh==4.15.2
```

## Rutas de Instalación

### Kratos Libraries
```
C:\Users\Pets48_2\AppData\Local\Programs\Python\Python311\Lib\site-packages\KratosMultiphysics\.libs
```

### DLLs Críticas
- KratosCore.dll
- KratosStructuralMechanicsCore.dll
- KratosOptimizationCore.dll
- KratosLinearSolversCore.dll
- zlib.dll

## Problemas Conocidos

### Error: DLL load failed
**Causa:** Dependencias del sistema faltantes (Visual C++ Redistributable)
**Solución Intentada:** Instalar Microsoft Visual C++ 2015-2022 Redistributable (x64)
**Resultado:** ❌ NO RESUELTO - El error persiste después de la instalación

**Conclusión:** El problema no es solo Visual C++ Redistributable. Kratos probablemente requiere:
- Instalación completa desde fuente
- Dependencias de desarrollo adicionales
- Configuración específica del sistema
- Posiblemente versiones específicas de compiladores/librerías

### Error: Unable to find KratosCore
**Causa:** PATH no incluye el directorio de DLLs de Kratos
**Solución:** Agregar directorio .libs al PATH o usar os.add_dll_directory()

## Pasos de Instalación Completa

### 1. Instalar dependencias del sistema
```powershell
winget install Microsoft.VC++2015-2022Redist-x64
```

### 2. Instalar paquetes Python
```bash
pip install KratosMultiphysics==10.4.3
pip install KratosStructuralMechanicsApplication==10.4.3
pip install KratosOptimizationApplication==10.4.3
pip install gmsh==4.15.2
```

### 3. Verificar instalación
```python
import sys
import os
kratos_libs = r'C:\Users\Pets48_2\AppData\Local\Programs\Python\Python311\Lib\site-packages\KratosMultiphysics\.libs'
os.add_dll_directory(kratos_libs)
import KratosMultiphysics
print(f"Kratos version: {KratosMultiphysics.__version__}")
```

## Configuración de Entorno

### Variables de Entorno
Asegurar que el PATH incluya las rutas necesarias si hay problemas de carga de DLLs.

### Script de Verificación
Usar `check_environment.py` para verificar el estado de las dependencias.

## Notas Importantes

1. **Kratos no es standalone-friendly:** Requiere intervención manual del sistema para dependencias
2. **Instalación vía pip incompleta:** No incluye todas las dependencias del sistema necesarias
3. **Problemas multiplataforma:** Las dependencias varían según el sistema operativo
4. **Requisitos de desarrollo:** Para instalación completa desde fuente, requiere:
   - CMake
   - Compilador C++ (GCC/Clang en Linux, MSVC en Windows)
   - Otras dependencias de desarrollo
5. **Problema de dependencias complejo:** Visual C++ Redistributable no es suficiente, el problema persiste

## Alternativa Recomendada

Dada la complejidad de dependencias, se recomienda desarrollar un solver FEA + SIMP propio utilizando:
- Gmsh para mallas (✅ funciona sin dependencias complejas)
- Implementación propia en Python/NumPy
- Control total sobre dependencias