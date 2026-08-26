#!/usr/bin/env python3
"""
Script para verificar componentes de OptimizationApplication
PoC Kratos Topological Optimization 3D
"""

import KratosMultiphysics as Kratos
from KratosMultiphysics import OptimizationApplication
import sys

def check_optimization_components():
    """
    Verifica mediante código qué componentes de optimización están disponibles
    """
    
    print("=== VERIFICANDO OPTIMIZATIONAPPLICATION ===")
    
    try:
        print("\n1. Verificando importación de OptimizationApplication...")
        print("[OK] OptimizationApplication importado exitosamente")
    except ImportError as e:
        print(f"[ERROR] Error importando OptimizationApplication: {e}")
        return False
    
    # Verificar componentes disponibles
    print("\n2. Componentes disponibles en OptimizationApplication:")
    
    try:
        # Obtener todos los atributos del módulo
        opt_attrs = dir(OptimizationApplication)
        
        # Filtrar componentes relevantes
        relevant_components = []
        for attr in opt_attrs:
            if not attr.startswith('_'):
                relevant_components.append(attr)
        
        print(f"   Total de componentes públicos: {len(relevant_components)}")
        
        # Buscar componentes específicos relacionados con SIMP
        simp_related = [attr for attr in relevant_components if 'simp' in attr.lower() or 'density' in attr.lower()]
        print(f"   Componentes relacionados con SIMP/densidad: {simp_related}")
        
        # Buscar componentes de response
        response_related = [attr for attr in relevant_components if 'response' in attr.lower()]
        print(f"   Componentes relacionados con response: {response_related}")
        
        # Buscar componentes de control
        control_related = [attr for attr in relevant_components if 'control' in attr.lower()]
        print(f"   Componentes relacionados con control: {control_related}")
        
        # Buscar componentes de filtro
        filter_related = [attr for attr in relevant_components if 'filter' in attr.lower()]
        print(f"   Componentes relacionados con filtro: {filter_related}")
        
        # Buscar componentes de algoritmo
        algorithm_related = [attr for attr in relevant_components if 'algorithm' in attr.lower() or 'solver' in attr.lower()]
        print(f"   Componentes relacionados con algoritmo/solver: {algorithm_related}")
        
    except Exception as e:
        print(f"[ERROR] Error explorando componentes: {e}")
    
    # Verificar variables de Kratos relacionadas con optimización
    print("\n3. Variables de Kratos relacionadas con optimización:")
    
    try:
        # Variables de densidad
        if hasattr(Kratos, 'DENSITY'):
            print("   [OK] DENSITY disponible")
        else:
            print("   [WARNING] DENSITY no encontrada")
        
        # Variables de sensibilidad
        sensitivity_vars = [attr for attr in dir(Kratos) if 'SENSITIVITY' in attr or 'sensitivity' in attr]
        print(f"   Variables de sensibilidad: {sensitivity_vars}")
        
        # Variables de strain energy
        strain_energy_vars = [attr for attr in dir(Kratos) if 'STRAIN_ENERGY' in attr or 'strain_energy' in attr]
        print(f"   Variables de strain energy: {strain_energy_vars}")
        
    except Exception as e:
        print(f"[ERROR] Error verificando variables: {e}")
    
    # Intentar importar clases específicas conocidas
    print("\n4. Verificando clases específicas conocidas:")
    
    specific_classes = [
        'SimpControl',
        'LinearStrainEnergyResponseFunction',
        'StrainEnergyResponse',
        'ComplianceResponse',
        'DensityControl',
        'SensitivityFilter',
        'VolumeConstraint'
    ]
    
    for class_name in specific_classes:
        try:
            # Intentar importar desde OptimizationApplication
            cls = getattr(OptimizationApplication, class_name, None)
            if cls is not None:
                print(f"   [OK] {class_name} disponible")
            else:
                print(f"   [WARNING] {class_name} no encontrada en OptimizationApplication")
        except Exception as e:
            print(f"   [ERROR] Error verificando {class_name}: {e}")
    
    # Verificar si hay módulos de utilidades
    print("\n5. Verificando módulos de utilidades:")
    
    utility_modules = [
        'OptimizationUtils',
        'ControlUtils',
        'ResponseUtils',
        'FilterUtils'
    ]
    
    for module_name in utility_modules:
        try:
            utils = getattr(OptimizationApplication, module_name, None)
            if utils is not None:
                print(f"   [OK] {module_name} disponible")
            else:
                print(f"   [WARNING] {module_name} no encontrado")
        except Exception as e:
            print(f"   [ERROR] Error verificando {module_name}: {e}")
    
    print("\n=== VERIFICACIÓN COMPLETADA ===")
    return True

if __name__ == "__main__":
    check_optimization_components()