#!/usr/bin/env python3
"""PRUEBA DE FLUJO FEA REAL CON KRATOS

Esta prueba ejecuta el flujo completo utilizando una entrada STEP real y
la integración con el Core mediante solver_interface.py.

Flujo: STEP REAL → STEP ADAPTER → CADModel → MALLA → SOLVER_INTERFACE → KRATOS → FEA → RESULTADOS → CORE
"""

import sys
import os
import tempfile
import logging
import numpy as np

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_real_step_file():
    """Use the real STEP file provided by the user."""
    logger.info("Using real STEP file: cono.step")
    
    step_file = "cono.step"
    
    if not os.path.exists(step_file):
        logger.error(f"Real STEP file not found: {step_file}")
        return None
    
    logger.info(f"Real STEP file found: {step_file}")
    return step_file

def step_1_import_step(step_file):
    """Step 1: Import STEP file using StepAdapter."""
    logger.info("\n=== STEP 1: IMPORTACIÓN STEP ===")
    
    try:
        from adapters.cad.step_adapter import StepAdapter
        
        adapter = StepAdapter()
        cad_model = adapter.load_from_file(step_file, model_name="RealStepModel")
        
        logger.info(f"✅ STEP importado exitosamente")
        logger.info(f"   - Modelo ID: {cad_model.id}")
        logger.info(f"   - Nombre: {cad_model.name}")
        logger.info(f"   - Volumen: {cad_model.total_volume:.6f} mm³")
        logger.info(f"   - Área: {cad_model.total_area:.6f} mm²")
        logger.info(f"   - Caras: {len(cad_model.faces)}")
        
        return cad_model
        
    except Exception as e:
        logger.error(f"❌ Falló importación STEP: {e}")
        import traceback
        traceback.print_exc()
        return None

def step_2_mesh_generation(step_file):
    """Step 2: Generate mesh using Gmsh from real STEP geometry."""
    logger.info("\n=== STEP 2: MALLADO ===")
    
    try:
        import gmsh
        
        # Initialize Gmsh
        gmsh.initialize()
        # Reduce verbosity
        try:
            gmsh.option.setNumber("General.Terminal", 0)
        except:
            pass
        
        # Add model first before importing shapes
        gmsh.model.add("real_step_model")
        gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
        
        # Import the real STEP file into Gmsh using OpenCASCADE importShapes
        logger.info(f"Importando geometría STEP real: {step_file}")
        imported_entities = gmsh.model.occ.importShapes(step_file, format="step")
        logger.info(f"Entidades importadas por OCC: {imported_entities}")
        
        # Synchronize OpenCASCADE kernel after STEP import
        logger.info("Sincronizando kernel OpenCASCADE...")
        gmsh.model.occ.synchronize()
        
        # Verify that volumes were detected after synchronization
        volumes = gmsh.model.getEntities(dim=3)
        logger.info(f"Volúmenes detectados tras synchronize: {len(volumes)}")
        if len(volumes) == 0:
            raise RuntimeError("El STEP no contiene sólidos 3D reconocibles, o el kernel usado no es OCC")
        
        # Set mesh size
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 5.0)
        
        # Generate 3D mesh from the real STEP geometry
        logger.info("Generando malla desde geometría STEP real...")
        gmsh.model.mesh.generate(3)
        
        # Get mesh statistics
        node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
        element_types = gmsh.model.mesh.getElementTypes()
        
        logger.info(f"✅ Malla generada exitosamente desde geometría STEP real")
        logger.info(f"   - Nodos: {len(node_tags)}")
        logger.info(f"   - Tipos de elementos: {element_types}")
        
        # Convert to numpy arrays for Core integration
        nodes_array = np.array([[node_coords[3*i], node_coords[3*i+1], node_coords[3*i+2]] 
                               for i in range(len(node_tags))])
        
        # Get elements
        element_tags, element_node_tags, element_connectivity = gmsh.model.mesh.getElements()
        
        # Find Tet4 elements
        tet_elements = None
        for i, et in enumerate(element_types):
            if et == 4:  # Tet4 in Gmsh
                tet_elements = element_connectivity[i]
                break
        
        if tet_elements is not None:
            num_tet_elements = len(tet_elements)//4
            logger.info(f"   - Elementos Tet4: {num_tet_elements}")
            
            # Convert to numpy array (reshape to M x 4)
            elements_array = np.array(tet_elements).reshape(-1, 4)
            # Convert to 0-based indexing
            elements_array = elements_array - 1
        else:
            logger.error("No se encontraron elementos Tet4")
            gmsh.finalize()
            return None, None
        
        gmsh.finalize()
        
        logger.info(f"   - Nodos array shape: {nodes_array.shape}")
        logger.info(f"   - Elementos array shape: {elements_array.shape}")
        
        return nodes_array, elements_array
        
    except Exception as e:
        logger.error(f"❌ Falló generación de malla desde STEP real: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def step_3_fea_analysis_with_core(nodes, elements):
    """Step 3: Execute FEA analysis using Kratos integrated with Core."""
    logger.info("\n=== STEP 3: ANÁLISIS FEA CON CORE ===")
    
    try:
        from core.solver_interface import create_kratos_fea_solver
        from core.materials import Material, STANDARD_MATERIALS
        from core.study import ConstraintDefinition, LoadDefinition, ConstraintType, LoadType
        
        # Create material (using standard aluminum)
        material = STANDARD_MATERIALS["aluminum"]
        logger.info(f"✅ Material seleccionado: {material.name}")
        
        # Create constraints (fixed at some nodes)
        constraints = [
            ConstraintDefinition(
                id="fixed_base",
                constraint_type=ConstraintType.FIXED,
                location_face_id="base"
            )
        ]
        
        # Create loads (distributed at some nodes)
        loads = [
            LoadDefinition(
                id="tip_load",
                magnitude=1000.0,
                direction=(0.0, 0.0, -1.0),
                load_type=LoadType.DISTRIBUTED
            )
        ]
        
        # Create Kratos FEA solver via Core interface
        fea_solver = create_kratos_fea_solver(nodes, elements, material, constraints, loads)
        logger.info("✅ Solver FEA Kratos creado vía Core interface")
        
        # Execute FEA analysis
        logger.info("🔄 Ejecutando análisis FEA...")
        densities = np.ones(len(elements))  # Full density for all elements
        result = fea_solver(densities=densities)
        
        if result["success"]:
            logger.info("✅ Análisis FEA completado exitosamente")
            logger.info(f"   - Estado: {result['status']}")
            logger.info(f"   - Nodos: {result['num_nodes']}")
            logger.info(f"   - Elementos: {result['num_elements']}")
            logger.info(f"   - Compliance: {result['compliance']:.6e}")
            logger.info(f"   - Desplazamientos: {len(result['displacements'])} nodos")
            logger.info(f"   - Energías elementales: {len(result['element_energies'])} elementos")
            
            return result
        else:
            logger.error(f"❌ Análisis FEA falló: {result.get('error')}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Falló análisis FEA con Core: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Execute complete real flow test of FEA with Kratos integrated in Core."""
    logger.info("=" * 80)
    logger.info("PRUEBA DE FLUJO FEA REAL CON KRATOS INTEGRADO EN CORE")
    logger.info("=" * 80)
    
    # Get real STEP file
    step_file = get_real_step_file()
    if not step_file:
        logger.error("\n❌ PRUEBA FALLIDA: No se pudo encontrar archivo STEP real")
        return False
    
    # Step 1: Import STEP
    cad_model = step_1_import_step(step_file)
    if not cad_model:
        logger.error("\n❌ PRUEBA FALLIDA: Importación STEP falló")
        return False
    
    # Step 2: Generate mesh from real STEP geometry
    nodes, elements = step_2_mesh_generation(step_file)
    if nodes is None or elements is None:
        logger.error("\n❌ PRUEBA FALLIDA: Generación de malla desde STEP real falló")
        return False
    
    # Step 3: Execute FEA analysis with Core integration
    fea_result = step_3_fea_analysis_with_core(nodes, elements)
    if not fea_result or not fea_result["success"]:
        logger.error("\n❌ PRUEBA FALLIDA: Análisis FEA con Core falló")
        return False
    
    # SUCCESS
    logger.info("\n" + "=" * 80)
    logger.info("✅ PRUEBA DE FLUJO REAL COMPLETADA EXITOSAMENTE")
    logger.info("=" * 80)
    logger.info("\nRESUMEN:")
    logger.info(f"  - Archivo STEP: {step_file}")
    logger.info(f"  - Modelo CAD: {cad_model.name} (ID: {cad_model.id})")
    logger.info(f"  - Malla: {fea_result['num_nodes']} nodos, {fea_result['num_elements']} elementos")
    logger.info(f"  - Desplazamientos: {len(fea_result['displacements'])} nodos")
    logger.info(f"  - Compliance: {fea_result['compliance']:.6e}")
    logger.info("\nFLUJO COMPLETO:")
    logger.info("  STEP REAL → STEP ADAPTER → CADModel → MALLA → SOLVER_INTERFACE → KRATOS → FEA → RESULTADOS → CORE")
    logger.info("     ✅         ✅           ✅        ✅       ✅              ✅      ✅      ✅        ✅")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"\n❌ ERROR CRÍTICO EN PRUEBA DE FLUJO REAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)