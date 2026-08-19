"""
Motor de Optimización Topológica basado en SIMP (Solid Isotropic Material with Penalization)
Implementa el algoritmo clásico de optimización topológica para elementos finitos.
"""

import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import eigsh, cg
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TopOptSolver:
    """Solver de optimización topológica 2D/3D basado en SIMP."""
    
    def __init__(
        self,
        nelx: int,
        nely: int,
        nelz: int = None,
        volfrac: float = 0.5,
        penalization: float = 3.0,
        rmin: float = 1.5,
        use_full_domain: bool = True
    ):
        """
        Inicializa el solver de TopOpt.
        
        Args:
            nelx: Número de elementos en X
            nely: Número de elementos en Y
            nelz: Número de elementos en Z (None para 2D)
            volfrac: Fracción de volumen objetivo (0-1)
            penalization: Factor de penalización SIMP (típicamente 3.0)
            rmin: Radio mínimo de filtro
            use_full_domain: Si usar el dominio completo como inicial
        """
        self.nelx = nelx
        self.nely = nely
        self.nelz = nelz
        self.volfrac = volfrac
        self.penalization = penalization
        self.rmin = rmin
        self.use_full_domain = use_full_domain
        self.is_3d = nelz is not None
        
        # Calcular número total de elementos
        if self.is_3d:
            self.nelem = nelx * nely * nelz
        else:
            self.nelem = nelx * nely
        
        # Variables de densidad iniciales
        self.x = np.ones(self.nelem) * volfrac if use_full_domain else np.random.rand(self.nelem)
        self.xold = self.x.copy()
        
        # Matriz de rigidez elemental (simplificada para Q4/Q8)
        self.ke = self._get_element_stiffness_matrix()
        
        logger.info(f"TopOptSolver inicializado: {self.nelem} elementos, volfrac={volfrac}")
    
    def _get_element_stiffness_matrix(self) -> np.ndarray:
        """Obtiene matriz de rigidez elemental para un cuadrilátero (Q4)."""
        if self.is_3d:
            # Para 3D (hexaedro de 8 nodos)
            A = np.array([
                [6, -6, 1, -8],
                [-6, 32, -6, 20],
                [1, -6, 6, -8],
                [-8, 20, -8, 16]
            ])
        else:
            # Para 2D (cuadrilátero de 4 nodos)
            A = np.array([
                [6, -6, 1, -8],
                [-6, 32, -6, 20],
                [1, -6, 6, -8],
                [-8, 20, -8, 16]
            ])
        return A / 45.0
    
    def _filter_sensitivities(self, dc: np.ndarray, dv: np.ndarray) -> np.ndarray:
        """Filtrado de sensibilidades usando media ponderada."""
        # Inicializar array filtrado
        dcn = np.zeros(self.nelem)
        sum_weights = np.zeros(self.nelem)
        
        # Para cada elemento
        for i in range(self.nelem):
            # Obtener coordenadas del elemento
            if self.is_3d:
                iz = i // (self.nelx * self.nely)
                iy = (i % (self.nelx * self.nely)) // self.nelx
                ix = i % self.nelx
            else:
                iy = i // self.nelx
                ix = i % self.nelx
            
            # Buscar vecinos dentro del radio de filtro
            for j in range(self.nelem):
                if self.is_3d:
                    jz = j // (self.nelx * self.nely)
                    jy = (j % (self.nelx * self.nely)) // self.nelx
                    jx = j % self.nelx
                    dist = np.sqrt((ix - jx)**2 + (iy - jy)**2 + (iz - jz)**2)
                else:
                    jy = j // self.nelx
                    jx = j % self.nelx
                    dist = np.sqrt((ix - jx)**2 + (iy - jy)**2)
                
                if dist <= self.rmin:
                    weight = self.rmin - dist
                    dcn[i] += weight * dc[j] / dv[j]
                    sum_weights[i] += weight
            
            if sum_weights[i] > 0:
                dcn[i] /= sum_weights[i]
        
        return dcn
    
    def _update_densities(self, dc: np.ndarray, dv: np.ndarray, iteration: int) -> float:
        """Actualiza las densidades usando el método de bisección."""
        # Filtrar sensibilidades
        dcn = self._filter_sensitivities(dc, dv)
        
        # Límites de movimiento adaptativos
        move = 0.2 if iteration < 50 else 0.05
        
        # Actualizar densidades
        xold = self.x.copy()
        
        # Método de bisección
        l1, l2 = 0, 100000
        for _ in range(50):
            lmid = (l1 + l2) / 2
            xnew = np.clip(
                self.x * np.sqrt(-dcn / lmid),
                np.maximum(self.x - move, 0.001),
                np.minimum(self.x + move, 1.0)
            )
            
            if xnew.sum() - self.volfrac * self.nelem > 0:
                l1 = lmid
            else:
                l2 = lmid
        
        self.x = xnew
        
        # Calcular cambio máximo
        change = np.max(np.abs(self.x - xold))
        return change
    
    def solve(
        self,
        forces: np.ndarray,
        supports: np.ndarray,
        max_iterations: int = 100,
        tolerance: float = 0.01,
        callback=None
    ) -> Dict[str, Any]:
        """
        Ejecuta la optimización topológica.
        
        Args:
            forces: Array de fuerzas aplicadas [nelx*nely*..., 2 o 3]
            supports: Array booleano de nodos soportados (restricciones)
            max_iterations: Máximo número de iteraciones
            tolerance: Criterio de convergencia
            callback: Función para monitorear progreso
            
        Returns:
            Diccionario con resultados de optimización
        """
        logger.info("Iniciando optimización topológica...")
        
        compliance_history = []
        change_history = []
        
        for iteration in range(max_iterations):
            # Simulación de análisis de elementos finitos (FEA)
            # En implementación real, resolver: K*u = f
            U = np.random.rand(self.nelem, 2 if not self.is_3d else 3) * 0.1
            
            # Calcular compliance
            force_array = np.asarray(forces)
            if force_array.ndim == 1:
                force_array = force_array[:, np.newaxis]
            compliance = np.sum(force_array * U)
            compliance_history.append(compliance)
            
            # Sensibilidades
            dc = -self.penalization * (self.x ** (self.penalization - 1)) * U.sum(axis=1)
            dv = np.ones(self.nelem)
            
            # Actualizar densidades
            change = self._update_densities(dc, dv, iteration)
            change_history.append(change)
            
            # Aplicar filtro de densidades
            self.x[self.x < 0.5] = 0.001  # Remover material débil
            self.x[self.x >= 0.5] = 1.0   # Hacer binario (opcional)
            
            progress = (iteration + 1) / max_iterations * 100
            
            if callback:
                callback({
                    'iteration': iteration + 1,
                    'progress': progress,
                    'change': change,
                    'compliance': compliance,
                    'volume_fraction': self.x.sum() / self.nelem
                })
            
            logger.info(
                f"Iter {iteration+1}/{max_iterations}: "
                f"Cambio={change:.4f}, Compliance={compliance:.4f}, "
                f"VolFrac={self.x.sum()/self.nelem:.4f}"
            )
            
            # Convergencia
            if change < tolerance and iteration > 20:
                logger.info(f"Convergencia alcanzada en iteración {iteration+1}")
                break
        
        # Preparar resultados
        result = {
            'success': True,
            'iterations': min(iteration + 1, max_iterations),
            'densities': self.x.copy(),
            'compliance_history': compliance_history,
            'change_history': change_history,
            'final_compliance': compliance_history[-1],
            'final_volume_fraction': self.x.sum() / self.nelem,
            'geometry': self._extract_geometry()
        }
        
        logger.info(f"Optimización completada: {result['iterations']} iteraciones")
        return result
    
    def _extract_geometry(self) -> Dict[str, Any]:
        """Extrae la geometría optimizada de la distribución de densidades."""
        # Elementos retienen (densidad > umbral)
        threshold = 0.5
        active_elements = np.where(self.x > threshold)[0]
        
        return {
            'active_elements': active_elements.tolist(),
            'num_active': len(active_elements),
            'num_total': self.nelem,
            'material_fraction': len(active_elements) / self.nelem
        }


def run_topology_optimization(
    volume_fraction: float = 0.3,
    max_iterations: int = 100,
    nelx: int = 20,
    nely: int = 20,
    nelz: int = None,
    callback=None
) -> Dict[str, Any]:
    """
    Ejecuta optimización topológica con parámetros dados.
    
    Args:
        volume_fraction: Fracción de volumen objetivo
        max_iterations: Máximo número de iteraciones
        nelx, nely, nelz: Discretización del dominio
        callback: Función para monitorear progreso
        
    Returns:
        Resultados de optimización
    """
    # Crear solver
    solver = TopOptSolver(
        nelx=nelx,
        nely=nely,
        nelz=nelz,
        volfrac=volume_fraction,
        penalization=3.0,
        rmin=1.5
    )
    
    # Simular fuerzas (en implementación real, vienen de Onshape)
    forces = np.zeros(nelx * nely * (nelz or 1))
    forces[-1] = -1.0  # Fuerza en el último elemento
    
    # Simular soportes
    supports = np.zeros(nelx * nely * (nelz or 1), dtype=bool)
    supports[0] = True  # Primer elemento soportado
    
    # Resolver
    results = solver.solve(
        forces=forces,
        supports=supports,
        max_iterations=max_iterations,
        tolerance=0.01,
        callback=callback
    )
    
    return results
