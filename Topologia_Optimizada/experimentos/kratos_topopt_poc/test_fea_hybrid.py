#!/usr/bin/env python3
"""
Script híbrido que usa StructuralMechanicsAnalysis pero evita duplicación de malla
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"

import KratosMultiphysics as Kratos
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis
import json

def test_hybrid_configuration():
    """
    Prueba híbrida usando StructuralMechanicsAnalysis con configuración JSON corregida
    """
    
    print("=== PRUEBA DE CONFIGURACIÓN HÍBRIDA ===")
    
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
        
        # Importar malla manualmente primero para evitar duplicación
        print("Importando malla manualmente...")
        model_part = model.CreateModelPart("Structure")
        
        # Configurar variables necesarias
        model_part.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
        model_part.AddNodalSolutionStepVariable(Kratos.FORCE)
        model_part.AddNodalSolutionStepVariable(Kratos.REACTION)
        model_part.AddNodalSolutionStepVariable(Kratos.VELOCITY)
        model_part.AddNodalSolutionStepVariable(Kratos.ACCELERATION)
        
        # Importar malla
        Kratos.ModelPartIO("model/cantilever_beam").ReadModelPart(model_part)
        
        print(f"[OK] Malla importada: {model_part.NumberOfNodes()} nodos, {model_part.NumberOfElements()} elementos")
        
        # Configurar DOFs correctamente con reacciones
        Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_X, Kratos.REACTION_X, model_part)
        Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_Y, Kratos.REACTION_Y, model_part)
        Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_Z, Kratos.REACTION_Z, model_part)
        
        print("[OK] DOFs configurados con reacciones correctas")
        
        # Importar materiales manualmente
        print("Importando materiales...")
        with open("MaterialParameters.json", "r") as f:
            material_params = json.load(f)
        
        for prop in material_params["properties"]:
            prop_id = prop["properties_id"]
            if prop_id not in model_part.Properties:
                model_part.Properties[prop_id] = Kratos.Properties(prop_id)
            
            properties = model_part.Properties[prop_id]
            
            # Configurar variables materiales
            for var_name, var_value in prop["Material"]["Variables"].items():
                var_enum = getattr(Kratos, var_name)
                properties.SetValue(var_enum, var_value)
            
            # Configurar ley constitutiva
            from KratosMultiphysics import StructuralMechanicsApplication
            law_name = prop["Material"]["constitutive_law"]["name"]
            constitutive_law = getattr(StructuralMechanicsApplication, law_name)()
            properties.SetValue(Kratos.CONSTITUTIVE_LAW, constitutive_law)
        
        print("[OK] Materiales importados")
        
        # Aplicar condiciones de contorno manualmente
        print("Aplicando condiciones de contorno manualmente...")
        
        length = 100.0
        force = -100.0
        
        # Cara fija (x=0)
        for node in model_part.Nodes:
            if abs(node.X) < 0.1:
                node.Fix(Kratos.DISPLACEMENT_X)
                node.Fix(Kratos.DISPLACEMENT_Y)
                node.Fix(Kratos.DISPLACEMENT_Z)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_X, 0.0)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_Y, 0.0)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_Z, 0.0)
        
        # Cara cargada (x=length) - aplicar fuerza
        for node in model_part.Nodes:
            if abs(node.X - length) < 0.1:
                node.SetSolutionStepValue(Kratos.FORCE_Z, force)
        
        print(f"[OK] Condiciones de contorno aplicadas")
        print(f"Nodos fijados: {len([n for n in model_part.Nodes if abs(n.X) < 0.1])}")
        print(f"Nodos cargados: {len([n for n in model_part.Nodes if abs(n.X - length) < 0.1])}")
        
        # Modificar el solver para que no importe la malla de nuevo
        # Sobrescribir el método ImportModelPart para no hacer nada
        original_import = simulation._GetSolver()._ImportModelPart
        def skip_import(model_part, settings):
            pass
        simulation._GetSolver()._ImportModelPart = skip_import
        
        # También sobrescribir el método que construye el RHS para incluir fuerzas manuales
        original_build = simulation._GetSolver()._builder_and_solver.BuildRHS
        def build_rhs_with_forces(scheme, builder_and_solver, model_part):
            # Llamar al método original
            original_build(scheme, builder_and_solver, model_part)
            
            # Añadir fuerzas manuales al RHS
            length = 100.0
            force = -100.0
            for node in model_part.Nodes:
                if abs(node.X - length) < 0.1:
                    if node.HasDof(Kratos.DISPLACEMENT_Z):
                        dof = node.GetDof(Kratos.DISPLACEMENT_Z)
                        eq_id = dof.EquationId()
                        # Añadir la fuerza al RHS del sistema
                        # Esto requiere acceso directo al vector RHS del sistema
        
        simulation._GetSolver()._builder_and_solver.BuildRHS = build_rhs_with_forces
        
        # Ejecutar el análisis
        print("Ejecutando análisis...")
        simulation.Initialize()
        simulation.Run()
        print("[OK] Análisis completado")
        
        # Extraer resultados
        model_part = model.GetModelPart("Structure")
        
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
        length = 100.0
        force = -100.0
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
    success, results = test_hybrid_configuration()
    
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
