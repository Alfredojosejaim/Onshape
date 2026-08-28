#!/usr/bin/env python3
"""Diagnóstico detallado del archivo STEP real con Gmsh"""

import gmsh
import sys

def analizar_step_con_metodos_alternativos():
    """Probar múltiples métodos para importar y sincronizar STEP en Gmsh"""
    
    print("=" * 80)
    print("DIAGNÓSTICO DETALLADO DE CONO.STEP")
    print("=" * 80)
    
    # Método 1: Enfoque estándar OCC
    print("\n=== MÉTODO 1: Enfoque estándar OCC ===")
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    
    print("Configurando opciones básicas...")
    # Opciones específicas de OCC podrían no estar disponibles en todas las compilaciones
    # Comentamos opciones que causan error
    
    print("Importando cono.step...")
    gmsh.merge("cono.step")
    gmsh.model.add("modelo1")
    
    print("Verificando entidades antes de synchronize:")
    for dim in range(4):
        entities = gmsh.model.getEntities(dim)
        print(f"  Dim {dim}: {len(entities)}")
    
    print("Ejecutando occ.synchronize()...")
    gmsh.model.occ.synchronize()
    
    print("Verificando entidades después de occ.synchronize():")
    for dim in range(4):
        entities = gmsh.model.getEntities(dim)
        print(f"  Dim {dim}: {len(entities)}")
        if entities:
            for i, entity in enumerate(entities[:3]):
                print(f"    Entity {i}: {entity}")
    
    gmsh.finalize()
    
    # Método 2: Enfoque con kernel nativo
    print("\n=== MÉTODO 2: Enfoque con kernel nativo ===")
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    
    print("Importando cono.step...")
    gmsh.merge("cono.step")
    gmsh.model.add("modelo2")
    
    print("Ejecutando geo.synchronize()...")
    gmsh.model.geo.synchronize()
    
    print("Verificando entidades después de geo.synchronize():")
    for dim in range(4):
        entities = gmsh.model.getEntities(dim)
        print(f"  Dim {dim}: {len(entities)}")
        if entities:
            for i, entity in enumerate(entities[:3]):
                print(f"    Entity {i}: {entity}")
    
    gmsh.finalize()
    
    # Método 3: Verificar contenido raw del archivo STEP
    print("\n=== MÉTODO 3: Análisis de contenido raw del archivo STEP ===")
    try:
        with open("cono.step", "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            print(f"Total de líneas: {len(lines)}")
            print("Primeras 20 líneas:")
            for i, line in enumerate(lines[:20]):
                print(f"  {i}: {line.strip()}")
            
            # Buscar keywords clave
            print("\nBúsqueda de keywords STEP:")
            keywords = ["PRODUCT", "PRODUCT_DEFINITION", "MANIFOLD_SOLID_BREP", "CLOSED_SHELL", "ADVANCED_BREP"]
            for keyword in keywords:
                count = sum(1 for line in lines if keyword in line)
                print(f"  {keyword}: {count} ocurrencias")
    except Exception as e:
        print(f"Error leyendo archivo: {e}")
    
    print("\n" + "=" * 80)
    print("FIN DEL DIAGNÓSTICO")
    print("=" * 80)

if __name__ == "__main__":
    analizar_step_con_metodos_alternativos()