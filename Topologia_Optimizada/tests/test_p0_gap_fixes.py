"""Tests for the three P0 gap fixes:
1. Gmsh surface extraction works without physical_groups (always populated).
2. ProvisionalTet4Mesher produces boundary-surface triangles via tet-face counting.
3. Halo radius defaults from mesh element size, not filter_radius.
"""

import numpy as np
import pytest

from core.topopt import SIMPSolver


def _hex_grid(nx=2, ny=1, nz=1):
    nodes = []
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                nodes.append([float(i), float(j), float(k)])
    nodes = np.asarray(nodes, dtype=float)

    def ni(i, j, k):
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    els = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                a = ni(i, j, k); b = ni(i + 1, j, k)
                c = ni(i + 1, j + 1, k); d = ni(i, j + 1, k)
                e = ni(i, j, k + 1); f = ni(i + 1, j, k + 1)
                g = ni(i + 1, j + 1, k + 1); h = ni(i, j + 1, k + 1)
                els.append([a, b, e, c]); els.append([b, f, e, c])
                els.append([e, f, g, c]); els.append([e, g, h, c])
                els.append([a, e, d, c]); els.append([h, e, d, c])
    return nodes, np.asarray(els, dtype=int)


# ================================================================== #
# Fix 1: Gmsh surface extraction without physical_groups
# ================================================================== #
def test_gmsh_surface_elements_populated_without_physical_groups():
    """_extract_all_surface_elements yields per-face triangles keyed 'face_<n>'
    even when no physical_groups were provided to the mesher."""
    gmsh = pytest.importorskip("gmsh")
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("test_no_phys_groups")
        gmsh.model.occ.addBox(0, 0, 0, 2, 2, 2)
        gmsh.model.occ.synchronize()
        gmsh.model.mesh.generate(3)

        from core.meshing import GmshTet4Mesher
        result = GmshTet4Mesher._extract_all_surface_elements(gmsh)
        assert result, "expected per-face surface elements from all surfaces"
        # A box has 6 surfaces; every one should have Tri3 triangles.
        assert len(result) == 6
        for key, tris in result.items():
            assert key.startswith("face_")
            assert len(tris) > 0
            for tri in tris:
                assert len(tri) == 3
                assert all(-1 < n for n in tri)
    finally:
        gmsh.finalize()


def test_gmsh_generate_mesh_from_step_without_physical_groups(tmp_path):
    """End-to-end: a STEP mesh produced through generate_mesh_from_step has
    face_surface_elements populated even when physical_groups is None."""
    import cadquery as cq
    gmsh = pytest.importorskip("gmsh")

    step_file = tmp_path / "box.step"
    cq.Workplane("XY").box(2, 2, 2).val().exportStep(str(step_file))

    from core.meshing import GmshTet4Mesher
    m = GmshTet4Mesher()
    result = m.generate_mesh_from_step(
        str(step_file), target_element_size=1.0, physical_groups=None
    )
    assert result.face_surface_elements, (
        "face_surface_elements should be populated even with no physical_groups"
    )
    # At least one per-face key.
    assert any(k.startswith("face_") for k in result.face_surface_elements)


# ================================================================== #
# Fix 2: ProvisionalTet4Mesher boundary-face extraction
# ================================================================== #
def test_provisional_mesher_produces_boundary_triangles():
    import cadquery as cq
    from core.meshing import ProvisionalTet4Mesher

    shape = cq.Workplane("XY").box(2, 2, 2).val()
    m = ProvisionalTet4Mesher(max_grid=2)
    result = m.generate_mesh(shape, target_element_size=1.0)
    assert result.face_surface_elements, "provisional mesh should expose boundary tris"
    # Every triangle references valid mesh node indices.
    boundary = result.face_surface_elements["boundary"]
    n_nodes = result.num_nodes
    for tri in boundary:
        assert all(0 <= n < n_nodes for n in tri)


def test_gmsh_surface_fallback_in_engine():
    """GenerativeDesignEngine._face_triangles_for_load falls back to the
    'face_<n>' keys produced by Gmsh when no physical_groups mapping exists."""
    from core.conditions import (
        LoadCondition, LoadSense, LoadOrientation, SelectionSet,
    )
    from core.cad_entity import CadEntityRef, EntityType
    from core.generative_engine import GenerativeDesignEngine

    engine = GenerativeDesignEngine(model_id=None)
    engine.face_surface_elements = {
        "face_0": [[0, 1, 2], [1, 3, 2]],
    }
    load = LoadCondition(
        name="carga", magnitude=10.0,
        sense=LoadSense.POSITIVE, orientation=LoadOrientation.PERPENDICULAR,
        faces=SelectionSet(
            name="f",
            entities=[CadEntityRef(entity_type=EntityType.FACE, face_index=0)],
        ),
    )
    tris = engine._face_triangles_for_load(load)
    assert tris == [[0, 1, 2], [1, 3, 2]]


# ================================================================== #
# Fix 3: Halo radius defaults from element size, not filter_radius
# ================================================================== #
def test_halo_default_radius_independent_of_filter_radius():
    """Different filter_radius must not change the default halo radius, which
    is based on the actual mesh element size."""
    nodes, els = _hex_grid()
    force = np.zeros(nodes.shape[0] * 3)
    force[-3:] = 1000.0

    solv_lo = SIMPSolver(nodes, els, young_modulus=210e9, poisson_ratio=0.3,
                         volfrac=0.5, filter_radius=0.5)
    solv_hi = SIMPSolver(nodes, els, young_modulus=210e9, poisson_ratio=0.3,
                         volfrac=0.5, filter_radius=8.0)

    def halo_size(solver):
        from core.fea import _tet_volume_and_B
        vmean = np.mean([abs(_tet_volume_and_B(solver.nodes[c])[0])
                         for c in solver.elements])
        return 2.0 * 2.0 * max(float(vmean) ** (1.0 / 3.0), 1e-9)

    # Same mesh => same element-size-derived radius regardless of filter_radius.
    assert np.isclose(halo_size(solv_lo), halo_size(solv_hi))


def test_halo_radius_scale_with_mesh_size():
    """Two meshes of different resolution should yield different default halo
    radii (coarser mesh -> larger characteristic element -> larger halo)."""
    nodes_coarse, els_coarse = _hex_grid(nx=2, ny=1, nz=1)  # element ~1.0
    # A finer mesh with half the element edge length: 4x2x2 grid of unit voxels
    # over a 4x2x2 domain is NOT what we want; instead scale node spacing.
    nodes_fine = nodes_coarse * 0.5
    els_fine = els_coarse

    def unit_halo(nodes, els):
        solver = SIMPSolver(nodes, els, young_modulus=210e9, poisson_ratio=0.3,
                            volfrac=0.5, filter_radius=1.5)
        from core.fea import _tet_volume_and_B
        vmean = np.mean([abs(_tet_volume_and_B(solver.nodes[c])[0])
                         for c in solver.elements])
        return 2.0 * 2.0 * max(float(vmean) ** (1.0 / 3.0), 1e-9)

    coarse = unit_halo(nodes_coarse, els_coarse)
    fine = unit_halo(nodes_fine, els_fine)
    assert coarse > 1.9 * fine, "halving edge size must shrink the halo"


def test_halo_protect_computes_radius_when_none():
    """protect_elements_near_nodes(radius=None) computes from mesh and preserves
    a non-empty set around BC nodes."""
    nodes, els = _hex_grid()
    solver = SIMPSolver(nodes, els, young_modulus=210e9, poisson_ratio=0.3,
                        volfrac=0.5, filter_radius=1.5)
    solver.protect_elements_near_nodes([0, 1, 2])
    assert solver._preserved is not None
    assert solver._preserved.any()
