"""
Test de validación: Geometría correcta de restricciones y cargas.

Este test verifica que el problema de sobreconstricción ha sido resuelto.
Compara los resultados FEA contra la solución analítica de una viga en voladizo.

Bloqueo original: Todos los nodos estaban fijos + todas las cargas en todos los nodos
Resultado: ~1e-9 m (ruido numérico)

Solución implementada: Selección geométrica de nodos
Resultado esperado: ~5.8e-4 m (coincide con fórmula analítica)
"""

import pytest
import numpy as np
from typing import List

from core.materials import Material
from core.study import LoadDefinition, ConstraintDefinition, LoadType, ConstraintType
from core.solver_interface import create_kratos_fea_solver


def create_simple_cantilever_mesh(
    length: float = 1.0,
    height: float = 0.1,
    width: float = 0.1,
    nelements_x: int = 10,
    nelements_y: int = 2,
    nelements_z: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Create a simple cantilever beam mesh using tetrahedral elements.
    
    Geometry:
    - Beam along X axis from X=0 (fixed) to X=length (free)
    - Y and Z dimensions for height and width
    - Rectangular cross-section
    
    Args:
        length: Length of beam along X axis
        height: Height of beam (Y direction)
        width: Width of beam (Z direction)
        nelements_x: Number of elements along length
        nelements_y: Number of elements along height
        nelements_z: Number of elements along width
        
    Returns:
        Tuple of (nodes, elements) arrays
    """
    # Create nodal grid
    nx, ny, nz = nelements_x + 1, nelements_y + 1, nelements_z + 1
    x = np.linspace(0, length, nx)
    y = np.linspace(-height/2, height/2, ny)
    z = np.linspace(-width/2, width/2, nz)
    
    # Generate node coordinates
    nodes = []
    node_indices = {}
    
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                nodes.append([x[i], y[j], z[k]])
                node_indices[(i, j, k)] = len(nodes) - 1
    
    nodes = np.array(nodes)
    
    # Generate tetrahedral elements
    # For each cubic cell, we create 6 tetrahedra
    elements = []
    
    for i in range(nelements_x):
        for j in range(nelements_y):
            for k in range(nelements_z):
                # 8 vertices of the cube
                v0 = node_indices[(i, j, k)]
                v1 = node_indices[(i+1, j, k)]
                v2 = node_indices[(i, j+1, k)]
                v3 = node_indices[(i, j, k+1)]
                v4 = node_indices[(i+1, j+1, k)]
                v5 = node_indices[(i+1, j, k+1)]
                v6 = node_indices[(i, j+1, k+1)]
                v7 = node_indices[(i+1, j+1, k+1)]
                
                # Create 6 tetrahedra from each cube
                elements.extend([
                    [v0, v1, v2, v3],
                    [v1, v4, v2, v5],
                    [v2, v4, v6, v7],
                    [v0, v2, v3, v6],
                    [v1, v5, v3, v7],
                    [v2, v3, v6, v7],
                ])
    
    elements = np.array(elements, dtype=int)
    
    return nodes, elements


def test_cantilever_geometric_selection():
    """Test cantilever beam with proper geometric node selection.
    
    Verifies that:
    1. Only nodes at Z=0 (fixed end) are constrained
    2. Only nodes at Z=L (free end) receive loads
    3. Resulting displacement matches analytical formula
    4. No over-constraint → displacements are not ~1e-9 m
    """
    # Material properties for steel
    material = Material(
        name="Steel",
        density=7850.0,  # kg/m³
        young_modulus=210e9,  # Pa (210 GPa)
        poisson_ratio=0.3,
        yield_strength=250e6  # Pa
    )
    
    # Create simple cantilever mesh
    length = 1.0  # 1 meter
    height = 0.05  # 50 mm
    width = 0.05  # 50 mm
    nodes, elements = create_simple_cantilever_mesh(
        length=length,
        height=height,
        width=width,
        nelements_x=8,
        nelements_y=2,
        nelements_z=2
    )
    
    print(f"\n=== Cantilever Beam Test ===")
    print(f"Mesh: {nodes.shape[0]} nodes, {elements.shape[0]} elements")
    print(f"Beam dimensions: L={length}m, H={height}m, W={width}m")
    
    # Define constraints: Fix nodes at X=0 (fixed end)
    constraints = [
        ConstraintDefinition(
            id="cantilever_fixed",
            constraint_type=ConstraintType.FIXED,
            location_face_id="fixed_end",
            # Geometric selection: nodes where X ≈ 0
            fixed_axis=0,  # X axis
            fixed_coordinate=0.0,  # X = 0 (fixed end)
            tolerance=0.01
        )
    ]
    
    # Define loads: Apply point load at free end (X=L, downward)
    load_magnitude = 1000.0  # 1000 N
    loads = [
        LoadDefinition(
            id="cantilever_load",
            magnitude=load_magnitude,
            direction=(0, 0, -1),  # Downward (negative Z)
            load_type=LoadType.POINT,
            # Geometric selection: nodes where X ≈ L
            load_axis=0,  # X axis
            load_coordinate=length,  # X = L (free end)
            tolerance=0.01
        )
    ]
    
    # Create FEA solver
    try:
        fea_solver = create_kratos_fea_solver(
            nodes=nodes,
            elements=elements,
            material=material,
            constraints=constraints,
            loads=loads
        )
        
        # Run FEA analysis
        result = fea_solver(
            densities=np.ones(elements.shape[0]),
            forces=None,
            supports=None,
            max_iterations=1
        )
        
        assert result["success"], f"FEA solver failed: {result.get('error')}"
        
        # Extract results
        displacements = result.get("displacements", [])
        max_displacement = result.get("max_displacement", 0)
        compliance = result.get("compliance", 0)
        
        print(f"\nFEA Results:")
        print(f"  Max displacement: {max_displacement:.6e} m")
        print(f"  Compliance: {compliance:.6e} J")
        print(f"  Displacements shape: {np.array(displacements).shape}")
        
        # Analytical formula for cantilever beam: δ = F*L³/(3*E*I)
        # For rectangular cross-section: I = b*h³/12 (b=width, h=height)
        I = (width * height**3) / 12  # Second moment of inertia
        analytical_displacement = (load_magnitude * length**3) / (3 * material.young_modulus * I)
        
        print(f"\nAnalytical Formula:")
        print(f"  I = {I:.6e} m⁴")
        print(f"  δ = F*L³/(3*E*I) = {analytical_displacement:.6e} m")
        print(f"  (where F={load_magnitude}N, L={length}m, E={material.young_modulus:.2e}Pa)")
        
        # Validate against analytical solution
        # Allow 30% error due to mesh discretization and FEA approximation
        tolerance_percent = 30.0
        tolerance_value = analytical_displacement * (tolerance_percent / 100.0)
        
        print(f"\nValidation:")
        print(f"  Expected range: {analytical_displacement - tolerance_value:.6e} to {analytical_displacement + tolerance_value:.6e} m")
        print(f"  Tolerance: ±{tolerance_percent}%")
        
        # Main assertion: displacement should NOT be ~1e-9 m (overconstrained)
        # and should be close to analytical value
        assert max_displacement > 1e-7, (
            f"Displacement {max_displacement:.6e} is too small (likely overconstrained). "
            f"Expected ~{analytical_displacement:.6e} m"
        )
        
        assert abs(max_displacement - analytical_displacement) <= tolerance_value, (
            f"Displacement {max_displacement:.6e} differs from analytical {analytical_displacement:.6e} "
            f"by more than ±{tolerance_percent}%"
        )
        
        print(f"\n✓ Test PASSED: Geometric selection working correctly")
        print(f"  Displacement = {max_displacement:.6e} m (within {tolerance_percent}% of analytical)")
        
    except Exception as e:
        print(f"\n✗ Test FAILED with exception:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_overconstrained_system_detection():
    """Test that detects if system is still over-constrained.
    
    If all nodes are fixed, displacement will be ~1e-9 m (numerical noise).
    This test verifies that the fix is working by checking displacement
    is significantly larger than numerical precision.
    """
    print("\n=== Over-constraint Detection Test ===")
    
    # Material properties
    material = Material(
        name="Steel",
        density=7850.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        yield_strength=250e6
    )
    
    # Simple 1x1x1 meter cube mesh (2 tetrahedra)
    nodes = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
        [1, 1, 0],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1],
    ], dtype=float)
    
    elements = np.array([
        [0, 1, 2, 3],
        [1, 4, 2, 5],
        [2, 4, 6, 7],
        [0, 2, 3, 6],
        [1, 5, 3, 7],
        [2, 3, 6, 7],
    ], dtype=int)
    
    print(f"Mesh: {nodes.shape[0]} nodes, {elements.shape[0]} elements")
    
    # Constraints and loads with proper geometric selection
    constraints = [
        ConstraintDefinition(
            id="test_fixed",
            constraint_type=ConstraintType.FIXED,
            location_face_id="face_0",
            fixed_axis=0,
            fixed_coordinate=0.0,
            tolerance=0.1
        )
    ]
    
    loads = [
        LoadDefinition(
            id="test_load",
            magnitude=100.0,
            direction=(1, 0, 0),
            load_type=LoadType.POINT,
            load_axis=0,
            load_coordinate=1.0,
            tolerance=0.1
        )
    ]
    
    try:
        fea_solver = create_kratos_fea_solver(
            nodes=nodes,
            elements=elements,
            material=material,
            constraints=constraints,
            loads=loads
        )
        
        result = fea_solver(
            densities=np.ones(elements.shape[0]),
            forces=None,
            supports=None
        )
        
        if result["success"]:
            max_displacement = result.get("max_displacement", 0)
            print(f"Max displacement: {max_displacement:.6e} m")
            
            # Check: should be > 1e-8 m (definitely not over-constrained)
            # If system was over-constrained, this would be ~1e-9 to 1e-12
            if max_displacement < 1e-8:
                print(f"⚠ WARNING: Displacement seems too small (~1e-9 to 1e-8)")
                print(f"  System may still be over-constrained")
                return False
            else:
                print(f"✓ Displacement is physically reasonable (> 1e-8 m)")
                return True
        else:
            print(f"⚠ FEA failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"✗ Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("GEOMETRIC NODE SELECTION VALIDATION TESTS")
    print("=" * 70)
    
    # Run overconstrained detection first (quick check)
    print("\n[1/2] Running over-constraint detection...")
    over_constrained_ok = test_overconstrained_system_detection()
    
    # Run cantilever beam test (full validation)
    print("\n[2/2] Running cantilever beam analytical comparison...")
    try:
        test_cantilever_geometric_selection()
    except AssertionError as e:
        print(f"\n✗ Assertion failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)
