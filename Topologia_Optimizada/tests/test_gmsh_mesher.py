"""Test del malla generadora definitiva — GmshTet4Mesher.

Verifica el flujo de mallado definitivo (Gmsh -> Tet4) sobre geometría STEP real:

    STEP (cono.step) -> Gmsh (OpenCASCADE) -> Malla Tet4 conformante

Criterios:
  * El malla NO es provisional (is_provisional = False).
  * Los elementos son Tet4 válidos (cada elemento refiere 4 nodos existentes).
  * El pipeline funciona tanto desde archivo STEP como desde cq.Shape.
  * CADService.generate_mesh utiliza la malla Gmsh.

Se usa el STEP real del proyecto (cono.step). No se genera geometría artificial.
"""

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REAL_STEP_FILE = "cono.step"

try:
    import gmsh  # noqa: F401
    GMSH_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = False


def _valid_tet4_mesh(nodes, elements):
    """True si nodes y elements forman una malla Tet4 bien formada."""
    if not nodes or not elements:
        return False
    n_nodes = len(nodes)
    for elem in elements:
        if len(elem) != 4:
            return False
        for idx in elem:
            if not (0 <= idx < n_nodes):
                return False
    return True


@unittest.skipUnless(GMSH_AVAILABLE, "gmsh no está instalado")
class TestGmshTet4MesherFromStep(unittest.TestCase):
    """Verifica la generación de malla definitiva desde un archivo STEP real."""

    def test_generate_mesh_from_real_step(self):
        """El STEP real produce una malla Tet4 real, no provisional."""
        from core.meshing import GmshTet4Mesher

        mesher = GmshTet4Mesher()
        result = mesher.generate_mesh_from_step(REAL_STEP_FILE, target_element_size=5.0)

        self.assertEqual(result.element_type, "tet4")
        self.assertFalse(result.is_provisional)
        self.assertGreater(result.num_nodes, 0)
        self.assertGreater(result.num_elements, 0)
        self.assertEqual(result.num_nodes, len(result.nodes))
        self.assertEqual(result.num_elements, len(result.elements))

        # Los nodos son coordenadas 3D
        self.assertEqual(len(result.nodes[0]), 3)

    def test_elements_reference_valid_nodes(self):
        """Todos los elementos Tet4 referencian nodos existentes."""
        from core.meshing import GmshTet4Mesher

        mesher = GmshTet4Mesher()
        result = mesher.generate_mesh_from_step(REAL_STEP_FILE, target_element_size=5.0)

        self.assertTrue(_valid_tet4_mesh(result.nodes, result.elements))

    def test_element_type_validation(self):
        """Solo tet4 es compatible con el generador Gmsh."""
        from core.meshing import GmshTet4Mesher

        mesher = GmshTet4Mesher()
        with self.assertRaises(ValueError):
            mesher.generate_mesh_from_step(REAL_STEP_FILE, element_type="hex8")

    def test_missing_step_file_raises(self):
        """Un archivo STEP inexistente lanza FileNotFoundError."""
        from core.meshing import GmshTet4Mesher

        mesher = GmshTet4Mesher()
        with self.assertRaises(FileNotFoundError):
            mesher.generate_mesh_from_step("no_existe.step")


@unittest.skipUnless(GMSH_AVAILABLE, "gmsh no está instalado")
class TestGmshTet4MesherFromShape(unittest.TestCase):
    """Verifica la generación de malla definitiva desde un cq.Shape."""

    def test_generate_mesh_from_shape(self):
        """Un Shape CAD real también puede mallarse vía Gmsh."""
        from adapters.cad.step_adapter import StepAdapter
        from core.meshing import GmshTet4Mesher

        adapter = StepAdapter()
        cad_model = adapter.load_from_file(REAL_STEP_FILE, model_name="Cono")
        shape = adapter.get_shape(cad_model.id)
        self.assertIsNotNone(shape)
        self.assertFalse(shape.isNull())

        mesher = GmshTet4Mesher()
        result = mesher.generate_mesh(shape, target_element_size=5.0)

        self.assertEqual(result.element_type, "tet4")
        self.assertFalse(result.is_provisional)
        self.assertGreater(result.num_nodes, 0)
        self.assertGreater(result.num_elements, 0)
        self.assertTrue(_valid_tet4_mesh(result.nodes, result.elements))


class TestCadServiceUsesGmshMesher(unittest.TestCase):
    """CADService.generate_mesh debe preferir la malla Gmsh definitiva."""

    def setUp(self):
        if not os.path.exists(REAL_STEP_FILE):
            self.skipTest(f"No existe {REAL_STEP_FILE}")
        from services.cad_service import CADService

        self.service = CADService()
        self.cad_model = self.service.import_step_from_file(REAL_STEP_FILE, model_name="Cono")

    def test_service_mesh_is_not_provisional(self):
        """La malla generada por el servicio usa Gmsh (no provisional)."""
        result = self.service.generate_mesh(self.cad_model.id, target_element_size=5.0)

        self.assertTrue(result.get("success"))
        self.assertIs(result.get("is_provisional"), False)
        meta = result.get("metadata", {})
        self.assertEqual(meta.get("mesher"), "GmshTet4Mesher")
        self.assertGreater(result.get("num_nodes", 0), 0)
        self.assertGreater(result.get("num_elements", 0), 0)
        self.assertTrue(
            _valid_tet4_mesh(result.get("nodes", []), result.get("elements", []))
        )


if __name__ == "__main__":
    unittest.main()
