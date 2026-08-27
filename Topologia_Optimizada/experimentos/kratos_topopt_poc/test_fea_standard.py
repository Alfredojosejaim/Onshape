#!/usr/bin/env python3
"""
Script para probar FEA básico usando el enfoque estándar de Kratos (JSON + StructuralMechanicsAnalysis)
PoC Kratos Topological Optimization 3D
"""

import KratosMultiphysics as Kratos
from KratosMultiphysics.StructuralMechanicsApplication import StructuralMechanicsAnalysis
import json
import os
import sys

def convert_msh_to_mdpa():
    """
    Convertir archivo Gmsh .msh a formato Kratos .mdpa
    """
    print("Convirtiendo malla de Gmsh a formato Kratos...")
    
    import gmsh
    
    gmsh.initialize()
    gmsh.open("model/cantilever_beam.msh")
    
    # Obtener nodos y elementos
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    element_types = gmsh.model.mesh.getElementTypes()
    
    # Escribir archivo MDPA manualmente
    with open("model/cantilever_beam.mdpa", "w") as f:
        f.write("Begin ModelPartData\n")
        f.write("//  Variable: Number of tables\n")
        f.write("  1\n")
        f.write("End ModelPartData\n\n")
        
        f.write("Begin Properties 0\n")
        f.write("End Properties\n\n")
        
        # Agregar propiedades de material
        f.write("Begin Properties 1\n")
        f.write("  DENSITY 2700.0\n")
        f.write("  YOUNG_MODULUS 68.9e9\n")
        f.write("  POISSON_RATIO 0.33\n")
        f.write("End Properties\n\n")
        
        f.write("Begin Nodes\n")
        for i, tag in enumerate(node_tags):
            x = node_coords[3*i]
            y = node_coords[3*i + 1]
            z = node_coords[3*i + 2]
            f.write(f"  {i+1}  {x:.6e}  {y:.6e}  {z:.6e}\n")
        f.write("End Nodes\n\n")
        
        # Obtener elementos Tet4
        element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
        
        tet_elements = None
        for i, et in enumerate(element_types):
            if et == 4:  # Tet4
                tet_elements = element_connectivity[i]
                break
        
        if tet_elements is not None:
            f.write("Begin Elements SmallDisplacementElement3D4N\n")
            for i in range(0, len(tet_elements), 4):
                elem_id = i//4 + 1
                node_ids = [int(tet_elements[i+j]) for j in range(4)]
                f.write(f"  {elem_id}  1  {' '.join(map(str, node_ids))}\n")
            f.write("End Elements\n\n")
        
        # Agregar condiciones de contorno simples (serán refinadas en el JSON)
        f.write("Begin SubModelPartNodes\n")
        f.write("End SubModelPartNodes\n\n")
        
        f.write("Begin SubModelPartElements\n")
        f.write("End SubModelPartElements\n\n")
        
        f.write("Begin SubModelPartConditions\n")
        f.write("End SubModelPartConditions\n\n")
    
    gmsh.finalize()
    print("Conversión completada: model/cantilever_beam.mdpa")

def run_standard_fea():
    """
    Ejecuta análisis FEA usando el enfoque estándar de Kratos con JSON
    """
    
    print("=== INICIANDO ANÁLISIS FEA ESTÁNDAR KRATOS ===")
    
    # Primero convertir malla si no existe
    if not os.path.exists("model/cantilever_beam.mdpa"):
        convert_msh_to_mdpa()
    
    # Cargar parámetros del proyecto
    with open("ProjectParameters.json", "r") as f:
        project_parameters = Kratos.Parameters(json.load(f))
    
    print("Parámetros cargados")
    
    # Crear análisis estructural
    try:
        analysis = StructuralMechanicsAnalysis(project_parameters)
        print("Análisis estructural creado")
    except Exception as e:
        print(f"Error creando análisis: {e}")
        return False, {'error': str(e)}
    
    # Ejecutar análisis
    print("\nEjecutando análisis...")
    try:
        analysis.Run()
        print("Análisis completado")
    except Exception as e:
        print(f"Error ejecutando análisis: {e}")
        return False, {'error': str(e)}
    
    # Extraer resultados
    print("\n=== RESULTADOS FEA ===")
    
    # Obtener el ModelPart del análisis
    model = analysis.model
    model_part = model.GetModelPart("Structure")
    
    # Encontrar desplazamiento máximo
    max_disp = 0.0
    max_disp_node = None
    max_disp_location = None
    
    for node in model_part.Nodes:
        disp_z = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Z)
        if abs(disp_z) > abs(max_disp):
            max_disp = disp_z
            max_disp_node = node.Id
            max_disp_location = (node.X, node.Y, node.Z)
    
    print(f"Desplazamiento máximo: {max_disp:.6e} m")
    print(f"Ubicación: Nodo {max_disp_node} en {max_disp_location}")
    
    # Parámetros del problema
    length = 100.0  # mm
    width = 10.0    # mm
    height = 10.0   # mm
    force = -100.0  # N (carga vertical negativa)
    Young_modulus = 68.9e9  # Pa (aluminio)
    
    # Comparar con solución analítica
    print("\n=== COMPARACIÓN CON SOLUCIÓN ANALÍTICA ===")
    
    # Solución analítica para viga en voladizo con carga puntual en el extremo
    # δ_max = (F * L^3) / (3 * E * I)
    # I = (b * h^3) / 12 para sección rectangular
    
    I = (width * height**3) / 12  # Momento de inercia (mm^4)
    I_m4 = I * 1e-12  # Convertir a m^4
    
    delta_analytical = (abs(force) * (length/1000)**3) / (3 * Young_modulus * I_m4)
    
    print(f"Desplazamiento analítico: {delta_analytical:.6e} m")
    print(f"Desplazamiento FEA: {abs(max_disp):.6e} m")
    
    error_relativo = abs(abs(max_disp) - delta_analytical) / delta_analytical
    print(f"Error relativo: {error_relativo:.2%}")
    
    # Validar
    if error_relativo < 0.15:  # 15% de error aceptable para malla relativamente gruesa
        print("[OK] VALIDACIÓN FEA: PASS - Error dentro de límite aceptable")
        return True, {
            'max_displacement': abs(max_disp),
            'analytical_displacement': delta_analytical,
            'relative_error': error_relativo,
            'nodes': model_part.NumberOfNodes(),
            'elements': model_part.NumberOfElements()
        }
    else:
        print("[FAIL] VALIDACIÓN FEA: FAIL - Error fuera de límite aceptable")
        return False, {
            'max_displacement': abs(max_disp),
            'analytical_displacement': delta_analytical,
            'relative_error': error_relativo,
            'nodes': model_part.NumberOfNodes(),
            'elements': model_part.NumberOfElements()
        }

if __name__ == "__main__":
    success, results = run_standard_fea()
    
    print("\n=== PRUEBA FEA COMPLETADA ===")
    print(f"Estado: {'PASS' if success else 'FAIL'}")
    if 'error' in results:
        print(f"Error: {results['error']}")
    else:
        print(f"Error relativo: {results['relative_error']:.2%}")
        print(f"Desplazamiento FEA: {results['max_displacement']:.6e} m")
        print(f"Desplazamiento analítico: {results['analytical_displacement']:.6e} m")