#!/usr/bin/env python3
"""
Script muy simplificado para FEA usando Python puro sin Kratos
Para comparar resultados y validar el enfoque matemático
"""

import numpy as np
import sys

def analytical_cantilever():
    """
    Calcula la solución analítica para una viga en voladizo
    """
    # Parámetros del problema
    length = 100.0  # mm
    width = 10.0    # mm
    height = 10.0   # mm
    force = -100.0  # N (carga vertical negativa)
    Young_modulus = 68.9e9  # Pa (aluminio)
    
    # Solución analítica para viga en voladizo con carga puntual en el extremo
    # δ_max = (F * L^3) / (3 * E * I)
    # I = (b * h^3) / 12 para sección rectangular
    
    I = (width * height**3) / 12  # Momento de inercia (mm^4)
    I_m4 = I * 1e-12  # Convertir a m^4
    
    delta_analytical = (abs(force) * (length/1000)**3) / (3 * Young_modulus * I_m4)
    
    print("=== SOLUCIÓN ANALÍTICA VIGA EN VOLADIZO ===")
    print(f"Longitud: {length} mm")
    print(f"Sección: {width} x {height} mm")
    print(f"Carga: {force} N")
    print(f"Módulo de Young: {Young_modulus:.2e} Pa")
    print(f"Momento de inercia: {I:.2e} mm^4 = {I_m4:.2e} m^4")
    print(f"Desplazamiento máximo analítico: {delta_analytical:.6e} m")
    print(f"Desplazamiento máximo analítico: {delta_analytical*1000:.6f} mm")
    
    return delta_analytical

if __name__ == "__main__":
    delta = analytical_cantilever()
    print(f"\nDesplazamiento esperado: {delta:.6e} m ({delta*1000:.6f} mm)")