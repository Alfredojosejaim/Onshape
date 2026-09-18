"""SOLID-GUARD: la cadena B-Rep no debe entregar una cáscara como "sólido".

Regresión medida el 18-sep-2026 con el caso envelope del usuario: el modelo
registrado por la app quedaba con `num_solids = 0` (una cáscara de 5619 caras
exportada a un STEP de 15 MB) porque `BRepCheck_Analyzer` da por válida una
cáscara y los pasos `UnifySameDomain` / `ShapeCustom_BSplineRestriction` /
`ShapeDivideContinuity` podían devolverla, y el pipeline la etiquetaba
`BREP_SOLID`/completed. La app registraba y mostraba una superficie.
"""
import sys

from OCP.BRep import BRep_Builder
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Compound

from core.cad_reconstruction import _shape_has_solid


def _box_solid():
    return BRepPrimAPI_MakeBox(1.0, 2.0, 3.0).Solid()


def _shell_of(shape):
    exp = TopExp_Explorer(shape, TopAbs_SHELL)
    assert exp.More()
    return TopoDS.Shell_s(exp.Current())


def _compound(*shapes):
    comp = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(comp)
    for s in shapes:
        builder.Add(comp, s)
    return comp


def test_solid_is_recognized():
    assert _shape_has_solid(_box_solid()) is True


def test_bare_shell_is_not_a_solid():
    assert _shape_has_solid(_shell_of(_box_solid())) is False


def test_compound_with_solid_counts():
    assert _shape_has_solid(_compound(_box_solid())) is True


def test_compound_with_only_shells_does_not_count():
    # `ShapeDivideContinuity.Result()` devuelve un COMPOUND: si trae solo
    # cáscaras, no puede registrarse como sólido CAD.
    assert _shape_has_solid(_compound(_shell_of(_box_solid()))) is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
