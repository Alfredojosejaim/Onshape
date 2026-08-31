#!/usr/bin/env python3
"""PRUEBA DE INTEGRACIÓN KRATOS CON EL CORE

Esta prueba valida que Kratos puede funcionar como solver FEA real del Core
mediante la interfaz definida en solver_interface.py.

Flujo: CORE → SOLVER_INTERFACE → KRATOS_ADAPTER → KRATOS → FEA → RESULTADOS → CORE
"""

import sys
import os
import logging
import numpy as np

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_kratos_fea_solver_creation():
    """Test that Kratos FEA solver can be created via solver_interface."""
    logger.info("\n=== TEST 1: CREACIÓN DE SOLVER FEA KRATOS ===")
    
    try:
        from core.solver_interface import create_kratos_fea_solver, KRATOS_AVAILABLE
        
        if not KRATOS_AVAILABLE:
            logger.error("❌ Kratos no está disponible")
            return False
        
        logger.info("✅ Kratos está disponible")
        
        # Create simple test data
        nodes = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ])
        
        elements = np.array([
            [0, 1, 2, 3],
            [1, 4, 2, 3],
        ])
        
        # Create material
        from core.materials import Material
        material = Material(
            name="TestSteel",
            young_modulus=2.1e11,
            poisson_ratio=0.3,
            density=7850.0,
            yield_strength=250.0e6
        )
        
        # Create constraints
        from core.study import ConstraintDefinition, ConstraintType
        constraints = [
            ConstraintDefinition(
                id="fixed_base",
                constraint_type=ConstraintType.FIXED,
                location_face_id="base"
            )
        ]
        
        # Create loads
        from core.study import LoadDefinition, LoadType
        loads = [
            LoadDefinition(
                id="tip_load",
                magnitude=1000.0,
                direction=(0.0, 0.0, -1.0),
                load_type=LoadType.DISTRIBUTED
            )
        ]
        
        # Create Kratos FEA solver
        fea_solver = create_kratos_fea_solver(nodes, elements, material, constraints, loads)
        
        logger.info("✅ Solver FEA Kratos creado exitosamente")
        logger.info(f"   - Tipo: {type(fea_solver)}")
        
        return True, fea_solver
        
    except Exception as e:
        logger.error(f"❌ Falló creación de solver FEA: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_kratos_fea_solver_execution(fea_solver):
    """Test that Kratos FEA solver can execute analysis."""
    logger.info("\n=== TEST 2: EJECUCIÓN DE ANÁLISIS FEA ===")
    
    try:
        # Execute FEA analysis
        densities = np.ones(2)  # 2 elements, full density
        result = fea_solver(densities=densities)
        
        if result["success"]:
            logger.info("✅ Análisis FEA completado exitosamente")
            logger.info(f"   - Estado: {result['status']}")
            logger.info(f"   - Nodos: {result['num_nodes']}")
            logger.info(f"   - Elementos: {result['num_elements']}")
            logger.info(f"   - Compliance: {result['compliance']:.6e}")
            logger.info(f"   - Desplazamientos: {len(result['displacements'])} nodos")
            logger.info(f"   - Energías elementales: {len(result['element_energies'])} elementos")
            
            return True, result
        else:
            logger.error(f"❌ Análisis FEA falló: {result.get('error')}")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Falló ejecución de análisis FEA: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_integration_with_topopt_solver():
    """Test integration with TopOptSolver using Kratos as fea_solver."""
    logger.info("\n=== TEST 3: INTEGRACIÓN CON TopOptSolver ===")
    
    try:
        from core.solver_interface import TopOptSolver, create_kratos_fea_solver
        
        # Create test data
        nodes = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ])
        
        elements = np.array([
            [0, 1, 2, 3],
            [1, 4, 2, 3],
        ])
        
        # Create material
        from core.materials import Material
        material = Material(
            name="TestSteel",
            young_modulus=2.1e11,
            poisson_ratio=0.3,
            density=7850.0,
            yield_strength=250.0e6
        )
        
        # Create constraints and loads
        from core.study import ConstraintDefinition, LoadDefinition, ConstraintType, LoadType
        constraints = [
            ConstraintDefinition(
                id="fixed_base",
                constraint_type=ConstraintType.FIXED,
                location_face_id="base"
            )
        ]
        loads = [
            LoadDefinition(
                id="tip_load",
                magnitude=1000.0,
                direction=(0.0, 0.0, -1.0),
                load_type=LoadType.DISTRIBUTED
            )
        ]
        
        # Create Kratos FEA solver
        fea_solver = create_kratos_fea_solver(nodes, elements, material, constraints, loads)
        
        # Create TopOptSolver with Kratos as fea_solver
        nelx, nely = 2, 1  # 2x1x1 grid = 2 elements
        topopt_solver = TopOptSolver(
            nelx=nelx,
            nely=nely,
            nelz=1,
            volfrac=0.5,
            penalization=3.0,
            rmin=1.5,
            fea_solver=fea_solver
        )
        
        logger.info("✅ TopOptSolver creado con Kratos como fea_solver")
        
        # Execute topology optimization (single iteration for testing)
        result = topopt_solver.solve(max_iterations=1)
        
        if result["success"]:
            logger.info("✅ Optimización topológica completada exitosamente")
            logger.info(f"   - Estado: {result['status']}")
            logger.info(f"   - Iteraciones: {result.get('iterations', 0)}")
            logger.info(f"   - Fracción de volumen final: {result.get('final_volume_fraction', 0.0)}")
            
            return True, result
        else:
            logger.error(f"❌ Optimización falló: {result.get('error')}")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Falló integración con TopOptSolver: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Execute complete integration test of Kratos with Core."""
    logger.info("=" * 80)
    logger.info("PRUEBA DE INTEGRACIÓN KRATOS CON EL CORE")
    logger.info("=" * 80)
    
    # Test 1: Create Kratos FEA solver
    success1, fea_solver = test_kratos_fea_solver_creation()
    if not success1:
        logger.error("\n❌ PRUEBA DE INTEGRACIÓN FALLIDA: No se pudo crear solver FEA")
        return False
    
    # Test 2: Execute FEA analysis
    success2, fea_result = test_kratos_fea_solver_execution(fea_solver)
    if not success2:
        logger.error("\n❌ PRUEBA DE INTEGRACIÓN FALLIDA: No se pudo ejecutar análisis FEA")
        return False
    
    # Test 3: Integration with TopOptSolver
    success3, topopt_result = test_integration_with_topopt_solver()
    if not success3:
        logger.error("\n❌ PRUEBA DE INTEGRACIÓN FALLIDA: No se pudo integrar con TopOptSolver")
        return False
    
    # SUCCESS
    logger.info("\n" + "=" * 80)
    logger.info("✅ PRUEBA DE INTEGRACIÓN COMPLETADA EXITOSAMENTE")
    logger.info("=" * 80)
    logger.info("\nRESUMEN:")
    logger.info("  - Kratos FEA solver creado: ✅")
    logger.info("  - Análisis FEA ejecutado: ✅")
    logger.info("  - Integración con TopOptSolver: ✅")
    logger.info("\nFLUJO COMPLETO:")
    logger.info("  CORE → SOLVER_INTERFACE → KRATOS_ADAPTER → KRATOS → FEA → RESULTADOS → CORE")
    logger.info("   ✅       ✅                ✅              ✅      ✅      ✅        ✅")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"\n❌ ERROR CRÍTICO EN PRUEBA DE INTEGRACIÓN: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)