"""Test de independencia del Core.

Verifica que el Core puede utilizarse sin:
- Onshape
- OAuth
- credenciales externas
- red
- aplicaciones CAD externas

El test debe fallar si el Core vuelve a depender de componentes de Onshape.
"""

import sys
import unittest
import importlib
import inspect


class TestCoreIndependence(unittest.TestCase):
    """Test que verifica independencia del Core de Onshape y APIs externas."""

    def test_core_no_onshape_imports(self):
        """Verifica que los módulos core no importan onshape_client."""
        core_modules = [
            "core.models",
            "core.geometry", 
            "core.meshing",
            "core.boundary",
            "core.materials",
            "core.study",
            "core.solver_interface",
        ]
        
        for module_name in core_modules:
            try:
                module = importlib.import_module(module_name)
                source = inspect.getsource(module)
                
                # Verificar que no hay imports de onshape_client
                self.assertNotIn("onshape_client", source,
                    f"{module_name} contiene import de onshape_client")
                
                # Verificar que no hay imports de connectors.onshape
                self.assertNotIn("connectors.onshape", source,
                    f"{module_name} contiene import de connectors.onshape")
                
                # Verificar que no hay imports de OAuth
                self.assertNotIn("OAuth", source,
                    f"{module_name} contiene import de OAuth")
                
            except ImportError as e:
                self.fail(f"No se pudo importar {module_name}: {e}")

    def test_cad_service_no_onshape_imports(self):
        """Verifica que CADService no depende de Onshape."""
        from services import cad_service
        source = inspect.getsource(cad_service)
        
        self.assertNotIn("onshape_client", source,
            "CADService contiene import de onshape_client")
        self.assertNotIn("connectors.onshape", source,
            "CADService contiene import de connectors.onshape")
        self.assertNotIn("OAuth", source,
            "CADService contiene import de OAuth")

    def test_step_adapter_no_onshape_imports(self):
        """Verifica que StepAdapter no depende de Onshape."""
        from adapters.cad import step_adapter
        source = inspect.getsource(step_adapter)
        
        self.assertNotIn("onshape_client", source,
            "StepAdapter contiene import de onshape_client")
        self.assertNotIn("connectors.onshape", source,
            "StepAdapter contiene import de connectors.onshape")
        self.assertNotIn("OAuth", source,
            "StepAdapter contiene import de OAuth")

    def test_cadmodel_agnostic(self):
        """Verifica que CADModel es agnóstico al formato CAD."""
        from core.models import CADModel, SourceType
        
        # Verificar que SourceType tiene STEP pero no depende de Onshape
        self.assertIn(SourceType.STEP, SourceType)
        self.assertIn(SourceType.SYNTHETIC, SourceType)
        
        # Verificar que CADModel puede crearse sin contexto Onshape
        cad_model = CADModel(
            id="test_id",
            name="Test Model",
            units="mm"
        )
        
        self.assertEqual(cad_model.id, "test_id")
        self.assertEqual(cad_model.name, "Test Model")
        self.assertIsNone(cad_model.source)  # No requiere fuente externa

    def test_geometry_engine_standalone(self):
        """Verifica que GeometryEngine funciona sin conexiones externas."""
        from core.geometry import GeometryEngine
        import cadquery as cq
        
        # Crear geometría local (val() convierte Workplane a Shape)
        box = cq.Workplane("XY").box(10, 10, 10).val()
        
        # Verificar que GeometryEngine puede procesarla
        bbox = GeometryEngine.calculate_bounding_box(box)
        self.assertIsNotNone(bbox)
        self.assertGreater(bbox.dx, 0)
        
        faces = GeometryEngine.extract_faces_metadata(box)
        self.assertGreater(len(faces), 0)

    def test_mesher_standalone(self):
        """Verifica que el mesher funciona sin conexiones externas."""
        from core.meshing import ProvisionalTet4Mesher
        import cadquery as cq
        
        # Crear geometría local
        box = cq.Workplane("XY").box(5, 5, 5).val()
        
        # Verificar que el mesher puede generar malla
        mesher = ProvisionalTet4Mesher()
        mesh_result = mesher.generate_mesh(box, target_element_size=2.0)
        
        self.assertIsNotNone(mesh_result)
        self.assertGreater(mesh_result.num_nodes, 0)
        self.assertGreater(mesh_result.num_elements, 0)

    def test_boundary_mapper_standalone(self):
        """Verifica que BoundaryConditionMapper funciona sin conexiones externas."""
        from core.boundary import BoundaryConditionMapper
        import cadquery as cq
        import numpy as np
        
        # Crear geometría local
        box = cq.Workplane("XY").box(3, 3, 3).val()
        
        # Crear nodos simples
        nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        
        # Verificar que el mapper puede procesar
        mapped = BoundaryConditionMapper.map_faces_to_nodes(box, nodes)
        
        self.assertIsNotNone(mapped)
        self.assertGreater(len(mapped), 0)

    def test_no_oauth_requirements(self):
        """Verifica que no hay variables de entorno OAuth obligatorias."""
        # Leer archivos de configuración
        try:
            with open(".env.example", "r") as f:
                env_content = f.read()
            
            self.assertNotIn("ONSHAPE_OAUTH", env_content,
                ".env.example contiene variables ONSHAPE_OAUTH obligatorias")
            self.assertNotIn("OAUTH_CLIENT", env_content,
                ".env.example contiene variables OAUTH_CLIENT obligatorias")
        except FileNotFoundError:
            pass  # Si no existe .env.example, no hay problema

    def test_api_server_standalone(self):
        """Verifica que api_server no tiene dependencias Onshape obligatorias."""
        # Leer el archivo api_server.py directamente
        try:
            with open("api_server.py", "r") as f:
                api_source = f.read()
            
            # Verificar que no hay imports de onshape_client
            self.assertNotIn("onshape_client", api_source,
                "api_server contiene import de onshape_client")
            
            # Verificar que no hay OAuth
            self.assertNotIn("OAuthTokenStore", api_source,
                "api_server contiene OAuthTokenStore")
            self.assertNotIn("oauth_configured", api_source,
                "api_server contiene oauth_configured")
            
        except FileNotFoundError:
            self.fail("No se encontró api_server.py")


if __name__ == "__main__":
    unittest.main()