#!/usr/bin/env python3
"""
Script para probar FEA básico sin optimización usando API directa de Kratos
PoC Kratos Topological Optimization 3D
"""

import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication
import gmsh
import numpy as np
import os

def run_basic_fea():
    """
    Ejecuta análisis FEA básico de viga en voladizo usando API directa de Kratos
    """
    
    print("=== INICIANDO ANÁLISIS FEA BÁSICO ===")
    
    # Primero generar malla si no existe
    if not os.path.exists("model/cantilever_beam.msh"):
        print("Generando malla...")
        from generate_mesh import generate_cantilever_beam_mesh
        generate_cantilever_beam_mesh()
    
    # Crear modelo Kratos
    model = Kratos.Model()
    model_part = model.CreateModelPart("Structure")
    
    # Configurar variables antes de crear nodos
    model_part.AddNodalSolutionStepVariable(Kratos.DISPLACEMENT)
    model_part.AddNodalSolutionStepVariable(Kratos.FORCE)
    model_part.AddNodalSolutionStepVariable(Kratos.REACTION)
    model_part.AddNodalSolutionStepVariable(Kratos.VELOCITY)
    
    # Cargar malla desde Gmsh
    gmsh.initialize()
    gmsh.open("model/cantilever_beam.msh")
    
    # Importar nodos
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    for i, tag in enumerate(node_tags):
        x = node_coords[3*i]
        y = node_coords[3*i + 1]
        z = node_coords[3*i + 2]
        model_part.CreateNewNode(i+1, x, y, z)
    
    # Importar elementos Tet4
    element_types = gmsh.model.mesh.getElementTypes()
    element_type_3d = None
    for et in element_types:
        if et == 4:  # Tet4
            element_type_3d = et
            break
    
    if element_type_3d:
        element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
        
        tet_elements = None
        for i, et in enumerate(element_types):
            if et == 4:
                tet_elements = element_connectivity[i]
                break
        
        if tet_elements is not None:
            material_properties = Kratos.Properties(1)
            Young_modulus = 68.9e9  # Pa (aluminio)
            Poisson_ratio = 0.33
            
            material_properties.SetValue(Kratos.YOUNG_MODULUS, Young_modulus)
            material_properties.SetValue(Kratos.POISSON_RATIO, Poisson_ratio)
            
            # Agregar ley constitutiva (constitutive law) usando el método correcto
            try:
                # Intentar diferentes formas de crear la ley constitutiva
                constitutive_law = Kratos.ConstitutiveLaw()
                material_properties.SetValue(Kratos.CONSTITUTIVE_LAW, constitutive_law)
            except:
                try:
                    # Método alternativo usando el registro de leyes constitutivas
                    constitutive_law = Kratos.KratosGlobals.GetRegistry("ConstitutiveLaw")
                    material_properties.SetValue(Kratos.CONSTITUTIVE_LAW, constitutive_law)
                except:
                    print("Advertencia: No se pudo configurar ley constitutiva, intentando sin ella")
            
            for i in range(0, len(tet_elements), 4):
                elem_id = i//4 + 1
                node_ids = [int(tet_elements[i+j]) for j in range(4)]
                model_part.CreateNewElement("SmallDisplacementElement3D4N", elem_id, node_ids, material_properties)
    
    gmsh.finalize()
    
    print(f"Malla cargada: {model_part.NumberOfNodes()} nodos, {model_part.NumberOfElements()} elementos")
    
    # Configurar DOFs
    for node in model_part.Nodes:
        node.AddDof(Kratos.DISPLACEMENT_X)
        node.AddDof(Kratos.DISPLACEMENT_Y)
        node.AddDof(Kratos.DISPLACEMENT_Z)
    
    # Parámetros del problema
    length = 100.0  # mm
    width = 10.0    # mm
    height = 10.0   # mm
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
    
    # Configurar solver usando un enfoque simplificado
    print("\nConfigurando solver...")
    
    # Crear esquema de tiempo
    model_part.ProcessInfo.SetValue(Kratos.STEP, 1)
    model_part.ProcessInfo.SetValue(Kratos.TIME, 0.0)
    
    # Crear solver lineal simplificado
    try:
        linear_solver = Kratos.SkylineLUSolver()
    except:
        try:
            linear_solver = Kratos.SkylineLUFactorizationSolver()
        except:
            print("Error creando solver lineal, intentando alternativa...")
            linear_solver = Kratos.SuperLUSolver()
    
    # Crear esquema y criterio de convergencia simplificados
    try:
        scheme = Kratos.ResidualBasedIncrementalUpdateStaticScheme()
        
        # Usar la firma correcta del constructor según el error:
        # Kratos.ResidualBasedLinearStrategy(arg0: ModelPart, arg1: Scheme, arg2: LinearSolver, arg3: bool, arg4: bool, arg5: bool, arg6: bool)
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
        print("Intentando enfoque alternativo...")
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
    
    # Calcular reacción total en los nodos fijos
    total_reaction = 0.0
    for node_id in fixed_nodes:
        node = model_part.GetNode(node_id)
        reaction_z = node.GetSolutionStepValue(Kratos.REACTION_Z)
        total_reaction += reaction_z
    
    print(f"Reacción total en soporte: {total_reaction:.6e} N")
    
    # Calcular strain energy si está disponible
    try:
        strain_energy = 0.0
        for element in model_part.Elements:
            try:
                element_energy = element.Calculate(Kratos.STRAIN_ENERGY, model_part.ProcessInfo)
                strain_energy += element_energy
            except:
                pass
        
        print(f"Strain energy total: {strain_energy:.6e} J")
    except Exception as e:
        print(f"No se pudo calcular strain energy: {e}")
    
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
            'total_reaction': total_reaction,
            'nodes': model_part.NumberOfNodes(),
            'elements': model_part.NumberOfElements()
        }
    else:
        print("[FAIL] VALIDACIÓN FEA: FAIL - Error fuera de límite aceptable")
        return False, {
            'max_displacement': abs(max_disp),
            'analytical_displacement': delta_analytical,
            'relative_error': error_relativo,
            'total_reaction': total_reaction,
            'nodes': model_part.NumberOfNodes(),
            'elements': model_part.NumberOfElements()
        }

if __name__ == "__main__":
    success, results = run_basic_fea()
    
    print("\n=== PRUEBA FEA COMPLETADA ===")
    print(f"Estado: {'PASS' if success else 'FAIL'}")
    if 'error' in results:
        print(f"Error: {results['error']}")
    else:
        print(f"Error relativo: {results['relative_error']:.2%}")
        print(f"Desplazamiento FEA: {results['max_displacement']:.6e} m")
        print(f"Desplazamiento analítico: {results['analytical_displacement']:.6e} m")