"""VOL-MATCH: la isosuperficie debe conservar el material del campo.

Regresión del "sigue inflando / no representa lo optimizado" (18-sep-2026): el
promedio elemento→nodo diluye los miembros delgados, así que la isosuperficie
extraída al umbral que pide el usuario sale con una fracción del material del
diseño. Medido en un caso real (envelope, 63 750 tets, umbral 0.3): 27.7% del
dominio extraído frente a 43.9% del conjunto de elementos; y en la app, el
sólido registrado quedó con 31% del material del campo.

`resolve_volume_threshold` busca por bisección el umbral que hace que el
volumen encerrado iguale el material que el umbral del usuario define en el
campo de elementos, y reporta objetivo/alcanzado/ratio (nunca silencioso).
"""
import sys

import numpy as np

from core.cad_reconstruction import (MarchingTetrahedraExtractor,
                                     resolve_volume_threshold)
from core.generative_engine import _voxel_tet_mesh

MATERIAL = 1.0
VOID = 1e-3


def _placa_delgada():
    """Caja de 8x8x8 voxels con UNA fila de voxels de material (placa de 1 voxel).

    Es el caso patológico del promedio nodal: los nodos de la placa tienen 1
    elemento denso de ~6 incidentes, así que su densidad nodal queda muy por
    debajo del umbral del usuario y la placa desaparece de la isosuperficie.
    """
    nodes, els, _ = _voxel_tet_mesh(np.zeros(3), np.array([8.0, 8.0, 8.0]), 1.0)
    cent = nodes[els].mean(axis=1)
    dens = np.where((cent[:, 2] > 3.4) & (cent[:, 2] < 4.6), MATERIAL, VOID)
    p = nodes[els]
    vol = np.abs(np.einsum("ij,ij->i", p[:, 1] - p[:, 0],
                           np.cross(p[:, 2] - p[:, 0],
                                    p[:, 3] - p[:, 0]))) / 6.0
    return (np.asarray(nodes, dtype=float), np.asarray(els, dtype=int),
            np.asarray(dens, dtype=float), float(vol[dens > 0.5].sum()))


def _volumen(res):
    v = np.asarray(res.data["vertices"], dtype=float)
    t = np.asarray(res.data["triangles"], dtype=int)
    if v.size == 0 or t.size == 0:
        return 0.0
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    return abs(float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0))


def test_umbral_del_usuario_pierde_material():
    """Punto de partida medido: al umbral pedido se extrae una fracción."""
    nodes, els, dens, objetivo = _placa_delgada()
    assert objetivo > 0.0
    ex = MarchingTetrahedraExtractor()
    extraido = _volumen(ex.extract(nodes, els, dens, threshold=0.5))
    assert extraido < 0.5 * objetivo, (
        f"el caso de prueba debe ser lossy: {extraido:.1f} vs {objetivo:.1f}")


def test_vol_match_conserva_el_material_del_campo():
    nodes, els, dens, objetivo = _placa_delgada()
    ex = MarchingTetrahedraExtractor()
    t_usado, meta, res = resolve_volume_threshold(ex, nodes, els, dens, 0.5)
    assert res is not None
    extraido = _volumen(res)
    assert 0.85 * objetivo <= extraido <= 1.15 * objetivo, (
        f"t*={t_usado:.4f} extrajo {extraido:.1f} de {objetivo:.1f}")
    # el reporte es explícito: umbral pedido, usado, objetivo y ratio
    assert meta["volume_matching"] is True
    assert meta["marching_threshold_requested"] == 0.5
    assert meta["marching_threshold_used"] == round(float(t_usado), 4)
    assert meta["material_volume_target_mm3"] == round(objetivo, 3)
    assert 0.85 <= meta["material_volume_ratio"] <= 1.15


def test_vol_match_sin_material_no_inventa_umbral():
    """Sin elementos sobre el umbral se conserva el umbral pedido y se reporta."""
    nodes, els, _, _ = _placa_delgada()
    dens = np.full(els.shape[0], VOID)
    ex = MarchingTetrahedraExtractor()
    t_usado, meta, res = resolve_volume_threshold(ex, nodes, els, dens, 0.3)
    assert t_usado == 0.3 and res is None
    assert meta["volume_matching"] == "no_material_sobre_umbral"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
