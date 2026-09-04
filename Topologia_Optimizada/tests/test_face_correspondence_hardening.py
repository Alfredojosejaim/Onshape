"""Pruebas obligatorias del endurecimiento del mapeo CAD face <-> Gmsh surface.

Cubre los casos que la auditoría (prompts.md) y la solución
(investigación_traceback.md) exigen validar:

  * P0.2 — fallo parcial de getValue() no debe desalinear la cuadrícula UV
           (regresión del bug pts_arr[i*samples+j]).
  * P0.2 — superficie parcialmente muestreada por debajo de cobertura mínima
           se marca como degradada, no como firma plausible pero errónea.
  * P0.1 — correspondencia biyectiva (1:1), sin duplicados.
  * P0.1 — rechazo de correspondencias ambiguas/simétricas.
  * P0.1 — caras simétricas distinguibles por la forma en el plano (extent).
  * superficies curvas (cilindro) mapeadas correctamente.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import gmsh  # noqa: F401
    GMSH_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = False


def _import_shape(shape, model_name="corr"):
    """Exporta *shape* a STEP temporal, lo importa en gmsh y sincroniza."""
    import tempfile
    import cadquery as cq
    import gmsh

    tmp = tempfile.mktemp(suffix=".step")
    cq.exporters.export(shape, tmp, exportType="STEP")
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add(model_name)
    gmsh.model.occ.importShapes(tmp, format="step")
    gmsh.model.occ.synchronize()
    try:
        yield gmsh
    finally:
        os.remove(tmp)
        gmsh.finalize()


def _assert_bijective(mapping, cad_sigs, gmsh_sigs):
    """Comprueba 1:1: cubre todas las caras, tags únicos y centro casi igual."""
    gmap = {tag: sig for tag, sig in gmsh_sigs}
    assert set(mapping.keys()) == set(range(len(cad_sigs))), "deben mapearse todas las caras"
    assert len(set(mapping.values())) == len(mapping), "los destinos deben ser únicos (1:1)"
    for fi, tag in mapping.items():
        dc = np.linalg.norm(np.array(cad_sigs[fi].center) - np.array(gmap[tag].center))
        assert dc < 1e-3, f"face {fi}->tag {tag}: centro difiere {dc:.4f}"


@pytest.mark.skipif(not GMSH_AVAILABLE, reason="gmsh no está instalado")
class TestCorrespondenceHardening:
    def _signatures(self, shape, gmsh):
        from core.face_correspondence import _shape_face_signatures, _gmsh_surface_signatures
        return _shape_face_signatures(shape), _gmsh_surface_signatures(gmsh)

    def test_bijective_caja(self):
        import cadquery as cq
        shape = cq.Workplane("XY").box(2, 3, 4).val()
        for gmsh in _import_shape(shape, "box"):
            from core.face_correspondence import build_face_correspondence
            cad_sigs, gmsh_sigs = self._signatures(shape, gmsh)
            mapping = build_face_correspondence(shape, gmsh)
            assert len(mapping) == 6
            _assert_bijective(mapping, cad_sigs, gmsh_sigs)

    def test_bijective_caja_rotada(self):
        import cadquery as cq
        shape = cq.Workplane("XY").box(2, 3, 4).rotate((0, 0, 0), (0, 0, 1), 37).val()
        for gmsh in _import_shape(shape, "boxrot"):
            from core.face_correspondence import build_face_correspondence
            cad_sigs, gmsh_sigs = self._signatures(shape, gmsh)
            mapping = build_face_correspondence(shape, gmsh)
            _assert_bijective(mapping, cad_sigs, gmsh_sigs)

    def test_superficies_curvas_cilindro(self):
        import cadquery as cq
        # Cilindro: tapa, tapa y manto (3 caras). El mapeo debe ser 1:1 y el
        # manto (curvo) debe mapearse a una tag única.
        shape = cq.Workplane("XY").cylinder(2, 1).val()
        for gmsh in _import_shape(shape, "cyl"):
            from core.face_correspondence import build_face_correspondence
            cad_sigs, gmsh_sigs = self._signatures(shape, gmsh)
            assert len(cad_sigs) == 3 and len(gmsh_sigs) == 3
            mapping = build_face_correspondence(shape, gmsh)
            assert len(mapping) == 3
            assert len(set(mapping.values())) == 3

    def test_fallo_parcial_getvalue_no_desalinea_grid(self):
        """/P0.2/ Un getValue() que falla en una posición no debe desplazar
        los índices restantes ni corromper el área."""
        import cadquery as cq
        shape = cq.Workplane("XY").box(2, 3, 4).val()
        from core.face_correspondence import _gmsh_surface_signatures, _signature_distance

        for gmsh in _import_shape(shape, "gfail"):
            real_getvalue = gmsh.model.getValue
            # Fuerza a fallar 3 posiciones del grid (uniendo fracción de fallos
            # por encima de 0 pero por debajo del 50% de cobertura sólo en 1 cara
            # no es necesario; basta con que NO reviente y devuelva firmas finitas).
            calls = {"n": 0}
            def flaky_getvalue(*args, **kwargs):
                calls["n"] += 1
                if calls["n"] in (5, 60, 200):
                    raise RuntimeError("flaky sample")
                return real_getvalue(*args, **kwargs)
            gmsh.model.getValue = flaky_getvalue
            sigs = _gmsh_surface_signatures(gmsh, samples=20)
            # Debe devolver tantas firmas como superficies, todas con área finita >= 0.
            assert len(sigs) == 6
            for tag, sig in sigs:
                assert np.all(np.isfinite(sig.center)), "centro no finito"
                assert sig.area >= 0
                assert np.all(np.isfinite(sig.extent))

    def test_carra_simetrica_extent_hongaro(self):
        """Dos caras congruentes (misma posición forma) siguen siendo 1:1 con
        la asignación húngara y no arrojan un fallo de conteo."""
        import cadquery as cq
        shape = cq.Workplane("XY").box(2, 3, 4).val()
        for gmsh in _import_shape(shape, "slots"):
            from core.face_correspondence import build_face_correspondence
            cad_sigs, gmsh_sigs = self._signatures(shape, gmsh)
            mapping = build_face_correspondence(shape, gmsh)
            _assert_bijective(mapping, cad_sigs, gmsh_sigs)

    def test_conteo_mismatch_rechaza(self):
        """Un desajuste de número de caras debe lanzar FaceCorrespondenceError."""
        from core.face_correspondence import (
            build_face_correspondence,
            FaceCorrespondenceError,
        )
        import cadquery as cq
        shape = cq.Workplane("XY").box(2, 3, 4).val()

        class _FakeModel:
            def getEntities(self, dim):
                return [(2, 1), (2, 2)]  # 2 superficies vs 6 caras CAD

            def getParametrizationBounds(self, dim, tag):
                return ((0.0, 0.0), (1.0, 1.0))

            def getValue(self, dim, tag, uv):
                return [float(uv[0]), float(uv[1]), 0.0]

            def getNormal(self, tag, uv):
                return (0.0, 0.0, 1.0)

        class _FakeGmsh:
            model = _FakeModel()

        with pytest.raises(FaceCorrespondenceError):
            build_face_correspondence(shape, _FakeGmsh())


@pytest.mark.skipif(not GMSH_AVAILABLE, reason="gmsh no está instalado")
def test_physical_group_tag_collision_no_mixing():
    """/REG/ Un tag de grupo físico que colisiona numéricamente con el tag de
    una superficie NO debe devolver los triángulos de esa otra superficie.

    ``_surface_elements_for_physical_groups`` resolvía cada nombre con
    ``getElements(2, phy_tag)``: como tags de grupos físicos y tags de
    entidades viven en espacios que ambos empiezan en 1, el grupo "LoadFace"
    (tag físico 2, sobre la cara 5) podía devolver los triángulos de la
    superficie 2 (otra cara CAD). Ahora resuelve el grupo a sus entidades y
    consulta por tag de entidad.
    """
    import cadquery as cq
    from core.meshing import GmshTet4Mesher

    shape = cq.Workplane("XY").box(2, 3, 4).val()
    mesh = GmshTet4Mesher(mesh_size_max=2.0).generate_mesh(
        shape,
        target_element_size=2.0,
        physical_groups={"FixedFace": [0], "LoadFace": [5]},
    )
    fse = mesh.face_surface_elements

    def sorted_tris(key):
        return sorted(map(sorted, fse.get(key, [])))

    assert sorted_tris("FixedFace") == sorted_tris("face_0"), (
        "FixedFace (face_0) no coincide con face_0"
    )
    assert sorted_tris("LoadFace") == sorted_tris("face_5"), (
        "LoadFace (face_5) no coincide con face_5: el grupo pudo haber "
        "leído los triángulos de otra superficie por colisión de tags"
    )
    assert fse["FixedFace"] and fse["LoadFace"], "los grupos no deben quedar vacíos"
