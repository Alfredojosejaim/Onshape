"""Fase 2 — gmsh physical groups para selección exacta de nodos por cara CAD.

Verifica que el mallador Gmsh definitivo:
  * Crea grupos físicos nombrados sobre las caras (dim=2) ANTES de mallar.
  * Expone, tras el mallado, los índices de nodo (0-based) de cada grupo
    (cara) en ``MeshResult.physical_groups``.
  * Los índices son válidos, no vacíos y un subconjunto estricto de la malla.
  * Se conservan en ``to_dict()``.

Y que la capa de importación (KratosAdapter) reconstruye esos grupos como
SubModelParts nombrados (con un fake que imita la API de Kratos, ya que
Kratos no está instalado en el entorno de test).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REAL_STEP_FILE = "cono.step"

try:
    import gmsh  # noqa: F401
    GMSH_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = False


def _assert_valid_groups(mesh, physical_groups):
    """Comprueba que los nodos de cada grupo son válidos y no toda la malla."""
    assert isinstance(physical_groups, dict)
    n = mesh.num_nodes
    for name, indices in physical_groups.items():
        assert isinstance(name, str)
        assert isinstance(indices, list)
        assert indices, f"grupo {name} vacío"
        assert len(indices) < n, f"grupo {name} debe ser un subconjunto estricto"
        for i in indices:
            assert 0 <= i < n, f"índice {i} fuera de rango para {name}"


def _gmsh_face_count():
    """Número de caras (surface entities) expuestas por gmsh para el STEP."""
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("_count_faces")
    gmsh.model.occ.importShapes(REAL_STEP_FILE, format="step")
    gmsh.model.occ.synchronize()
    count = len(gmsh.model.getEntities(2))
    gmsh.finalize()
    return count


# Guard simple: los tests de mallado Gmsh se saltan si no hay gmsh.
import unittest

if not GMSH_AVAILABLE:
    print("gmsh no instalado; tests de Fase 2 (gmsh) omitidos")


@unittest.skipUnless(GMSH_AVAILABLE, "gmsh no está instalado")
class TestMesherPhysicalGroups(unittest.TestCase):
    def setUp(self):
        from core.meshing import GmshTet4Mesher
        self.mesher = GmshTet4Mesher()
        # Para el cono del proyecto hay 3 superficies (índices 0,1,2).
        self.n_faces = _gmsh_face_count()
        self.assertGreaterEqual(self.n_faces, 3)

    def test_named_groups_node_sets_from_step(self):
        res = self.mesher.generate_mesh_from_step(
            REAL_STEP_FILE,
            target_element_size=5.0,
            physical_groups={"FixedFace": [0], "LoadFace": [2]},
        )
        self.assertEqual(list(res.physical_groups.keys()), ["FixedFace", "LoadFace"])
        _assert_valid_groups(res, res.physical_groups)

    def test_groups_preserved_in_to_dict(self):
        res = self.mesher.generate_mesh_from_step(
            REAL_STEP_FILE,
            target_element_size=5.0,
            physical_groups={"A": [1]},
        )
        d = res.to_dict()
        self.assertIn("physical_groups", d)
        self.assertEqual(d["physical_groups"].keys(), {"A"})

    def test_no_groups_when_none_requested(self):
        res = self.mesher.generate_mesh_from_step(REAL_STEP_FILE, target_element_size=5.0)
        self.assertEqual(res.physical_groups, {})

    def test_groups_from_shape(self):
        from adapters.cad.step_adapter import StepAdapter
        adapter = StepAdapter()
        model = adapter.load_from_file(REAL_STEP_FILE, model_name="Cono")
        shape = adapter.get_shape(model.id)
        res = self.mesher.generate_mesh(
            shape,
            target_element_size=5.0,
            physical_groups={"FixedFace": [0], "LoadFace": [2]},
        )
        _assert_valid_groups(res, res.physical_groups)

    def test_groups_from_adaptive_mesh(self):
        res = self.mesher.generate_adaptive_mesh(
            REAL_STEP_FILE,
            base_size=5.0,
            physical_groups={"FixedFace": [0]},
        )
        _assert_valid_groups(res, res.physical_groups)


class _FakeSubModelPart:
    def __init__(self, name):
        self.name = name
        self.nodes = []

    def AddNodes(self, node_ids):
        self.nodes.extend(node_ids)


class _FakeModelPart:
    """Maniquí mínimo que imita la API de Kratos usada por el adapter."""

    def __init__(self, n_nodes):
        self._n_nodes = n_nodes
        self._subs = {}

    def NumberOfNodes(self):
        return self._n_nodes

    def CreateSubModelPart(self, name):
        sub = _FakeSubModelPart(name)
        self._subs[name] = sub
        return sub

    def HasSubModelPart(self, name):
        return name in self._subs

    def GetSubModelPart(self, name):
        return self._subs[name]


class TestKratosSubmodelpartsFromGroups(unittest.TestCase):
    """Reconstrucción de SubModelParts nombrados desde los grupos físicos."""

    def _adapter(self):
        from core.kratos_adapter import KratosAdapter
        adapter = KratosAdapter.__new__(KratosAdapter)
        return adapter

    def test_creates_named_submodelparts(self):
        adapter = self._adapter()
        mp = _FakeModelPart(n_nodes=1476)
        groups = {"FixedFace": [1, 2, 3], "LoadFace": [10, 20]}
        adapter._create_submodelparts_from_groups(mp, groups)

        self.assertTrue(mp.HasSubModelPart("FixedFace"))
        self.assertTrue(mp.HasSubModelPart("LoadFace"))
        # Los ids se convierten a 1-based en Kratos.
        self.assertEqual(mp.GetSubModelPart("FixedFace").nodes, [2, 3, 4])
        self.assertEqual(mp.GetSubModelPart("LoadFace").nodes, [11, 21])

    def test_filters_out_of_range_indices(self):
        adapter = self._adapter()
        mp = _FakeModelPart(n_nodes=5)
        groups = {"A": [0, 1, 99, -3]}
        adapter._create_submodelparts_from_groups(mp, groups)
        sub = mp.GetSubModelPart("A")
        self.assertIn(1, sub.nodes)   # 0 -> 1 (1-based)
        self.assertIn(2, sub.nodes)   # 1 -> 2
        self.assertNotIn(100, sub.nodes)
        self.assertNotIn(-2, sub.nodes)


if __name__ == "__main__":
    unittest.main()
