#!/usr/bin/env python3
"""
Script para probar FEA usando el módulo gmsh_io de Kratos
PoC Kratos Topological Optimization 3D
"""

import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication
import os

def run_fea_with_gmsh_io():
    """
    Ejecuta análisis FEA usando el módulo gmsh_io de Kratos
    """
    
    print("=== INICIANDO ANÁLISIS FEA CON GMSH_IO ===")
    
    # Importar módulo gmsh_io
    try:
        from KratosMultiphysics.GmshIO import ModelPartIO
        print("Módulo gmsh_io importado correctamente")
    except ImportError as e:
        print(f"Error importando gmsh_io: {e}")
        return False, {'error': f"No se pudo importar gmsh_io: {e}"}
    
    # Crear modelo Kratos
    model = Kratos.Model()
    model_part = model.CreateModelPart("Structure")
    
    # Configurar variables necesarias
    model_part.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
    model_part.AddNodalSolutionStepVariable(Kratos.FORCE)
    model_part.AddNodalSolutionStepVariable(Kratos.REACTION)
    model_part.AddNodalSolutionStepVariable(Kratos.VELOCITY)
    model_part.AddNodalSolutionStepVariable(Kratos.ACCELERATION)
    
    # Intentar importar malla directamente desde archivo .msh
    try:
        # Intentar diferentes métodos de importación
        model_io = ModelPartIO("model/cantilever_beam.msh")
        model_io.ReadModelPart(model_part)
        print(f"Malla importada: {model_part.NumberOfNodes()} nodos, {model_part.NumberOfElements()} elementos")
    except Exception as e:
        print(f"Error importando malla: {e}")
        # Intentar con nombre sin extensión
        try:
            model_io = ModelPartIO("model/cantilever_beam")
            model_io.ReadModelPart(model_part)
            print(f"Malla importada (segundo intento): {model_part.NumberOfNodes()} nodos, {model_part.NumberOfElements()} elementos")
        except Exception as e2:
            print(f"Error en segundo intento: {e2}")
            return False, {'error': f"No se pudo importar malla: {e2}"}
    
    # Configurar material
    material_properties = Kratos.Properties(1)
    Young_modulus = 68.9e9  # Pa (aluminio)
    Poisson_ratio = 0.33
    
    material_properties.SetValue(Kratos.YOUNG_MODULUS, Young_modulus)
    material_properties.SetValue(Kratos.POISSON_RATIO, Poisson_ratio)
    
    # Configurar ley constitutiva
    try:
        constitutive_law = StructuralMechanicsApplication.LinearElastic3DLaw()
        material_properties.SetValue(Kratos.CONSTITUTIVE_LAW, constitutive_law)
        print("Ley constitutiva configurada")
    except Exception as e:
        print(f"Error configurando ley constitutiva: {e}")
        return False, {'error': str(e)}
    
    # Asignar propiedades a elementos
    for element in model_part.Elements:
        element.Properties = material_properties
    
    # Configurar DOFs
    for node in model_part.Nodes:
        node.AddDof(Kratos.DISPLACEMENT_X)
        node.AddDof(Kratos.DISPLACEMENT_Y)
        node.AddDof(Kratos.DISPLACEMENT_Z)
    
    # Parámetros del problema
    length = 100.0  # mm
    force = -100.0  # N (carga vertical negativa)
    
    # Aplicar condiciones de contorno
    print("\nAplicando condiciones de contorno...")
    
    # Cara fija (x=0): fijar todos los desplazamientos
    fixed_nodes = []
    for node in model_part.Nodes:
        if abs(node.X) < 0.1:  # Cara x=0
            node.Fix(Kratos.DISPLACEMENT_X)
            node.Fix(Kratos.DISPLACEMENT_Y)
            node.Fix(Kratos.DISPLACEMENT_Z)
            node.SetSolutionStepValue(Kratos.DISPLACEMENT_X, 0.0)
            node.SetSolutionStepValue(Kratos.DISPLACEMENT_Y, 0.0)
            node.SetSolutionStepValue(Kratos.DISPLACEMENT_Z, 0.0)
            fixed_nodes.append(node.Id)
    
    print(f"Nodos fijados: {len(fixed_nodes)}")
    
    # Cara cargada (x=length): aplicar carga vertical
    loaded_nodes = []
    for node in model_part.Nodes:
        if abs(node.X - length) < 0.1:  # Cara x=length
            force_vector = Kratos.Array3([0.0, 0.0, force])
            node.SetSolutionStepValue(Kratos.FORCE, force_vector)
            loaded_nodes.append(node.Id)
    
    print(f"Nodos cargados: {len(loaded_nodes)}")
    
    # Configurar solver
    print("\nConfigurando solver...")
    
    model_part.ProcessInfo.SetValue(Kratos.STEP, 1)
    model_part.ProcessInfo.SetValue(Kratos.TIME, 0.0)
    
    try:
        linear_solver = Kratos.SkylineLUSolver()
    except:
        try:
            linear_solver = Kratos.SkylineLUFactorizationSolver()
        except:
            print("Error creando solver lineal")
            return False, {'error': "No se pudo crear solver lineal"}
    
    try:
        scheme = Kratos.ResidualBasedIncrementalUpdateStaticScheme()
        solving_strategy = Kratos.ResidualBasedLinearStrategy(
            model_part,
            scheme,
            linear_solver,
            True,  # ComputeReactions
            True,  # ReformulateDofSet
            True,  # MoveMesh
            False  # CalculateNormDxFlag
        )
    except Exception as e:
        print(f"Error configurando estrategia: {e}")
        return False, {'error': str(e)}
    
    try:
        solving_strategy.Initialize()
        print("Solver inicializado")
    except Exception as e:
        print(f"Error inicializando solver: {e}")
        return False, {'error': str(e)}
    
    # Resolver
    print("\nResolviendo sistema K*u = F...")
    try:
        solving_strategy.Solve()
        print("Solución completada")
    except Exception as e:
        print(f"Error resolviendo: {e}")
        return False, {'error': str(e)}
    
    # Extraer resultados
    print("\n=== RESULTADOS FEA ===")
    
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
    
    # Comparar con solución analítica
    print("\n=== COMPARACIÓN CON SOLUCIÓN ANALÍTICA ===")
    
    width = 10.0    # mm
    height = 10.0   # mm
    
    I = (width * height**3) / 12  # Momento de inercia (mm^4)
    I_m4 = I * 1e-12  # Convertir a m^4
    
    delta_analytical = (abs(force) * (length/1000)**3) / (3 * Young_modulus * I_m4)
    
    print(f"Desplazamiento analítico: {delta_analytical:.6e} m")
    print(f"Desplazamiento FEA: {abs(max_disp):.6e} m")
    
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

if __name__ == "__main__":
    success, results = run_fea_with_gmsh_io()
    
    print("\n=== PRUEBA FEA COMPLETADA ===")
    print(f"Estado: {'PASS' if success else 'FAIL'}")
    if 'error' in results:
        print(f"Error: {results['error']}")
    else:
        print(f"Error relativo: {results['relative_error']:.2%}")
        print(f"Desplazamiento FEA: {results['max_displacement']:.6e} m")
        print(f"Desplazamiento analítico: {results['analytical_displacement']:.6e} m")