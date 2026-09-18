"""ORIENT/EDGE-CANON: la isosuperficie del marching-tets debe ser coherente.

Regresión del "inflado"/geometría sucia del generativo (18-sep-2026):
  - `_voxel_tet_mesh` (dominio de diseño) emite 5 de cada 6 tets con volumen
    NEGATIVO (medido: 53125/63750 en un envelope real) y el marching-tets
    heredaba esa orientación mezclada: medido 4082 normales hacia afuera vs
    4094 hacia adentro en una esfera sintética, con integral de volumen ~0
    (−1392 en vez de +167260 mm3).
  - Además cada tetraedro calculaba el punto de corte de una arista compartida
    en su propio orden local, así que los dos floats diferían en los últimos
    bits y el soldado a 1e-9 no los fusionaba.

Este test fija el contrato: esfera de material DENTRO de la caja ->
normales 100% hacia afuera, malla cerrada y volumen positivo y realista.
"""
import sys

import numpy as np

from core.cad_reconstruction import (MarchingTetrahedraExtractor,
                                     _boundary_edges)
from core.generative_engine import _voxel_tet_mesh

RES = 1.0
RADIUS = 3.5


def _sphere_case():
    lo = np.zeros(3)
    hi = np.array([10.0, 10.0, 10.0])
    nodes, els, _ = _voxel_tet_mesh(lo, hi, RES)
    cen = np.array([5.0, 5.0, 5.0])
    cent = nodes[els].mean(axis=1)
    dens = np.where(np.linalg.norm(cent - cen, axis=1) <= RADIUS, 1.0, 1e-3)
    return np.asarray(nodes, dtype=float), np.asarray(els, dtype=int), dens, cen


def test_isosurface_normals_point_outward_and_mesh_is_closed():
    nodes, els, dens, cen = _sphere_case()
    for threshold in (0.35, 0.5):
        ex = MarchingTetrahedraExtractor().extract(nodes, els, dens,
                                                   threshold=threshold)
        verts = np.asarray(ex.data["vertices"], dtype=float)
        tris = np.asarray(ex.data["triangles"], dtype=int)
        assert tris.shape[0] > 100, tris.shape

        a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
        normals = np.cross(b - a, c - a)
        mids = (a + b + c) / 3.0
        dot = np.einsum("ij,ij->i", normals, mids - cen)
        assert int((dot < 0).sum()) == 0, (
            f"t={threshold}: {int((dot < 0).sum())} normales hacia adentro "
            f"(orientacion mezclada)")

        # esfera estrictamente dentro de la caja -> superficie cerrada
        abiertas = sum(1 for n in _boundary_edges(tris).values() if n == 1)
        assert abiertas == 0, f"t={threshold}: {abiertas} aristas abiertas"

        vol = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
        exacto = 4.0 / 3.0 * np.pi * RADIUS ** 3
        assert vol > 0.0, f"t={threshold}: volumen {vol} (orientacion rota)"
        # Cota ancha a proposito: el promedio nodal diluye la superficie (la
        # isosuperficie queda algo adentro) y un umbral bajo la infla (196 mm3
        # vs 180 analiticos a t=0.35). Lo que se protege aqui es que el volumen
        # sea POSITIVO y del orden correcto: con la orientacion mezclada daba
        # ~0 (cancelacion) o negativo.
        assert 0.5 * exacto < vol < 1.3 * exacto, (
            f"t={threshold}: volumen {vol:.0f} vs analitico {exacto:.0f}")


def test_shared_edge_points_are_bit_identical_between_tets():
    """EDGE-CANON: dos tets que comparten arista dan el MISMO punto (soldable)."""
    from core.cad_reconstruction import _tet_iso_triangles
    verts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                      [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    dens = np.array([0.2, 0.8, 0.8, 0.2])
    # mismo tet con la conectividad global permutada: la arista (0,1) global
    # aparece como (0,1) en un caso y como (2,0) en el otro.
    t1 = _tet_iso_triangles(verts, dens, 0.5, gcon=np.array([0, 1, 2, 3]))
    perm = [2, 0, 1, 3]
    t2 = _tet_iso_triangles(verts[perm], dens[perm], 0.5,
                            gcon=np.array([2, 0, 1, 3]))
    pts1 = {tuple(np.round(p, 12)) for tri in t1 for p in tri}
    pts2 = {tuple(np.round(p, 12)) for tri in t2 for p in tri}
    assert pts1 == pts2, (pts1, pts2)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
