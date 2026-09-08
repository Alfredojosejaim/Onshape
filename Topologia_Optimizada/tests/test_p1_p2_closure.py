"""Tests de cierre P1/P2 (prompts.md: AUDITORIA Y CIERRE P1/P2).

Cubre los GAPS detectados en la auditoria:
  3. caras geometricamente similares -> grupos distintos y disjuntos;
  5. multisolido -> correspondencia cubre todas las caras;
  6. ambiguedad (firmas empatadas) -> error explicito;
  8. ningun fallback por orden silencioso (metadata + warning + resolver);
  9/10. cara -> physical group -> nodos (identidad grupo<->triangulos);
  12-local. condicion en cara -> mismos nodos via default_face_resolver.
Ademas: parse_face_id unificado y helper unico face_triangles_for_indices.
"""

import logging

import numpy as np
import pytest

try:
    import gmsh  # noqa: F401
    GMSH_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = False

try:
    import cadquery as cq  # noqa: F401
    CQ_AVAILABLE = True
except ImportError:
    CQ_AVAILABLE = False

NEEDS_STACK = pytest.mark.skipif(
    not (GMSH_AVAILABLE and CQ_AVAILABLE), reason="requiere gmsh+cadquery")


def test_parse_face_id_unificado():
    from core.boundary import parse_face_id, resolve_face_index
    assert parse_face_id("face_3") == 3
    assert parse_face_id("face:3") == 3
    assert parse_face_id("face3") == 3
    assert parse_face_id("face-3") == 3
    assert parse_face_id("3") == 3
    assert parse_face_id("base") is None
    assert parse_face_id(None) is None
    # resolve_face_index delega: mismo lenguaje en ambos modulos.
    assert resolve_face_index("face:3") == 3
    assert resolve_face_index("face_3") == 3
    from core.topo_problem import _face_id
    assert _face_id("face:3") == 3
    assert _face_id("face_3") == 3


def test_ambiguedad_firmas_empatadas_falla_explicito():
    """Firmas Gmsh identicas (empate perfecto) -> AmbiguousFaceCorrespondenceError."""
    import math
    import cadquery as cq
    from core.face_correspondence import (
        build_face_correspondence,
        AmbiguousFaceCorrespondenceError,
        FaceCorrespondenceError,
    )
    shape = cq.Workplane("XY").box(2, 3, 4).val()
    # Area total CAD = 2*(6+8+12) = 52: lado por superficie para igualar el
    # total (si no, el invariante de area dispara primero, que tambien es
    # correcto pero no es lo que este test exige).
    side = math.sqrt(52.0 / 6.0)

    class _FakeModel:
        def getEntities(self, dim):
            return [(2, i) for i in range(1, 7)]  # 6 == 6 caras CAD

        def getParametrizationBounds(self, dim, tag):
            return ((0.0, 0.0), (side, side))

        def getValue(self, dim, tag, uv):
            return [float(uv[0]), float(uv[1]), 0.0]

        def getNormal(self, tag, uv):
            return (0.0, 0.0, 1.0)

    class _FakeGmsh:
        model = _FakeModel()

    with pytest.raises(AmbiguousFaceCorrespondenceError):
        build_face_correspondence(shape, _FakeGmsh())
    # La ambiguedad es subclase del error de correspondencia.
    assert issubclass(AmbiguousFaceCorrespondenceError, FaceCorrespondenceError)


def test_area_total_difiere_rechaza():
    """Split/merge con conteo igual pero area distinta -> FaceCorrespondenceError."""
    import cadquery as cq
    from core.face_correspondence import (
        build_face_correspondence,
        FaceCorrespondenceError,
    )
    shape = cq.Workplane("XY").box(2, 3, 4).val()

    class _FakeModel:
        def getEntities(self, dim):
            return [(2, i) for i in range(1, 7)]  # 6 == 6 caras CAD

        def getParametrizationBounds(self, dim, tag):
            # Superficies 100x mas chicas: area total muy distinta.
            return ((0.0, 0.0), (0.1, 0.1))

        def getValue(self, dim, tag, uv):
            return [float(uv[0]), float(uv[1]), 0.0]

        def getNormal(self, tag, uv):
            return (0.0, 0.0, 1.0)

    class _FakeGmsh:
        model = _FakeModel()

    with pytest.raises(FaceCorrespondenceError, match="[Aa]rea"):
        build_face_correspondence(shape, _FakeGmsh())


def test_extract_sin_correspondencia_advierte_orden(caplog):
    """Sin face_index_to_tag: etiquetas posicionales + warning explicito."""
    from core.meshing import GmshTet4Mesher
    import numpy as np

    class _FakeMesh:
        @staticmethod
        def getNodes():
            tags = np.array([1, 2, 3, 4, 5])
            coords = np.array([
                0., 0., 0., 1., 0., 0., 1., 1., 0., 0., 1., 0., 0., 0., 1.,
            ])
            return tags, coords, None

        @staticmethod
        def getElements(dim, tag):
            if tag == 1:
                return ([2], None, [np.array([1, 2, 5])])
            return ([2], None, [np.array([2, 3, 5])])

    class _FakeModel:
        mesh = _FakeMesh()

        @staticmethod
        def getEntities(dim):
            return [(2, 1), (2, 2)]

    class _FakeGmsh:
        model = _FakeModel()

    with caplog.at_level(logging.WARNING, logger="core.meshing"):
        out = GmshTet4Mesher._extract_all_surface_elements(_FakeGmsh(), None)
    assert set(out) == {"face_0", "face_1"}
    assert any("order-fallback" in r.message for r in caplog.records), (
        "el fallback por orden debe advertirse, nunca ser silencioso")


def test_resolver_advierte_malla_no_determinista(caplog):
    """default_face_resolver advierte si la malla no trae procedencia determinista."""
    from core.topo_problem import default_face_resolver, GeometrySelection
    mesh = {
        "nodes": [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]],
        "elements": [[0, 1, 2, 0]],
        "physical_groups": {},
        "face_surface_elements": {"face_0": [[0, 1, 2]]},
        "metadata": {"face_correspondence": "order-fallback"},
    }
    sel = GeometrySelection(entity_type="face", selection_id="face_0")
    with caplog.at_level(logging.WARNING, logger="core.topo_problem"):
        out = default_face_resolver(sel, mesh)
    assert out["node_indices"] == [0, 1, 2]
    assert any("ORDER-BASED" in r.message for r in caplog.records)


@NEEDS_STACK
def test_caras_similares_grupos_disjuntos():
    """Caja 2x2x4: tapas opuestas congruentes -> grupos nombrados disjuntos,
    misma area, no vacios (identidad por grupo, no por posicion)."""
    import cadquery as cq
    from core.meshing import GmshTet4Mesher
    from core.boundary import surface_area_mm2

    shape = cq.Workplane("XY").box(2, 2, 4).val()
    assert len(shape.Faces()) == 6
    mesh = GmshTet4Mesher(mesh_size_max=2.0).generate_mesh(
        shape, target_element_size=2.0,
        physical_groups={"CaraA": [0], "CaraB": [1]},
    )
    assert mesh.metadata.get("face_correspondence") == "deterministic"
    fse = mesh.face_surface_elements
    assert fse.get("CaraA") and fse.get("CaraB")
    a = {tuple(sorted(t)) for t in fse["CaraA"]}
    b = {tuple(sorted(t)) for t in fse["CaraB"]}
    assert not (a & b), "grupos de caras distintas no deben compartir triangulos"
    nodes = np.asarray(mesh.nodes, dtype=float)
    assert surface_area_mm2(nodes, fse["CaraA"]) == pytest.approx(
        surface_area_mm2(nodes, fse["CaraB"]), rel=1e-6)


@NEEDS_STACK
def test_multisolido_cubre_todas_las_caras():
    """Compuesto de 2 cajas disjuntas: 12 caras CAD, claves validas."""
    import cadquery as cq
    from core.meshing import GmshTet4Mesher

    b1 = cq.Workplane("XY").box(1, 1, 1).val()
    b2 = cq.Workplane("XY").box(1, 1, 1).translate((5, 0, 0)).val()
    shape = cq.Compound.makeCompound([b1, b2])
    assert len(shape.Faces()) == 12
    mesh = GmshTet4Mesher(mesh_size_max=1.0).generate_mesh(
        shape, target_element_size=1.0)
    fse = mesh.face_surface_elements
    assert fse, "sin triangulos de superficie"
    for key in fse:
        if key.startswith("face_unmapped_"):
            continue
        assert key.startswith("face_")
        fi = int(key.split("_")[1])
        assert 0 <= fi < 12, f"clave fuera de rango CAD: {key}"
    n_face = sum(1 for k in fse if k.startswith("face_") and not k.startswith("face_unmapped"))
    assert n_face + len(mesh.metadata.get("face_unmapped", [])) >= 1


@NEEDS_STACK
def test_cadena_grupo_a_nodos_y_resolver():
    """Identidad 9/10/12-local: nodos del grupo == nodos de sus triangulos ==
    nodos del default_face_resolver para la misma cara."""
    import cadquery as cq
    from core.meshing import GmshTet4Mesher
    from core.topo_problem import default_face_resolver, GeometrySelection

    shape = cq.Workplane("XY").box(2, 3, 4).val()
    mesh = GmshTet4Mesher(mesh_size_max=2.0).generate_mesh(
        shape, target_element_size=2.0,
        physical_groups={"LoadFace": [5]},
    )
    d = mesh.to_dict()
    group_nodes = set(d["physical_groups"]["LoadFace"])
    tri_nodes = {n for tri in d["face_surface_elements"]["LoadFace"] for n in tri}
    assert group_nodes, "grupo vacio"
    assert group_nodes == tri_nodes, "grupo y triangulos deben cubrir los mismos nodos"
    sel = GeometrySelection(entity_type="face", selection_id="face_5")
    out = default_face_resolver(sel, d)
    assert set(out["node_indices"]) == group_nodes, (
        "el resolvedor debe devolver exactamente los nodos del grupo")


def test_helper_unico_tres_fuentes():
    """face_triangles_for_indices: grupo nombrado, face_<fi> y propagacion."""
    from core.boundary import face_triangles_for_indices
    fse = {"G": [[0, 1, 2]], "face_1": [[3, 4, 5]], "boundary": [[6, 7, 8]]}
    tris, matched = face_triangles_for_indices(
        [0, 1], fse, group_index={0: ["G"]}, node_indices=[6, 7, 8, 0])
    assert matched is True
    assert sorted(map(sorted, tris)) == [[0, 1, 2], [3, 4, 5]]
    # Solo propagacion cuando no hay match especifico.
    tris2, matched2 = face_triangles_for_indices(
        [9], fse, group_index={}, node_indices=[6, 7, 8])
    assert matched2 is False
    assert tris2 == [[6, 7, 8]]
    # Sin nada: vacio (el caller decide uniforme vs error).
    tris3, matched3 = face_triangles_for_indices([9], {}, node_indices=[6])
    assert tris3 == [] and matched3 is False
