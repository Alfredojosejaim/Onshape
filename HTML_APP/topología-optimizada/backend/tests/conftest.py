"""Fixtures comunes de la suite del backend.

TMP-PATH (reversible): redirige ``backend/api.py`` (vía ``TOPOOPT_UPLOADS``)
a un ``tmp_path`` por test, para que ninguna corrida deje artefactos en el
árbol (antes: ``backend/uploads/computed_*.step`` sin trackear, con el mismo
nombre que fixtures versionados). Para volver atrás: borrar este archivo.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _uploads_en_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("TOPOOPT_UPLOADS", str(tmp_path))
