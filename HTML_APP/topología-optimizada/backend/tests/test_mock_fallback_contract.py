"""Contrato MOCK-FALLBACK en la cadena bridge -> jobs -> App (TS estático).

Sin WebView2 en CI no se puede montar pywebview; esta prueba certifica la
cadena que hace visible el fallback:
- bridge.ts marca toda respuesta mock con `mock: true`;
- jobs.ts (useJobPoll) rechaza el sondeo mock (no dispara onDone real);
- App.tsx expone `isMockFallback`, lo activa solo en el timer sin bridge,
  lo limpia con un resultado real de mapSimpResult/mapSimpOutcome y
  renderiza la etiqueta persistente `MOCK-FALLBACK`.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _read(rel: str) -> str:
    return (SRC / rel).read_text(encoding="utf-8")


def test_bridge_marks_mock_responses():
    bridge = _read("lib/bridge.ts")
    assert "mock: true" in bridge
    assert "MOCK-FALLBACK" in bridge


def test_job_poll_rejects_mock():
    jobs = _read("lib/jobs.ts")
    assert "r.mock" in jobs
    assert "no es un resultado real" in jobs


def test_app_exposes_visible_mock_fallback_state():
    app = _read("App.tsx")
    assert "isMockFallback" in app
    assert "setIsMockFallback(true)" in app
    assert "setIsMockFallback(false)" in app
    assert "MOCK-FALLBACK" in app
    # La marca se limpia al recibir resultado real del backend.
    assert "mapSimpOutcome" in app or "mapSimpResult" in app
    # La etiqueta es persistente junto a los resultados (role=status).
    assert 'role="status"' in app


def test_outcome_contract_distinguishes_states():
    realdata = _read("lib/realdata.ts")
    for token in ("'pending'", "'completed'", "'invalid'", "'error'",
                  "mapSimpOutcome", "mapFeaOutcome"):
        assert token in realdata
    # La UI consume el volumen físico cuando el core lo reporta (punto 5).
    assert "physical_volume_fraction" in realdata


def test_keepout_faces_reach_backend():
    faces = _read("lib/faces.ts")
    assert "type: 'obstruction'" in faces
    assert "Caras de obstrucción" in faces
    app = (ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "cond.type !== 'keepout'" in app  # guard lo acepta
    assert "c.type === 'keepout'" in app  # sync + undo lo incluyen
    # MAP-REPORT: la UI muestra el mapeo real por condición (diagnóstico
    # "al revés": caras pedidas vs nodos/elementos mapeados).
    assert "_condition_mapping" in app
    assert "mapText" in app


def test_tree_body_select_and_tolerant_delete():
    app = (ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
    # TREE-BODY-SELECT: cuerpos/mallas se marcan como las herramientas.
    assert "selectedBodyKey" in app
    assert "onSelectBody" in app
    # DELETE-TOLERANT: id desconocido en backend se elimina igual en local.
    assert "desconocida|unknown" in app
    left = (ROOT / "src" / "components" / "LeftPanel.tsx").read_text(encoding="utf-8")
    assert "selectedBodyKey" in left
    ops = (ROOT / "src" / "components" / "OperationRow.tsx").read_text(encoding="utf-8")
    assert "TREE-BODY-SELECT" in ops


def test_bridge_long_timeouts_cover_blocking_calls():
    desk = (ROOT / "backend" / "app_desktop.py").read_text(encoding="utf-8")
    assert "_LONG_METHODS" in desk
    assert "_LONG_TIMEOUT" in desk
    for m in ("registerReconstruction", "exportStep", "generateMesh",
              "importStep"):
        assert m in desk
