#!/usr/bin/env python3
"""Test script for Kratos loads (Etapa F)."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_point_load():
    """Test applying point load to a node."""
    print("=== ETAPA F - CARGAS ===")
    print("\n1. Aplicando carga puntual...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestPointLoad")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply point load to last node
        force_vector = [0.0, 0.0, -1000.0]  # 1000 N in -Z direction
        adapter.apply_point_load(model_part, 3, force_vector)
        
        print(f"   [PASS] Carga puntual aplicada: {force_vector} N al nodo 3")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando carga puntual: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_distributed_load():
    """Test applying distributed load to multiple nodes."""
    print("\n2. Aplicando carga distribuida...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestDistributedLoad")
        
        # Create a larger mesh
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
            [1.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0], [1.0, 1.0, 1.0]
        ]
        elements = [[0, 1, 2, 3], [1, 4, 2, 5], [2, 6, 3, 7]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply distributed load to top face nodes
        force_vector = [0.0, 0.0, -5000.0]  # 5000 N total
        node_indices = [4, 5, 6, 7]  # Top face nodes
        adapter.apply_distributed_load(model_part, node_indices, force_vector, distribute=True)
        
        print(f"   [PASS] Carga distribuida aplicada: {force_vector} N a {len(node_indices)} nodos")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando carga distribuida: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_load_from_core():
    """Test applying load from Core's LoadDefinition."""
    print("\n3. Aplicando carga desde Core...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import LoadDefinition, LoadType
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestCoreLoad")
        
        # Create a simple mesh
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Create a Core load
        load = LoadDefinition(
            id="tip_load",
            magnitude=1000.0,
            direction=(0.0, 0.0, -1.0),  # Downward
            load_type=LoadType.POINT
        )
        
        # Apply load
        adapter.apply_load_from_core(model_part, load, [3])
        
        print(f"   [PASS] Carga Core aplicada: {load.id} ({load.magnitude} N)")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando carga Core: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_pressure_load():
    """Test applying pressure load (simplified)."""
    print("\n4. Aplicando carga de presión...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestPressureLoad")
        
        # Create a simple mesh
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
            [1.0, 1.0, 0.0]
        ]
        elements = [[0, 1, 2, 3]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply pressure load
        pressure = 1000.0  # Pa
        normal_vector = [0.0, 0.0, -1.0]  # Downward normal
        node_indices = [1, 2, 4]  # Top face nodes
        
        adapter.apply_pressure_load(model_part, node_indices, pressure, normal_vector)
        
        print(f"   [PASS] Carga de presión aplicada: {pressure} Pa a {len(node_indices)} nodos")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando carga de presión: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_loads_with_constraints():
    """Test applying loads together with constraints."""
    print("\n5. Aplicando cargas con restricciones...")
    
    try:
        from core.kratos_adapter import initialize_kratos_adapter
        from core.study import LoadDefinition, LoadType, ConstraintDefinition, ConstraintType
        
        adapter = initialize_kratos_adapter()
        model_part = adapter.create_model_part("TestLoadsWithConstraints")
        
        # Create a cantilever-like mesh
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
            [2.0, 0.0, 0.0], [2.0, 1.0, 0.0], [2.0, 0.0, 1.0], [2.0, 1.0, 1.0]
        ]
        elements = [[0, 1, 2, 3], [1, 4, 2, 5], [2, 6, 3, 7]]
        
        adapter.import_mesh_from_core_format(model_part, nodes, elements, "tet4")
        adapter.configure_material_manually(model_part, 68.9e9, 0.33)
        adapter.add_displacement_dofs(model_part)
        
        # Apply fixed constraint to one end
        constraint = ConstraintDefinition(
            id="fixed_end",
            constraint_type=ConstraintType.FIXED,
            location_face_id="face_left"
        )
        adapter.apply_constraint_from_core(model_part, constraint, [0, 1, 2])
        
        # Apply point load to the other end
        load = LoadDefinition(
            id="tip_load",
            magnitude=2000.0,
            direction=(0.0, 0.0, -1.0),
            load_type=LoadType.POINT
        )
        adapter.apply_load_from_core(model_part, load, [7])
        
        print("   [PASS] Cargas y restricciones aplicadas conjuntamente")
        return adapter, model_part
        
    except Exception as e:
        print(f"   [ERROR] Error aplicando cargas con restricciones: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def main():
    """Run all Stage F tests."""
    print("=== PRUEBAS DE CARGAS (ETAPA F) ===\n")
    
    # Test point load
    adapter, model_part = test_point_load()
    if adapter is None or model_part is None:
        print("\n=== RESULTADO: ETAPA F FALLIDA ===")
        print("No se pudo aplicar carga puntual")
        return False
    
    # Test distributed load
    dist_adapter, dist_model_part = test_distributed_load()
    if dist_adapter is None or dist_model_part is None:
        print("\n=== RESULTADO: ETAPA F PARCIAL ===")
        print("Carga puntual exitosa pero distribuida falló")
        return False
    
    # Test Core load
    core_adapter, core_model_part = test_load_from_core()
    if core_adapter is None or core_model_part is None:
        print("\n=== RESULTADO: ETAPA F PARCIAL ===")
        print("Cargas básicas exitosas pero Core falló")
        return False
    
    # Test pressure load
    pressure_adapter, pressure_model_part = test_pressure_load()
    if pressure_adapter is None or pressure_model_part is None:
        print("\n=== RESULTADO: ETAPA F PARCIAL ===")
        print("Carga Core exitosa pero presión falló")
        return False
    
    # Test loads with constraints
    combined_adapter, combined_model_part = test_loads_with_constraints()
    if combined_adapter is None or combined_model_part is None:
        print("\n=== RESULTADO: ETAPA F PARCIAL ===")
        print("Cargas individuales exitosas pero combinadas fallaron")
        return False
    
    print("\n=== RESULTADO: ETAPA F COMPLETADA ===")
    print("Cargas pueden aplicarse correctamente en múltiples modalidades")
    print("Componentes verificados:")
    print("  - Aplicación de carga puntual: OK")
    print("  - Aplicación de carga distribuida: OK")
    print("  - Aplicación desde LoadDefinition del Core: OK")
    print("  - Aplicación de carga de presión: OK")
    print("  - Aplicación combinada con restricciones: OK")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)