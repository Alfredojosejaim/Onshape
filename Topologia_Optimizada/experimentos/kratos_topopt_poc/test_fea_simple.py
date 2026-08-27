#!/usr/bin/env python3
"""
Script simplificado usando el enfoque correcto para Kratos 10.4.3
Basado en documentación oficial
"""

import KratosMultiphysics as Kratos
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis
import os

def run_simple_fea():
    """
    Ejecuta análisis FEA con configuración mínima correcta
    """
    
    print("=== INICIANDO ANÁLISIS FEA SIMPLIFICADO ===")
    
    # Verificar malla
    if not os.path.exists("model/cantilever_beam.mdpa"):
        print("Convirtiendo malla a MDPA...")
        from generate_mesh import generate_cantilever_beam_mesh
        if not os.path.exists("model/cantilever_beam.msh"):
            generate_cantilever_beam_mesh()
        
        import gmsh
        gmsh.initialize()
        gmsh.open("model/cantilever_beam.msh")
        
        node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
        element_types = gmsh.model.mesh.getElementTypes()
        
        with open("model/cantilever_beam.mdpa", "w") as f:
            # Eliminar ModelPartData por ahora
            # f.write("Begin ModelPartData\n")
            # f.write("  1\n")
            # f.write("End ModelPartData\n\n")
            
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
            
            element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
            
            tet_elements = None
            for i, et in enumerate(element_types):
                if et == 4:
                    tet_elements = element_connectivity[i]
                    break
            
            if tet_elements is not None:
                f.write("Begin Elements SmallDisplacementElement3D4N\n")
                for i in range(0, len(tet_elements), 4):
                    elem_id = i//4 + 1
                    node_ids = [int(tet_elements[i+j]) for j in range(4)]
                    f.write(f"  {elem_id}  1  {' '.join(map(str, node_ids))}\n")
                f.write("End Elements\n\n")
        
        gmsh.finalize()
        print("Malla convertida")
    
    # Configuración mínima JSON correcta para Kratos 10.4.3
    # Ajustada a los tipos de solver disponibles: static, dynamic, eigen_value, harmonic_analysis, formfinding, adjoint_static, prebuckling
    json_config = """{
    "problem_data": {
        "problem_name": "cantilever_beam",
        "parallel_type": "OpenMP",
        "echo_level": 1
    },
    "solver_settings": {
        "solver_type": "static",
        "analysis_type": "linear",
        "echo_level": 1,
        "model_part_name": "Structure",
        "domain_size": 3,
        "model_import_settings": {
            "input_type": "mdpa",
            "input_filename": "model/cantilever_beam"
        },

        "time_stepping": {
            "time_step": 1.0
        },
        "max_iteration": 30,
        "convergence_criterion": "displacement_criterion",
        "displacement_relative_tolerance": 1e-6,
        "displacement_absolute_tolerance": 1e-6,
        "linear_solver_settings": {
            "solver_type": "skyline_lu_factorization",
            "scaling": false,
            "tolerance": 1e-6
        },
        "compute_reactions": true,
        "move_mesh_flag": true
    },
    "processes": {
        "constraints_process_list": [],
        "loads_process_list": []
    }
}"""
    
    # Guardar configuración
    with open("ProjectParameters_simple.json", "w") as f:
        f.write(json_config)
    
    # Cargar parámetros
    project_parameters = Kratos.Parameters(json_config)
    
    print("Parámetros cargados")
    
    # Crear análisis
    model = Kratos.Model()
    
    try:
        simulation = StructuralMechanicsAnalysis(model, project_parameters)
        print("Análisis creado")
    except Exception as e:
        print(f"Error creando análisis: {e}")
        return False, {'error': str(e)}
    
    # Ejecutar - pero primero aplicar condiciones de contorno manualmente
    print("Aplicando condiciones de contorno manualmente...")
    
    try:
        # El análisis inicializa el ModelPart pero no lo resuelve todavía
        simulation.Initialize()
        print("Análisis inicializado")
        
        # Obtener el ModelPart
        model_part = model.GetModelPart("Structure")
        
        # Aplicar condiciones de contorno directamente
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
        
        # Cara cargada (x=length)
        for node in model_part.Nodes:
            if abs(node.X - length) < 0.1:
                force_vector = Kratos.Array3([0.0, 0.0, force])
                node.SetSolutionStepValue(Kratos.FORCE, force_vector)
        
        print("Condiciones de contorno aplicadas")
        
        # Ejecutar el solver
        print("Ejecutando solver...")
        simulation.Run()
        print("Análisis completado")
        
    except Exception as e:
        print(f"Error ejecutando: {e}")
        return False, {'error': str(e)}
    
    # Resultados
    model_part = model.GetModelPart("Structure")
    
    max_disp = 0.0
    for node in model_part.Nodes:
        disp_z = node.GetSolutionStepValue(Kratos.DISPLACEMENT_Z)
        if abs(disp_z) > abs(max_disp):
            max_disp = disp_z
    
    print(f"Desplazamiento máximo: {max_disp:.6e} m")
    
    # Comparación analítica
    length = 100.0
    width = 10.0
    height = 10.0
    force = -100.0
    Young_modulus = 68.9e9
    
    I = (width * height**3) / 12
    I_m4 = I * 1e-12
    delta_analytical = (abs(force) * (length/1000)**3) / (3 * Young_modulus * I_m4)
    
    error_relativo = abs(abs(max_disp) - delta_analytical) / delta_analytical
    
    print(f"Desplazamiento analítico: {delta_analytical:.6e} m")
    print(f"Error relativo: {error_relativo:.2%}")
    
    if error_relativo < 0.15:
        print("[OK] PASS")
        return True, {
            'max_displacement': abs(max_disp),
            'analytical_displacement': delta_analytical,
            'relative_error': error_relativo
        }
    else:
        print("[FAIL] Error fuera de límite")
        return False, {
            'max_displacement': abs(max_disp),
            'analytical_displacement': delta_analytical,
            'relative_error': error_relativo
        }

if __name__ == "__main__":
    success, results = run_simple_fea()
    print(f"\nEstado: {'PASS' if success else 'FAIL'}")
    if 'error' in results:
        print(f"Error: {results['error']}")