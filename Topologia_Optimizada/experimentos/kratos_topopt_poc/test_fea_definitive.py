#!/usr/bin/env python3
"""
Script definitivo usando StructuralMechanicsAnalysis con aplicación manual de condiciones
que se integran correctamente en el RHS del sistema
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"

import KratosMultiphysics as Kratos
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis
import json

def test_definitive_configuration():
    """
    Prueba definitiva usando StructuralMechanicsAnalysis con condiciones manuales
    """
    
    print("=== PRUEBA DE CONFIGURACIÓN DEFINITIVA ===")
    
    # Verificar archivos
    if not os.path.exists("model/cantilever_beam.mdpa"):
        print("ERROR: No existe model/cantilever_beam.mdpa")
        return False, {'error': 'Mesh file not found'}
    
    if not os.path.exists("ProjectParameters.json"):
        print("ERROR: No existe ProjectParameters.json")
        return False, {'error': 'ProjectParameters.json not found'}
    
    if not os.path.exists("MaterialParameters.json"):
        print("ERROR: No existe MaterialParameters.json")
        return False, {'error': 'MaterialParameters.json not found'}
    
    print("[OK] Archivos de configuracion encontrados")
    
    try:
        print("\nCargando configuración JSON...")
        with open("ProjectParameters.json", "r") as f:
            json_content = f.read()
        
        project_parameters = Kratos.Parameters(json_content)
        
        model = Kratos.Model()
        
        # Crear el análisis
        simulation = StructuralMechanicsAnalysis(model, project_parameters)
        print("[OK] StructuralMechanicsAnalysis creado")
        
        # Inicializar el análisis (esto importará malla, materiales, configurará DOFs, etc.)
        print("Inicializando análisis...")
        simulation.Initialize()
        print("[OK] Análisis inicializado")
        
        # Obtener el ModelPart después de la inicialización
        model_part = model.GetModelPart("Structure")
        
        print(f"Malla cargada: {model_part.NumberOfNodes()} nodos, {model_part.NumberOfElements()} elementos")
        
        # Aplicar condiciones de contorno manualmente después de la inicialización
        print("Aplicando condiciones de contorno manualmente...")
        
        length = 100.0
        force = -100.0
        
        # Cara fija (x=0)
        fixed_count = 0
        for node in model_part.Nodes:
            if abs(node.X) < 0.1:
                node.Fix(Kratos.DISPLACEMENT_X)
                node.Fix(Kratos.DISPLACEMENT_Y)
                node.Fix(Kratos.DISPLACEMENT_Z)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_X, 0.0)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_Y, 0.0)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_Z, 0.0)
                fixed_count += 1
        
        # Cara cargada (x=length) - aplicar fuerza usando SetValue que sí se integra en RHS
        loaded_count = 0
        for node in model_part.Nodes:
            if abs(node.X - length) < 0.1:
                # Usar SetValue para cargas externas (esto sí se integra en el RHS)
                node.SetValue(Kratos.FORCE_Z, force)
                loaded_count += 1
        
        print(f"[OK] Condiciones de contorno aplicadas")
        print(f"Nodos fijados: {fixed_count}")
        print(f"Nodos cargados: {loaded_count}")
        
        # Ejecutar solo el step de solución (sin volver a importar malla)
        print("Ejecutando step de solución...")
        simulation._GetSolver().SolveSolutionStep()
        print("[OK] Step de solución completado")
        
        # Extraer resultados
        max_disp = 0.0
        for node in model_part.Nodes:
            disp_z = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Z)
            if abs(disp_z) > abs(max_disp):
                max_disp = disp_z
        
        print(f"\n=== RESULTADOS ===")
        print(f"Desplazamiento máximo: {max_disp:.6e} m")
        
        # Comparación analítica
        Young_modulus = 68.9e9
        width = 10.0
        height = 10.0
        I = (width * height**3) / 12
        I_m4 = I * 1e-12
        delta_analytical = (abs(force) * (length/1000)**3) / (3 * Young_modulus * I_m4)
        
        print(f"Desplazamiento analítico: {delta_analytical:.6e} m")
        
        error_relativo = abs(abs(max_disp) - delta_analytical) / delta_analytical
        print(f"Error relativo: {error_relativo:.2%}")
        
        if error_relativo < 0.15:
            print("[OK] VALIDACIÓN FEA: PASS")
            return True, {
                'max_displacement': abs(max_disp),
                'analytical_displacement': delta_analytical,
                'relative_error': error_relativo,
                'nodes': model_part.NumberOfNodes(),
                'elements': model_part.NumberOfElements()
            }
        else:
            print("[FAIL] VALIDACIÓN FEA: FAIL")
            return False, {
                'max_displacement': abs(max_disp),
                'analytical_displacement': delta_analytical,
                'relative_error': error_relativo,
                'nodes': model_part.NumberOfNodes(),
                'elements': model_part.NumberOfElements()
            }
        
    except Exception as e:
        print(f"ERROR ejecutando análisis: {e}")
        import traceback
        traceback.print_exc()
        return False, {'error': str(e)}

if __name__ == "__main__":
    success, results = test_definitive_configuration()
    
    print(f"\n=== ESTADO FINAL ===")
    print(f"Resultado: {'PASS' if success else 'FAIL'}")
    
    if success:
        print(f"Desplazamiento máximo: {results['max_displacement']:.6e} m")
        print(f"Desplazamiento analítico: {results['analytical_displacement']:.6e} m")
        print(f"Error relativo: {results['relative_error']:.2%}")
        print(f"Nodos: {results['nodes']}")
        print(f"Elementos: {results['elements']}")
    else:
        print(f"Error: {results.get('error', 'Unknown')}")
