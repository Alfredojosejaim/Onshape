"""Instrumento de medición: compliance 0.5·uᵀ·K·u para el benchmark.

NO es un solver ni sustituye a Kratos: es un post-procesador NumPy que, dada una
malla Tet4 y el vector de desplazamientos resuelto por Kratos, ensambla la rigidez
global K (elemento de deformación constante de 4 nodos, el mismo que usa
``Element3D4N``) y calcula la energía 0.5·uᵀ·K·u.

Motivo: en el build de Kratos instalado no hay forma de obtener por Python ni el
sistema K ensamblado, ni las reacciones, ni ``STRAIN_ENERGY`` (verificado en
RESUMEN_IMPLEMENTACION, Fase 0.5). Para el caso de *desplazamiento impuesto* no hay
vector de fuerza explícito, así que la única forma rigurosa de reportar compliance
es 0.5·uᵀ·K·u (energía interna = trabajo externo 0.5·F·u en ese modo de carga).

En lugar de materializar la K global, se explota que uᵀ·K·u = Σ_e u_eᵀ·K_e·u_e
(donde K_e es la rigidez elemental y u_e el desplazamiento de los 4 nodos del
elemento), por lo que basta sumar las formas cuadráticas elementales. Operación
100% vectorizada → escala a decenas de miles de elementos.

Este módulo se usa EXCLUSIVAMENTE como métrica del benchmark sobre la solución
producida por Kratos (no participa del solve). Material isótropo lineal.
"""

import numpy as np


def tet4_strain_energy(nodes, elements, displacements, young, poisson):
    """Energía de deformación total 0.5·uᵀ·K·u para una malla Tet4.

    Args:
        nodes: (N,3) coordenadas.
        elements: (M,4) conectividad 0-based.
        displacements: (N,3) desplazamiento nodal resuelto (NaN se trata como 0).
        young: módulo de Young — DEBE coincidir con el que recibió Kratos
            (sin conversión de unidades) para que la energía sea consistente.
        poisson: coeficiente de Poisson.

    Returns:
        float: 0.5·uᵀ·K·u = Σ_e 0.5·u_eᵀ·K_e·u_e (trabajo externo en el caso de
        desplazamiento impuesto).
    """
    nodes = np.asarray(nodes, dtype=float)
    elements = np.asarray(elements, dtype=int)
    disp = np.asarray(displacements, dtype=float)

    n_nodes = nodes.shape[0]
    d = disp[:n_nodes] if disp.ndim == 2 else np.zeros((n_nodes, 3), dtype=float)
    u = np.zeros((3, n_nodes), dtype=float)
    u[:] = np.nan_to_num(d.T)

    lam = young * poisson / ((1 + poisson) * (1 - 2 * poisson))
    mu = young / (2 * (1 + poisson))
    D = np.zeros((6, 6), dtype=float)
    D[:3, :3] = lam
    np.fill_diagonal(D, lam + 2 * mu)
    D[3, 3] = D[4, 4] = D[5, 5] = mu

    x = nodes[:, 0]
    y = nodes[:, 1]
    z = nodes[:, 2]

    e = elements
    P = np.stack(
        [
            np.stack([x[e[:, k]], y[e[:, k]], z[e[:, k]]], axis=1)
            for k in range(4)
        ],
        axis=1,
    )  # (M, 4, 3)

    p0 = P[:, 0, :]
    J = np.stack(
        [
            P[:, k, :] - p0 for k in (1, 2, 3)
        ],
        axis=1,
    ).transpose(0, 2, 1)  # (M, 3, 3) columnas = p_k - p0

    detJ = np.linalg.det(J)
    valid = np.abs(detJ) > 1e-15
    detJ = np.where(valid, detJ, 1.0)
    volume = detJ / 6.0

    invJ = np.linalg.inv(J)  # (M,3,3); fila i = grad(N_i) p/ i=1,2,3 (x = J·ξ)
    g1 = invJ[:, 0, :]
    g2 = invJ[:, 1, :]
    g3 = invJ[:, 2, :]
    g0 = -(g1 + g2 + g3)

    # Construir B (M,6,12)
    M = e.shape[0]
    B = np.zeros((M, 6, 12), dtype=float)
    for ni, g in enumerate((g0, g1, g2, g3)):
        dof = 3 * ni
        B[:, 0, dof + 0] = g[:, 0]
        B[:, 1, dof + 1] = g[:, 1]
        B[:, 2, dof + 2] = g[:, 2]
        B[:, 3, dof + 0] = g[:, 1]
        B[:, 3, dof + 1] = g[:, 0]
        B[:, 4, dof + 1] = g[:, 2]
        B[:, 4, dof + 2] = g[:, 1]
        B[:, 5, dof + 0] = g[:, 2]
        B[:, 5, dof + 2] = g[:, 0]

    # Ke = volume * B^T D B  (M,12,12)
    BD = np.matmul(B.transpose(0, 2, 1), D)  # (M,12,6)
    Ke = np.matmul(BD, B)  # (M,12,12)
    Ke *= volume[:, None, None]

    # u_e por elemento: (M,4,3) nodo-mayor/componente-menor -> (M,12)
    ue = np.stack([u[:, e[:, k]] for k in range(4)], axis=2)  # (3, M, 4)
    ue = ue.transpose(1, 2, 0).reshape(M, 12)  # (M,4,3) -> (M,12)
    # contrib = u_e^T Ke u_e
    Ku = np.einsum("mij,mj->mi", Ke, ue)
    contrib = np.einsum("mi,mi->m", ue, Ku)
    contrib = np.where(valid, contrib, 0.0)

    return 0.5 * float(contrib.sum())
