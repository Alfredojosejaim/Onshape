#!/usr/bin/env python3
"""
Script de prueba con configuración completamente manual para evitar duplicación de malla
"""

import os
# Desactivar OpenMP para evitar errores de paralelización
os.environ["OMP_NUM_THREADS"] = "1"

import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication
import json

def test_manual_configuration():
    """
    Prueba con configuración completamente manual
    """
    
    print("=== PRUEBA DE CONFIGURACIÓN MANUAL ===")
    
    # Verificar que los archivos existen
    if not os.path.exists("model/cantilever_beam.mdpa"):
        print("ERROR: No existe model/cantilever_beam.mdpa")
        return False, {'error': 'Mesh file not found'}
    
    if not os.path.exists("MaterialParameters.json"):
        print("ERROR: No existe MaterialParameters.json")
        return False, {'error': 'MaterialParameters.json not found'}
    
    print("[OK] Archivos de configuracion encontrados")
    
    # Validar MaterialParameters.json
    try:
        with open("MaterialParameters.json", "r") as f:
            material_params = json.load(f)
        
        for prop in material_params["properties"]:
            law_name = prop["Material"]["constitutive_law"]["name"]
            print(f"[OK] Constitutive law: {law_name}")
            
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
    
    # Enfoque completamente manual
    try:
        print("\nCreando modelo y malla manualmente...")
        
        model = Kratos.Model()
        model_part = model.CreateModelPart("Structure")
        
        # Configurar variables necesarias (antes de importar malla)
        from KratosMultiphysics import StructuralMechanicsApplication as SMA
        model_part.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
        model_part.AddNodalSolutionStepVariable(Kratos.FORCE)
        model_part.AddNodalSolutionStepVariable(Kratos.REACTION)
        model_part.AddNodalSolutionStepVariable(Kratos.VELOCITY)
        model_part.AddNodalSolutionStepVariable(Kratos.ACCELERATION)
        model_part.AddNodalSolutionStepVariable(SMA.POINT_LOAD)
        
        # Importar malla
        Kratos.ModelPartIO("model/cantilever_beam").ReadModelPart(model_part)
        
        # Escalar de mm a metros
        for node in model_part.Nodes:
            node.X = node.X / 1000.0
            node.Y = node.Y / 1000.0
            node.Z = node.Z / 1000.0
        
        print(f"[OK] Malla importada y escalada: {model_part.NumberOfNodes()} nodos, {model_part.NumberOfElements()} elementos")
        
        # Verificar dimensiones de la malla (ahora en metros)
        x_coords = [node.X for node in model_part.Nodes]
        y_coords = [node.Y for node in model_part.Nodes]
        z_coords = [node.Z for node in model_part.Nodes]
        
        print(f"Rango X: {min(x_coords):.4f} a {max(x_coords):.4f} m")
        print(f"Rango Y: {min(y_coords):.4f} a {max(y_coords):.4f} m")
        print(f"Rango Z: {min(z_coords):.4f} a {max(z_coords):.4f} m")
        
        # Configurar DOFs usando VariableUtils con reacciones correctas
        Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_X, Kratos.REACTION_X, model_part)
        Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_Y, Kratos.REACTION_Y, model_part)
        Kratos.VariableUtils().AddDof(Kratos.DISPLACEMENT_Z, Kratos.REACTION_Z, model_part)
        
        # Importar materiales manualmente
        print("Importando materiales...")
        with open("MaterialParameters.json", "r") as f:
            material_params = json.load(f)
        
        for prop in material_params["properties"]:
            prop_id = prop["properties_id"]
            if prop_id not in model_part.Properties:
                model_part.Properties[prop_id] = Kratos.Properties(prop_id)
            
            properties = model_part.Properties[prop_id]
            
            # Configurar variables materiales (usar unidades SI)
            for var_name, var_value in prop["Material"]["Variables"].items():
                var_enum = getattr(Kratos, var_name)
                properties.SetValue(var_enum, var_value)
            
            # Configurar ley constitutiva
            law_name = prop["Material"]["constitutive_law"]["name"]
            constitutive_law = getattr(StructuralMechanicsApplication, law_name)()
            properties.SetValue(Kratos.CONSTITUTIVE_LAW, constitutive_law)
        
        print("[OK] Materiales importados")
        
        # Configurar condiciones de contorno manualmente
        print("Aplicando condiciones de contorno...")
        
        length = 0.1  # 100 mm en metros
        force = -100.0  # N
        
        # Cara fija (x=0)
        tolerance = 1e-6  # tolerancia en metros
        for node in model_part.Nodes:
            if abs(node.X) < tolerance:
                node.Fix(Kratos.DISPLACEMENT_X)
                node.Fix(Kratos.DISPLACEMENT_Y)
                node.Fix(Kratos.DISPLACEMENT_Z)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_X, 0.0)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_Y, 0.0)
                node.SetSolutionStepValue(Kratos.DISPLACEMENT_Z, 0.0)
        
        # Cara cargada (x=length) - aplicar fuerza usando POINT_LOAD Conditions
        print("Creando POINT_LOAD conditions para nodos cargados...")
        
        loaded_nodes = []
        for node in model_part.Nodes:
            if abs(node.X - length) < tolerance:
                loaded_nodes.append(node.Id)
        
        # Distribuir la fuerza total entre los nodos cargados
        force_per_node = force / len(loaded_nodes) if loaded_nodes else 0.0
        
        for node in model_part.Nodes:
            if abs(node.X - length) < 0.1:
                # Crear condición POINT_LOAD para cada nodo cargado
                condition_id = node.Id + 10000  # Usar ID único para evitar colisiones
                model_part.CreateNewCondition(
                    "PointLoadCondition3D1N",
                    condition_id,
                    [node.Id],
                    model_part.Properties[1]
                )
                
                # Configurar la carga en la condición
                node.SetSolutionStepValue(SMA.POINT_LOAD, [0.0, 0.0, force_per_node])
        
        print(f"[OK] Condiciones de contorno aplicadas")
        print(f"Nodos fijados: {len([n for n in model_part.Nodes if abs(n.X) < 0.1])}")
        print(f"Nodos cargados: {len(loaded_nodes)}")
        print(f"Fuerza total: {force} N")
        print(f"Fuerza por nodo: {force_per_node} N")
        print(f"Conditions POINT_LOAD creadas: {len(loaded_nodes)}")
        
        # Inicializar ProcessInfo
        model_part.ProcessInfo.SetValue(Kratos.TIME, 0.0)
        model_part.ProcessInfo.SetValue(Kratos.DELTA_TIME, 1.0)
        model_part.ProcessInfo.SetValue(Kratos.STEP, 1)
        
        # Inicializar elementos y condiciones (clona la constitutive law en cada punto de Gauss)
        for elem in model_part.Elements:
            elem.Initialize(model_part.ProcessInfo)
        
        for cond in model_part.Conditions:
            cond.Initialize(model_part.ProcessInfo)
        
        print("[OK] Elementos y condiciones inicializados")
        
        print("[OK] Condiciones de contorno aplicadas")
        
        # Configurar solver manualmente
        print("Configurando solver...")
        
        model_part.ProcessInfo.SetValue(Kratos.STEP, 1)
        model_part.ProcessInfo.SetValue(Kratos.TIME, 0.0)
        model_part.ProcessInfo.SetValue(Kratos.DELTA_TIME, 1.0)
        
        linear_solver = Kratos.SkylineLUFactorizationSolver()
        scheme = Kratos.ResidualBasedIncrementalUpdateStaticScheme()
        
        solving_strategy = Kratos.ResidualBasedLinearStrategy(
            model_part,
            scheme,
            linear_solver,
            True,  # ComputeReactions
            True,  # ReformulateDofSet
            True,  # MoveMesh
            True   # CalculateNormDxFlag
        )
        
        solving_strategy = Kratos.ResidualBasedLinearStrategy(
            model_part,
            scheme,
            linear_solver,
            True,  # ComputeReactions
            True,  # ReformulateDofSet
            True,  # MoveMesh
            True   # CalculateNormDxFlag
        )
        
        solving_strategy.Initialize()
        print("[OK] Solver inicializado")
        
        # Resolver
        print("Resolviendo sistema...")
        solving_strategy.Solve()
        print("[OK] Solución completada")
        
        # Extraer resultados
        print("\n=== RESULTADOS ===")
        
        max_disp = 0.0
        for node in model_part.Nodes:
            disp_z = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Z)
            if abs(disp_z) > abs(max_disp):
                max_disp = disp_z
        
        print(f"Desplazamiento máximo: {max_disp:.6e} m")
        
        # Comparación analítica (unidades SI)
        Young_modulus = 68.9e9  # Pa
        width = 0.01  # 10 mm en metros
        height = 0.01  # 10 mm en metros
        length = 0.1  # 100 mm en metros
        force_N = 100.0  # N
        
        I = (width * height**3) / 12  # m^4
        delta_analytical = (force_N * length**3) / (3 * Young_modulus * I)  # m
        
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
    success, results = test_manual_configuration()
    
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
