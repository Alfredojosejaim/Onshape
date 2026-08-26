"""Test real de importación STEP standalone.

Verifica el flujo: STEP → Adapter → CADModel
Sin dependencias de Onshape, OAuth, o APIs externas.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import cadquery as cq

from adapters.cad.step_adapter import StepAdapter
from services.cad_service import CADService
from core.models import CADModel, SourceType


class TestStandaloneStepImport(unittest.TestCase):
    """Test de importación STEP real standalone."""

    def setUp(self):
        self.step_adapter = StepAdapter()
        self.cad_service = CADService()

    def test_step_adapter_creates_cad_model(self):
        """Verifica que StepAdapter crea un CADModel desde STEP bytes."""
        # Crear un STEP simple usando CadQuery
        box = cq.Workplane("XY").box(10, 10, 10)
        
        # Exportar a STEP temporal
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cq.exporters.export(box, tmp_path)
            
            # Leer el STEP
            with open(tmp_path, "rb") as f:
                step_data = f.read()
            
            # Importar usando StepAdapter
            cad_model = self.step_adapter.load_from_bytes(
                step_data,
                model_name="Test Box",
                metadata={"source": "test"}
            )
            
            # Verificar que se creó un CADModel válido
            self.assertIsInstance(cad_model, CADModel)
            self.assertEqual(cad_model.name, "Test Box")
            self.assertEqual(cad_model.source.source_type, SourceType.STEP)
            self.assertGreater(cad_model.total_volume, 0)
            self.assertGreater(cad_model.total_area, 0)
            self.assertIsNotNone(cad_model.bbox)
            self.assertGreater(len(cad_model.faces), 0)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_cad_service_import_step_from_bytes(self):
        """Verifica que CADService importa STEP desde bytes."""
        # Crear un STEP simple
        box = cq.Workplane("XY").box(5, 5, 5)
        
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cq.exporters.export(box, tmp_path)
            
            with open(tmp_path, "rb") as f:
                step_data = f.read()
            
            # Importar usando CADService
            cad_model = self.cad_service.import_step_from_bytes(
                step_data,
                model_name="CAD Service Test",
                metadata={"source": "standalone_test"}
            )
            
            # Verificar resultado
            self.assertIsInstance(cad_model, CADModel)
            self.assertEqual(cad_model.name, "CAD Service Test")
            self.assertIsNotNone(cad_model.id)
            self.assertGreater(cad_model.total_volume, 0)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_step_adapter_handles_invalid_data(self):
        """Verifica manejo de datos STEP inválidos."""
        with self.assertRaises(ValueError):
            self.step_adapter.load_from_bytes(b"", model_name="Empty Test")
        
        with self.assertRaises(ValueError):
            self.step_adapter.load_from_bytes(b"invalid step data", model_name="Invalid Test")

    def test_step_adapter_from_file(self):
        """Verifica importación desde archivo STEP."""
        # Crear STEP temporal
        box = cq.Workplane("XY").box(8, 8, 8)
        
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cq.exporters.export(box, tmp_path)
            
            # Importar desde archivo
            cad_model = self.step_adapter.load_from_file(tmp_path)
            
            # Verificar
            self.assertIsInstance(cad_model, CADModel)
            self.assertGreater(cad_model.total_volume, 0)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_cad_service_get_model(self):
        """Verifica que CADService puede recuperar modelos cacheados."""
        # Crear y cachear un modelo
        box = cq.Workplane("XY").box(3, 3, 3)
        
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cq.exporters.export(box, tmp_path)
            
            with open(tmp_path, "rb") as f:
                step_data = f.read()
            
            cad_model = self.cad_service.import_step_from_bytes(step_data, model_name="Cache Test")
            
            # Recuperar desde cache
            retrieved_model = self.cad_service.get_model(cad_model.id)
            
            self.assertIsNotNone(retrieved_model)
            self.assertEqual(retrieved_model.id, cad_model.id)
            self.assertEqual(retrieved_model.name, "Cache Test")
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()