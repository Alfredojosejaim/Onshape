#!/usr/bin/env python3
"""
Script para importar malla Gmsh a Kratos ModelPart
PoC Kratos Topological Optimization 3D
"""

import KratosMultiphysics as Kratos
from KratosMultiphysics import StructuralMechanicsApplication
import os
import gmsh

def import_mesh_to_kratos(msh_file):
    """
    Importa malla desde archivo MSH a Kratos ModelPart usando Gmsh directamente
    """
    
    # Inicializar Kratos
    Kratos.Logger.GetDefaultOutput().SetSeverity(Kratos.Logger.Severity.WARNING)
    
    # Crear Model y ModelPart principal
    model = Kratos.Model()
    model_part = model.CreateModelPart("MainModelPart")
    
    print("=== IMPORTANDO MALLA A KRATOS ===")
    
    # Método: Importación manual desde Gmsh
    gmsh.initialize()
    gmsh.open(msh_file)
    
    # Obtener nodos
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    
    print(f"Importando {len(node_tags)} nodos desde Gmsh...")
    
    # Crear nodos en Kratos
    for i, tag in enumerate(node_tags):
        x = node_coords[3*i]
        y = node_coords[3*i + 1]
        z = node_coords[3*i + 2]
        model_part.CreateNewNode(i+1, x, y, z)
    
    # Obtener elementos 3D (tipo 4 = Tet4)
    element_types = gmsh.model.mesh.getElementTypes()
    element_type_3d = None
    for et in element_types:
        if et == 4:  # Tet4
            element_type_3d = et
            break
    
    if element_type_3d:
        element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
        
        # Buscar elementos Tet4 (índice correspondiente a tipo 4)
        tet_elements = None
        for i, et in enumerate(element_types):
            if et == 4:
                tet_elements = element_connectivity[i]
                break
        
        if tet_elements is not None:
            num_tet_elements = len(tet_elements)//4
            print(f"Importando {num_tet_elements} elementos Tet4...")
            
            # Configurar propiedades del material
            material_properties = Kratos.Properties(1)
            
            # Propiedades del aluminio
            Young_modulus = 68.9e9  # Pa
            Poisson_ratio = 0.33
            
            material_properties.SetValue(Kratos.YOUNG_MODULUS, Young_modulus)
            material_properties.SetValue(Kratos.POISSON_RATIO, Poisson_ratio)
            
            # Usar el elemento genérico de Kratos para sólidos 3D
            # Kratos tiene diferentes elementos, usaremos "SmallDisplacementElement3D4N"
            element_name = "SmallDisplacementElement3D4N"
            
            for i in range(0, len(tet_elements), 4):
                elem_id = i//4 + 1
                # Los IDs de nodos de Gmsh son 1-based igual que Kratos
                node_ids = [int(tet_elements[i+j]) for j in range(4)]
                
                try:
                    model_part.CreateNewElement(element_name, elem_id, node_ids, material_properties)
                except Exception as e:
                    print(f"Error creando elemento {elem_id}: {e}")
                    # Intentar con otro nombre de elemento
                    if i == 0:  # Solo probar alternativas en el primer error
                        alternative_names = ["Element3D4N", "TetrahedralElement3D4N"]
                        for alt_name in alternative_names:
                            try:
                                model_part.CreateNewElement(alt_name, elem_id, node_ids, material_properties)
                                element_name = alt_name
                                print(f"Usando elemento alternativo: {alt_name}")
                                break
                            except:
                                continue
            
            print("Elementos creados exitosamente")
    else:
        print("No se encontraron elementos Tet4")
    
    gmsh.finalize()
    
    # Verificar la importación
    print("\n=== VERIFICACIÓN DE IMPORTACIÓN ===")
    print(f"Nodos en ModelPart: {model_part.NumberOfNodes()}")
    print(f"Elementos en ModelPart: {model_part.NumberOfElements()}")
    
    # Configurar DOFs
    print("\nConfigurando DOFs...")
    for node in model_part.Nodes:
        node.AddDof(Kratos.DISPLACEMENT_X)
        node.AddDof(Kratos.DISPLACEMENT_Y)
        node.AddDof(Kratos.DISPLACEMENT_Z)
    
    print("DOFs configurados")
    
    # Calcular total de DOFs
    total_dofs = model_part.NumberOfNodes() * 3
    print(f"Total DOFs: {total_dofs}")
    
    return model_part

if __name__ == "__main__":
    unv_file = "model/cantilever_beam.unv"
    
    if not os.path.exists(unv_file):
        print(f"Error: Archivo {unv_file} no encontrado")
        print("Ejecute primero generate_mesh.py")
    else:
        model_part = import_mesh_to_kratos(unv_file)
        print("\n=== IMPORTACIÓN COMPLETADA ===")