"""Orden fill→smooth + tope max_hole_edges (FILL-SMOOTH-ORDER, FILL-CAP).

Aprobado explícitamente por el usuario (fuera de plan, confirm-gate Fase 0.5):
el suavizado fijaba los vértices de los loops abiertos del marching (eran el
"borde" en ese momento) y el abanico plano del fill posterior se pegaba sobre
superficie ya lisa. Ahora el tapado corre ANTES del suavizado y lo no tapado
queda explícito en metadata (FILL-REPORT), nunca en silencio.
"""
import numpy as np
import pytest

from core.cad_reconstruction import (
    MeshHoleFiller,
    ReconstructionPipeline,
    ReconstructionResult,
    ReconstructionStage,
    ReconstructionStatus,
    SurfaceExtractor,
    _boundary_loops,
    fill_holes,
    smooth_surface_mesh,
)


def _open_box():
    """Cubo unidad sin tapa superior: 10 triángulos, 1 loop abierto de 4."""
    v = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
        [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
    ], dtype=float)
    f = np.array([
        (0, 1, 2), (0, 2, 3),          # fondo
        (0, 4, 5), (0, 5, 1),          # +Y? laterales
        (2, 6, 7), (2, 7, 3),
        (0, 3, 7), (0, 7, 4),
        (1, 5, 6), (1, 6, 2),
    ], dtype=int)
    return v, f


class _HoledBoxExtractor(SurfaceExtractor):
    def __init__(self, v, t):
        self.v = np.asarray(v, dtype=float)
        self.t = np.asarray(t, dtype=int)

    def extract(self, nodes, elements, densities, threshold=0.5):
        return ReconstructionResult(
            stage=ReconstructionStage.SURFACE_MESH,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": self.v.copy(), "triangles": self.t.copy()},
            metadata={},
        )


class _PassthroughFitter:
    def fit(self, vertices, triangles):
        return ReconstructionResult(
            stage=ReconstructionStage.BREP_SOLID,
            status=ReconstructionStatus.COMPLETED,
            data={"vertices": np.asarray(vertices),
                  "triangles": np.asarray(triangles)},
            metadata={},
        )


def _dummy_inputs():
    nodes = np.zeros((4, 3))
    elements = np.zeros((1, 4), dtype=int)
    densities = np.ones(1)
    return nodes, elements, densities


def test_fill_runs_before_smooth_patch_gets_smoothed():
    v, t = _open_box()
    assert len(_boundary_loops(t)) == 1
    pipe = ReconstructionPipeline(
        surface_extractor=_HoledBoxExtractor(v, t),
        brep_fitter=_PassthroughFitter(),
    )
    out = pipe.run(*_dummy_inputs())
    assert out.status == ReconstructionStatus.COMPLETED, out.error_message
    stage = pipe.get_stage_result(ReconstructionStage.SMOOTHED_MESH)
    assert stage.metadata["holes_filled"] == 1
    assert stage.metadata["holes_skipped"] == 0
    assert stage.metadata["open_loops_after"] == 0
    assert stage.metadata["largest_hole_edges"] == 4
    assert stage.metadata["fill_before_smooth"] is True
    # El parche se suavizó con el resto: el centroide agregado ya no está en
    # la media cruda del loop (con el orden viejo quedaba exactamente ahí,
    # congelado como borde + abanico posterior sin suavizar).
    n0 = v.shape[0]
    raw_mean = v[[4, 5, 6, 7]].mean(axis=0)
    new_centroid = np.asarray(stage.data["vertices"])[n0]
    assert not np.allclose(new_centroid, raw_mean)
    # Referencia del orden viejo (smooth→fill): el centroide queda en la media.
    sv, st = smooth_surface_mesh(v, t, iterations=3, alpha=0.5)
    fv_old, _, n_old = fill_holes(sv, st)
    assert n_old == 1
    assert np.allclose(fv_old[n0], sv[[4, 5, 6, 7]].mean(axis=0))
    assert not np.allclose(new_centroid, fv_old[n0])


def test_max_hole_edges_skips_big_loops_and_reports():
    v, t = _open_box()
    pipe = ReconstructionPipeline(
        surface_extractor=_HoledBoxExtractor(v, t),
        brep_fitter=_PassthroughFitter(),
        max_hole_edges=3,
    )
    out = pipe.run(*_dummy_inputs())
    assert out.status == ReconstructionStatus.COMPLETED, out.error_message
    stage = pipe.get_stage_result(ReconstructionStage.SMOOTHED_MESH)
    assert stage.metadata["holes_filled"] == 0
    assert stage.metadata["holes_skipped"] == 1
    assert stage.metadata["open_loops_after"] == 1
    # Malla intacta: mismos 10 triángulos, sin vértices agregados.
    assert np.asarray(stage.data["triangles"]).shape[0] == t.shape[0]
    assert np.asarray(stage.data["vertices"]).shape[0] == v.shape[0]


def test_filler_metadata_direct_and_invalid_cap():
    v, t = _open_box()
    r = MeshHoleFiller().fill(v, t)
    assert r.metadata["holes_filled"] == 1
    assert r.metadata["holes_skipped"] == 0
    assert r.metadata["open_loops_before"] == 1
    assert r.metadata["open_loops_after"] == 0
    r2 = MeshHoleFiller().fill(v, t, max_hole_edges=3)
    assert r2.metadata["holes_filled"] == 0
    assert r2.metadata["holes_skipped"] == 1
    with pytest.raises(ValueError):
        ReconstructionPipeline(max_hole_edges=2)
    with pytest.raises(ValueError):
        ReconstructionPipeline(max_hole_edges="muchos")  # type: ignore[arg-type]
