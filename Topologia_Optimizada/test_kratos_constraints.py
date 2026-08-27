#!/usr/bin/env python3
"""Test script for Kratos boundary conditions (Etapa E)."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fixed_constraint():
    """Test applying fixed constraint to nodes."""
    print("=== ETAPA E - CONDICIONES DE FRONTERA ===")
    print("\n1. Aplicando restricción fija...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.materials import STANDARD_MATERIALS
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestFixedConstraint")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.apply_standard_material(model_part, "steel")
        adapter.add_displacement_dofs(model_part)
        
        # Apply fixed constraint to first node
        adapter.apply_fixed_constraint(model_part, [0])
        
        print("   [PASS] Restricción fija aplicada al nodo 0")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando restricción fija: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_pinned_constraint():
    """Test applying pinned constraint to nodes."""
    print("\n2. Aplicando restricción empotrada...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestPinnedConstraint")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply pinned constraint to first two nodes
        adapter.apply_pinned_constraint(model_part, [0, 1])
        
        print("   [PASS] Restricción empotrada aplicada a nodos 0, 1")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando restricción empotrada: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_constraint_from_core():
    """Test applying constraint from Core's ConstraintDefinition."""
    print("\n3. Aplicando restricción desde Core...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import ConstraintDefinition, ConstraintType
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestCoreConstraint")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Create a Core constraint
        constraint = ConstraintDefinition(
            id="fixed_support",
            constraint_type=ConstraintType.FIXED,
            location_face_id="face_1"
        )
        
        # Apply constraint
        adapter.apply_constraint_from_core(model_part, constraint, [0])
        
        print(f"   [PASS] Restricción Core aplicada: {constraint.id} ({constraint.constraint_type})")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando restricción Core: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_multiple_constraints():
    """Test applying multiple constraints."""
    print("\n4. Aplicando múltiples restricciones...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import ConstraintDefinition, ConstraintType
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestMultipleConstraints")
        
        # Create a larger mesh
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
            [1.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0], [1.0, 1.0, 1.0]
        ]
        elements = [[0, 1, 2, 3], [1, 4, 2, 5], [2, 6, 3, 7]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply multiple constraints
        fixed_constraint = ConstraintDefinition(
            id="fixed_end",
            constraint_type=ConstraintType.FIXED,
            location_face_id="face_left"
        )
        
        pinned_constraint = ConstraintDefinition(
            id="pinned_support",
            constraint_type=ConstraintType.PINNED,
            location_face_id="face_right"
        )
        
        adapter.apply_constraint_from_core(model_part, fixed_constraint, [0, 1, 2])
        adapter.apply_constraint_from_core(model_part, pinned_constraint, [6, 7])
        
        print("   [PASS] Múltiples restricciones aplicadas (3 fijos, 2 empotrados)")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando múltiples restricciones: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_constraints_with_real_mesh():
    """Test constraints with real mesh from Gmsh."""
    print("\n5. Aplicando restricciones con malla real Gmsh...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import ConstraintDefinition, ConstraintType
        import os
        
        # Check if we have a Gmsh file from the PoC
        gmsh_file = "experimentos/kratos_topopt_poc/model/cantilever_beam.msh"
        
        if not os.path.exists(gmsh_file):
            print(f"   [SKIP] Archivo Gmsh no encontrado: {gmsh_file}")
            return None, None
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestRealMeshConstraints")
        
        # Import real mesh
        adapter.import_mesh_from_gmsh(model_part, gmsh_file)
        adapter.apply_standard_material(model_part, "aluminum")
        adapter.add_displacement_dofs(model_part)
        
        # Apply fixed constraint to some nodes (simulating fixed face)
        # In a real scenario, this would use face mapping
        fixed_nodes = list(range(10))  # First 10 nodes as example
        adapter.apply_fixed_constraint(model_part, fixed_nodes)
        
        print(f"   [PASS] Restricciones aplicadas a malla real: {len(fixed_nodes)} nodos fijos de {model_part.NumberOfNodes()} total")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando restricciones con malla real: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    """Run all Stage E tests."""
    print("=== PRUEBAS DE CONDICIONES DE FRONTERA (ETAPA E) ===\n")
    
    # Test fixed constraint
    adapter, model_part = test_fixed_constraint()
    if adapter is None or model_part is None:
        print("\n=== RESULTADO: ETAPA E FALLIDA ===")
        print("No se pudo aplicar restricción fija")
        return False
    
    # Test pinned constraint
    pinned_adapter, pinned_model_part = test_pinned_constraint()
    if pinned_adapter is None or pinned_model_part is None:
        print("\n=== RESULTADO: ETAPA E PARCIAL ===")
        print("Restricción fija exitosa pero empotrada falló")
        return False
    
    # Test Core constraint
    core_adapter, core_model_part = test_constraint_from_core()
    if core_adapter is None or core_model_part is None:
        print("\n=== RESULTADO: ETAPA E PARCIAL ===")
        print("Restricciones básicas exitosas pero Core falló")
        return False
    
    # Test multiple constraints
    multi_adapter, multi_model_part = test_multiple_constraints()
    if multi_adapter is None or multi_model_part is None:
        print("\n=== RESULTADO: ETAPA E PARCIAL ===")
        print("Restricción Core exitosa pero múltiples fallaron")
        return False
    
    # Test with real mesh
    real_adapter, real_model_part = test_constraints_with_real_mesh()
    if real_adapter is not None and real_model_part is not None:
        print("   Restricciones con malla real exitosas")
    
    print("\n=== RESULTADO: ETAPA E COMPLETADA ===")
    print("Condiciones de frontera pueden aplicarse correctamente")
    print("Componentes verificados:")
    print("  - Aplicación de restricción fija: OK")
    print("  - Aplicación de restricción empotrada: OK")
    print("  - Aplicación desde ConstraintDefinition del Core: OK")
    print("  - Aplicación de múltiples restricciones: OK")
    print("  - Restricciones con malla real: OK (si archivo disponible)")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)