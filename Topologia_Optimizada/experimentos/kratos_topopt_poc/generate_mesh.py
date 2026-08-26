#!/usr/bin/env python3
"""
Script para generar malla volumétrica Tet4 de viga en voladizo usando Gmsh
PoC Kratos Topological Optimization 3D
"""

import gmsh
import numpy as np
import os

def generate_cantilever_beam_mesh():
    """
    Genera malla volumétrica Tet4 para viga en voladizo
    
    Especificaciones:
    - Longitud: 100 mm
    - Sección: 10 mm × 10 mm
    - Elementos: Tetraédricos lineales de 4 nodos (Tet4)
    """
    
    # Inicializar Gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    
    # Crear modelo
    gmsh.model.add("cantilever_beam")
    
    # Parámetros geométricos (en mm)
    length = 100.0
    width = 10.0
    height = 10.0
    
    # Crear puntos (esquinas del bloque)
    p1 = gmsh.model.occ.addPoint(0, 0, 0, 0.0)
    p2 = gmsh.model.occ.addPoint(length, 0, 0, 0.0)
    p3 = gmsh.model.occ.addPoint(length, width, 0, 0.0)
    p4 = gmsh.model.occ.addPoint(0, width, 0, 0.0)
    p5 = gmsh.model.occ.addPoint(0, 0, height, 0.0)
    p6 = gmsh.model.occ.addPoint(length, 0, height, 0.0)
    p7 = gmsh.model.occ.addPoint(length, width, height, 0.0)
    p8 = gmsh.model.occ.addPoint(0, width, height, 0.0)
    
    # Crear líneas
    l1 = gmsh.model.occ.addLine(p1, p2)
    l2 = gmsh.model.occ.addLine(p2, p3)
    l3 = gmsh.model.occ.addLine(p3, p4)
    l4 = gmsh.model.occ.addLine(p4, p1)
    l5 = gmsh.model.occ.addLine(p5, p6)
    l6 = gmsh.model.occ.addLine(p6, p7)
    l7 = gmsh.model.occ.addLine(p7, p8)
    l8 = gmsh.model.occ.addLine(p8, p5)
    l9 = gmsh.model.occ.addLine(p1, p5)
    l10 = gmsh.model.occ.addLine(p2, p6)
    l11 = gmsh.model.occ.addLine(p3, p7)
    l12 = gmsh.model.occ.addLine(p4, p8)
    
    # Crear superficies (caras)
    c1 = gmsh.model.occ.addCurveLoop([l1, l2, l3, l4])
    s1 = gmsh.model.occ.addPlaneSurface([c1])
    
    c2 = gmsh.model.occ.addCurveLoop([l5, l6, l7, l8])
    s2 = gmsh.model.occ.addPlaneSurface([c2])
    
    c3 = gmsh.model.occ.addCurveLoop([l1, l10, l5, -l9])
    s3 = gmsh.model.occ.addPlaneSurface([c3])
    
    c4 = gmsh.model.occ.addCurveLoop([l2, l11, l6, -l10])
    s4 = gmsh.model.occ.addPlaneSurface([c4])
    
    c5 = gmsh.model.occ.addCurveLoop([l3, l12, l7, -l11])
    s5 = gmsh.model.occ.addPlaneSurface([c5])
    
    c6 = gmsh.model.occ.addCurveLoop([l4, l9, l8, -l12])
    s6 = gmsh.model.occ.addPlaneSurface([c6])
    
    # Crear volumen
    sl = gmsh.model.occ.addSurfaceLoop([s1, s2, s3, s4, s5, s6])
    vol = gmsh.model.occ.addVolume([sl])
    
    # Sincronizar modelo
    gmsh.model.occ.synchronize()
    
    # Definir grupos físicos para condiciones de contorno
    # Cara fija (x=0): fijar todos los grados de libertad
    fixed_face = gmsh.model.addPhysicalGroup(2, [s1])
    gmsh.model.setPhysicalName(2, fixed_face, "FixedFace")
    
    # Cara cargada (x=length): aplicar carga vertical
    loaded_face = gmsh.model.occ.addSurfaceLoop([s2])
    loaded_face_tag = gmsh.model.addPhysicalGroup(2, [s2])
    gmsh.model.setPhysicalName(2, loaded_face_tag, "LoadedFace")
    
    # Volumen
    volume_group = gmsh.model.addPhysicalGroup(3, [vol])
    gmsh.model.setPhysicalName(3, volume_group, "BeamVolume")
    
    # Configurar malla
    # Tamaño de elemento más fino para mejor precisión
    mesh_size = 2.0  # mm
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
    
    # Forzar elementos tetraédricos
    gmsh.option.setNumber("Mesh.Algorithm", 6)  # Frontal-Delaunay para 3D
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)  # Delaunay
    
    # Generar malla
    gmsh.model.mesh.generate(3)
    
    # Verificar tipo de elementos
    element_types = gmsh.model.mesh.getElementTypes()
    print(f"Tipos de elementos generados: {element_types}")
    
    # Obtener estadísticas de malla
    node_tags = gmsh.model.mesh.getNodes()[0]
    element_tags = gmsh.model.mesh.getElements()[2]
    
    num_nodes = len(node_tags)
    num_elements = len(element_tags[0]) if element_tags else 0
    
    print(f"\n=== ESTADÍSTICAS DE MALLA ===")
    print(f"Nodos: {num_nodes}")
    print(f"Elementos: {num_elements}")
    
    # Identificar tipo de elemento 3D (Tet4 es tipo 4 en Gmsh)
    element_type_3d = None
    for et in element_types:
        if et == 4:  # Tet4 en Gmsh
            element_type_3d = et
            break
    
    print(f"Tipo de elemento 3D: {element_type_3d if element_type_3d else 'No Tet4 encontrado'}")
    
    # Obtener información de conectividad para verificación
    if element_type_3d:
        element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
        # Buscar elementos 3D (índice 2 en el resultado)
        if len(element_connectivity) > 2:
            print(f"Conectividad de elementos 3D (primeros 5):")
            for i in range(min(5, len(element_connectivity[2]))):
                print(f"  Elemento {i}: {element_connectivity[2][i]}")
    
    # Exportar a formato UNV (compatible con Kratos via MdpaConverter)
    output_dir = "model"
    os.makedirs(output_dir, exist_ok=True)
    
    unv_file = os.path.join(output_dir, "cantilever_beam.unv")
    gmsh.write(unv_file)
    print(f"\nMalla exportada a: {unv_file}")
    
    # También exportar a formato msh para inspección
    msh_file = os.path.join(output_dir, "cantilever_beam.msh")
    gmsh.write(msh_file)
    print(f"Malla exportada a: {msh_file}")
    
    # Exportar a formato VTK para visualización
    vtk_file = os.path.join(output_dir, "cantilever_beam.vtk")
    gmsh.write(vtk_file)
    print(f"Malla exportada a: {vtk_file}")
    
    # Finalizar Gmsh
    gmsh.finalize()
    
    return {
        'nodes': num_nodes,
        'elements': num_elements,
        'element_type': element_type_3d,
        'unv_file': unv_file,
        'msh_file': msh_file,
        'vtk_file': vtk_file
    }

if __name__ == "__main__":
    print("=== GENERANDO MALLA DE VIGA EN VOLADIZO ===")
    mesh_info = generate_cantilever_beam_mesh()
    print("\n=== GENERACIÓN DE MALLA COMPLETADA ===")
    print(f"Archivo UNV: {mesh_info['unv_file']}")
    print(f"Archivo MSH: {mesh_info['msh_file']}")
    print(f"Archivo VTK: {mesh_info['vtk_file']}")