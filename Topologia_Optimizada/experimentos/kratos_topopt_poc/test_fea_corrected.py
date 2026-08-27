#!/usr/bin/env python3
"""
Script de prueba con configuración corregida basada en el checklist
"""

import KratosMultiphysics as Kratos
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis
import json
import os

def test_corrected_configuration():
    """
    Prueba la configuración corregida siguiendo el checklist
    """
    
    print("=== PRUEBA DE CONFIGURACIÓN CORREGIDA ===")
    
    # Verificar que los archivos existen
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
    
    # Cargar y validar ProjectParameters.json
    try:
        with open("ProjectParameters.json", "r") as f:
            project_params = json.load(f)
        
        # Verificar materiales_filename
        materials_filename = project_params["solver_settings"]["material_import_settings"]["materials_filename"]
        print(f"[OK] materials_filename: {materials_filename}")
        
        # Verificar model_part_name
        model_part_name = project_params["solver_settings"]["model_part_name"]
        print(f"[OK] model_part_name: {model_part_name}")
        
    except Exception as e:
        print(f"ERROR leyendo ProjectParameters.json: {e}")
        return False, {'error': str(e)}
    
    # Cargar y validar MaterialParameters.json
    try:
        with open("MaterialParameters.json", "r") as f:
            material_params = json.load(f)
        
        # Verificar estructura
        if "properties" not in material_params:
            print("ERROR: MaterialParameters.json no tiene 'properties'")
            return False, {'error': 'Invalid material structure'}
        
        for prop in material_params["properties"]:
            if "model_part_name" not in prop:
                print("ERROR: Property sin model_part_name")
                return False, {'error': 'Missing model_part_name in property'}
            
            if prop["model_part_name"] != model_part_name:
                print(f"ERROR: model_part_name mismatch: {prop['model_part_name']} != {model_part_name}")
                return False, {'error': 'model_part_name mismatch'}
            
            if "Material" not in prop:
                print("ERROR: Property sin Material")
                return False, {'error': 'Missing Material in property'}
            
            if "constitutive_law" not in prop["Material"]:
                print("ERROR: Material sin constitutive_law")
                return False, {'error': 'Missing constitutive_law'}
            
            law_name = prop["Material"]["constitutive_law"]["name"]
            print(f"[OK] Constitutive law: {law_name}")
            
            if "Variables" not in prop["Material"]:
                print("ERROR: Material sin Variables")
                return False, {'error': 'Missing Variables'}
            
            variables = prop["Material"]["Variables"]
            required_vars = ["DENSITY", "YOUNG_MODULUS", "POISSON_RATIO"]
            for var in required_vars:
                if var not in variables:
                    print(f"ERROR: Variable requerida faltante: {var}")
                    return False, {'error': f'Missing required variable: {var}'}
            
            print(f"[OK] Variables requeridas presentes: {required_vars}")
        
    except Exception as e:
        print(f"ERROR leyendo MaterialParameters.json: {e}")
        return False, {'error': str(e)}
    
    print("\n=== TODAS LAS VALIDACIONES PASARON ===")
    
    # Intentar ejecutar el análisis
    try:
        print("\nIntentando ejecutar StructuralMechanicsAnalysis...")
        
        with open("ProjectParameters.json", "r") as f:
            json_content = f.read()
        
        project_parameters = Kratos.Parameters(json_content)
        
        model = Kratos.Model()
        simulation = StructuralMechanicsAnalysis(model, project_parameters)
        
        print("[OK] StructuralMechanicsAnalysis creado")
        
        simulation.Initialize()
        print("[OK] Análisis inicializado")
        
        simulation.Run()
        print("[OK] Análisis completado")
        
        # Extraer resultados
        model_part = model.GetModelPart(model_part_name)
        
        max_disp = 0.0
        for node in model_part.Nodes:
            disp_z = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Z)
            if abs(disp_z) > abs(max_disp):
                max_disp = disp_z
        
        print(f"\n=== RESULTADOS ===")
        print(f"Desplazamiento máximo: {max_disp:.6e} m")
        
        return True, {
            'max_displacement': abs(max_disp),
            'nodes': model_part.NumberOfNodes(),
            'elements': model_part.NumberOfElements()
        }
        
    except Exception as e:
        print(f"ERROR ejecutando análisis: {e}")
        import traceback
        traceback.print_exc()
        return False, {'error': str(e)}

if __name__ == "__main__":
    success, results = test_corrected_configuration()
    
    print(f"\n=== ESTADO FINAL ===")
    print(f"Resultado: {'PASS' if success else 'FAIL'}")
    
    if success:
        print(f"Desplazamiento máximo: {results['max_displacement']:.6e} m")
        print(f"Nodos: {results['nodes']}")
        print(f"Elementos: {results['elements']}")
    else:
        print(f"Error: {results.get('error', 'Unknown')}")
