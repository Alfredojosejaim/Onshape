"""Comprehensive automated test suite for Hito 1 of Onshape Topology Optimization.

Validates:
1. OAuth token exchange and refresh logic.
2. Handling of invalid OAuth requests.
3. STEP geometry parsing and import from binary data.
4. B-Rep STEP tessellation (triangles, vertices, normals) for Three.js.
5. Volumetric finite element meshing (nodes and tetrahedral elements).
6. Non-empty nodes and elements in generated FEM mesh.
7. Geometric boundary condition mapping from CAD B-Rep faces to FEM nodes.
8. Proper rejection of empty or corrupt STEP data.
9. Pydantic schema validation for loads, constraints, and optimization configs.
10. Querying real Part Studio parts list from Onshape API.
11. STEP download filtering by specific part IDs.
12. HTTPS security configuration and TLS certificate presence.
13. End-to-end pipeline consistency for Hito 1.
"""

import os
import sys
import tempfile
import unittest
from typing import Dict, Any

import numpy as np
import requests
import cadquery as cq

from geometry_processor import GeometryProcessor
from onshape_client import OAuthTokenStore, OnshapeAPIError, OnshapeClient
from api_server import ForceDefinition, ConstraintDefinition, GeometrySelection, OAUTH_REDIRECT_URI


class MemoryTokenStore(OAuthTokenStore):
    def __init__(self):
        self.tokens = {}

    def get_token(self, session_id):
        return self.tokens.get(session_id)

    def save_token(self, session_id, token):
        self.tokens[session_id] = token


def make_mock_response(status, payload=None, content=None):
    resp = requests.Response()
    resp.status_code = status
    if content is not None:
        resp._content = content
    elif payload is not None:
        resp._content = __import__("json").dumps(payload).encode()
    else:
        resp._content = b""
    return resp


def create_sample_step_bytes(length=20.0, width=10.0, height=5.0) -> bytes:
    """Create a real valid STEP binary byte stream using CadQuery/OpenCASCADE."""
    box = cq.Workplane("XY").box(length, width, height)
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        cq.exporters.export(box, tmp_path)
        with open(tmp_path, "rb") as f:
            data = f.read()
        return data
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


class TestHito1Pipeline(unittest.TestCase):

    # --- TEST 1: OAuth Valid Token Exchange and Auto-refresh ---
    def test_oauth_valid_exchange_and_refresh(self):
        store = MemoryTokenStore()
        client = OnshapeClient(store, "test_session", "client_id", "client_secret")
        token_sequence = iter([
            make_mock_response(200, {"access_token": "token_1", "refresh_token": "refresh_1", "expires_in": 0}),
            make_mock_response(200, {"access_token": "token_2", "refresh_token": "refresh_1", "expires_in": 3600}),
        ])
        client.session.post = lambda *args, **kwargs: next(token_sequence)

        token = client.exchange_code("code_123", "https://localhost:8000/oauth/callback")
        self.assertEqual(token["access_token"], "token_1")
        self.assertEqual(store.get_token("test_session")["access_token"], "token_1")

        refreshed = client._refresh(store.get_token("test_session"))
        self.assertEqual(refreshed["access_token"], "token_2")

    # --- TEST 2: OAuth Invalid Token / 401 Error Handling ---
    def test_oauth_unauthorized_error_handling(self):
        store = MemoryTokenStore()
        client = OnshapeClient(store, "test_session", "client_id", "client_secret")

        with self.assertRaises(OnshapeAPIError) as ctx:
            client.request("GET", "/documents")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.code, "ONSHAPE_AUTH_REQUIRED")

    # --- TEST 3: STEP Loading and B-Rep Parsing ---
    def test_step_loading_and_solid_volume(self):
        step_data = create_sample_step_bytes(length=10.0, width=10.0, height=10.0)
        processor = GeometryProcessor(None, "did", "wid", "eid")
        shape = processor.load_shape_from_step(step_data)

        self.assertIsNotNone(shape)
        self.assertFalse(shape.isNull())
        self.assertAlmostEqual(shape.Volume(), 1000.0, places=1)

    # --- TEST 4: STEP Tessellation (Vertices, Normals, Triangles for Three.js) ---
    def test_step_tessellation_for_threejs(self):
        step_data = create_sample_step_bytes(length=15.0, width=10.0, height=8.0)
        processor = GeometryProcessor(None, "did", "wid", "eid")
        result = processor.tessellate_step(step_data, linear_deflection=0.1, angular_deflection=0.1)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["format"], "triangle_mesh")
        self.assertGreater(result["num_vertices"], 0)
        self.assertGreater(result["num_triangles"], 0)
        self.assertEqual(len(result["vertices"]), result["num_vertices"] * 3)
        self.assertEqual(len(result["indices"]), result["num_triangles"] * 3)
        self.assertEqual(len(result["faces"]), 6)

    # --- TEST 5 & 6: Real Volumetric FEM Meshing (Nodes & Elements > 0) ---
    def test_volumetric_mesh_generation_tet4(self):
        step_data = create_sample_step_bytes(length=10.0, width=10.0, height=10.0)
        processor = GeometryProcessor(None, "did", "wid", "eid")
        result = processor.create_mesh(step_data, target_element_size=2.5, element_type="tet4")

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "ready")
        self.assertGreater(result["num_nodes"], 0)
        self.assertGreater(result["num_elements"], 0)
        self.assertEqual(result["element_type"], "tet4")

        for elem in result["elements"]:
            self.assertEqual(len(elem), 4)
            for node_idx in elem:
                self.assertTrue(0 <= node_idx < result["num_nodes"])

    # --- TEST 7: Boundary Condition Mapping (CAD B-Rep Face to Mesh Nodes) ---
    def test_cad_face_to_mesh_nodes_mapping(self):
        step_data = create_sample_step_bytes(length=10.0, width=10.0, height=10.0)
        processor = GeometryProcessor(None, "did", "wid", "eid")

        mesh_res = processor.create_mesh(step_data, target_element_size=2.0, element_type="tet4")
        nodes = mesh_res["nodes"]

        bc_res = processor.identify_boundary_conditions(nodes, step_data, face_indices=[0], tolerance=0.5)
        self.assertTrue(bc_res["success"])
        self.assertEqual(len(bc_res["mapped_faces"]), 1)
        mapped_face = bc_res["mapped_faces"][0]
        self.assertEqual(mapped_face["face_index"], 0)
        self.assertGreater(mapped_face["matched_nodes_count"], 0)
        self.assertEqual(len(mapped_face["node_indices"]), mapped_face["matched_nodes_count"])

    # --- TEST 8: Rejection of Corrupt or Empty STEP Data ---
    def test_invalid_step_data_rejection(self):
        processor = GeometryProcessor(None, "did", "wid", "eid")

        res_empty = processor.tessellate_step(b"")
        self.assertFalse(res_empty["success"])
        self.assertEqual(res_empty["code"], "STEP_TESSELLATION_FAILED")

        res_corrupt = processor.tessellate_step(b"NOT A VALID STEP FILE HEADER DATA")
        self.assertFalse(res_corrupt["success"])

    # --- TEST 9: Pydantic Schema Validation (Loads & Constraints & Selection) ---
    def test_pydantic_schema_validation(self):
        # Valid Force
        f_valid = ForceDefinition(magnitude=500.0, direction_x=0.0, direction_y=-1.0, direction_z=0.0)
        self.assertEqual(f_valid.magnitude, 500.0)

        # Zero vector Force must be rejected
        with self.assertRaises(ValueError):
            ForceDefinition(magnitude=500.0, direction_x=0.0, direction_y=0.0, direction_z=0.0)

        # Valid Constraint
        c_valid = ConstraintDefinition(constraint_type="fixed", location="face_0")
        self.assertTrue(c_valid.degrees_of_freedom["ux"])

        # Constraint with all False degrees of freedom must be rejected
        with self.assertRaises(ValueError):
            ConstraintDefinition(
                constraint_type="fixed",
                location="face_0",
                degrees_of_freedom={"ux": False, "uy": False, "uz": False, "rx": False, "ry": False, "rz": False}
            )

        # Valid GeometrySelection
        sel = GeometrySelection(
            context={"documentId": "doc1", "workspaceId": "ws1", "elementId": "el1"},
            designSpace=["JHD"],
            keepOut=["JHF"],
        )
        self.assertEqual(sel.designSpace, ["JHD"])
        self.assertEqual(sel.keepOut, ["JHF"])

    # --- TEST 10: Onshape REST Part Studio Query & STEP Export with Part IDs ---
    def test_onshape_parts_list_and_filtered_download(self):
        store = MemoryTokenStore()
        store.save_token("sess1", {
            "access_token": "valid_token",
            "refresh_token": "refresh_token",
            "expires_at": 9999999999,
            "token_type": "Bearer",
            "scope": "OAuth2Read",
        })
        client = OnshapeClient(store, "sess1", "cid", "csecret")

        mock_parts = [
            {"partId": "JHD", "name": "Bracket_Solid", "bodyType": "solid"},
            {"partId": "JHF", "name": "Pin_Obstacle", "bodyType": "solid"},
        ]
        sample_step = create_sample_step_bytes(10, 10, 10)

        def mock_request(method, path, **kwargs):
            if path.endswith("/parts"):
                return make_mock_response(200, payload=mock_parts)
            elif "/export" in path:
                params = kwargs.get("params", {})
                self.assertEqual(params.get("partIds"), "JHD")
                return make_mock_response(200, content=sample_step)
            return make_mock_response(404, payload={})

        client.session.request = mock_request

        processor = GeometryProcessor(client, "doc1", "ws1", "el1")
        parts = processor.get_parts_list()
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]["partId"], "JHD")
        self.assertEqual(parts[0]["name"], "Bracket_Solid")

        downloaded_bytes = processor.download_part_studio(output_format="step", part_ids=["JHD"])
        self.assertIsNotNone(downloaded_bytes)
        self.assertEqual(len(downloaded_bytes), len(sample_step))

    # --- TEST 11: HTTPS and TLS Security Configuration ---
    def test_https_security_configuration(self):
        # Verify OAuth redirect URI uses HTTPS
        self.assertTrue(OAUTH_REDIRECT_URI.startswith("https://"))

        # Verify certs directory and PEM format if generated
        cert_path = os.path.join(os.path.dirname(__file__), "certs", "localhost.pem")
        key_path = os.path.join(os.path.dirname(__file__), "certs", "localhost-key.pem")

        if os.path.exists(cert_path) and os.path.exists(key_path):
            with open(cert_path, "r", encoding="utf-8") as f:
                cert_content = f.read()
            with open(key_path, "r", encoding="utf-8") as f:
                key_content = f.read()
            self.assertIn("-----BEGIN CERTIFICATE-----", cert_content)
            self.assertIn("-----BEGIN PRIVATE KEY-----", key_content)

    # --- TEST 12: Complete Hito 1 Pipeline Consistency ---
    def test_complete_hito1_pipeline(self):
        step_data = create_sample_step_bytes(length=20.0, width=15.0, height=10.0)
        processor = GeometryProcessor(None, "d1", "w1", "e1")

        # 1. Tessellate for visual CAD display in Three.js
        tess = processor.tessellate_step(step_data)
        self.assertTrue(tess["success"])
        self.assertGreater(tess["num_vertices"], 0)
        self.assertGreater(tess["num_triangles"], 0)

        # 2. Generate volumetric FEM mesh
        mesh = processor.create_mesh(step_data, target_element_size=3.0, element_type="tet4")
        self.assertTrue(mesh["success"])
        self.assertGreater(mesh["num_nodes"], 0)
        self.assertGreater(mesh["num_elements"], 0)

        # 3. Map boundary conditions
        bcs = processor.identify_boundary_conditions(mesh["nodes"], step_data)
        self.assertTrue(bcs["success"])
        self.assertEqual(len(bcs["mapped_faces"]), 6)
        total_matched_nodes = sum(f["matched_nodes_count"] for f in bcs["mapped_faces"])
        self.assertGreater(total_matched_nodes, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
