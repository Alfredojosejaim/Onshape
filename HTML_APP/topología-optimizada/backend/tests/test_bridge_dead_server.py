"""DEAD-SERVER: el puente distingue proceso muerto de proceso ocupado.

Regresión del "WinError 10061" opaco: con el servidor monohilo, un handler
bloqueante (register/export) puede rechazar polls aunque el proceso siga
vivo; y si el proceso murió (crash nativo/OOM), el poll debe decirlo con el
exit code en vez del crudo URLError. Sin importar el Api pesado.
"""
import sys

import pytest

from app_desktop import _make_bridge


def test_refused_with_dead_process_reports_exit_code():
    b = _make_bridge("http://127.0.0.1:9/", is_alive=lambda: -1073741819)
    r = b._call("pollJob", "x")
    assert r["ok"] is False
    assert "el proceso backend terminó" in r["error"]
    assert "-1073741819" in r["error"]
    assert "server_stdout.log" in r["error"]


def test_refused_with_live_process_asks_for_retry():
    b = _make_bridge("http://127.0.0.1:9/", is_alive=lambda: None)
    r = b._call("pollJob", "x")
    assert r["ok"] is False
    assert "backend ocupado" in r["error"]
    assert "proceso vivo" in r["error"]


def test_refused_without_probe_keeps_generic_fallback():
    b = _make_bridge("http://127.0.0.1:9/")
    r = b._call("pollJob", "x")
    assert r["ok"] is False
    # Sin sonda no se puede afirmar muerte: mensaje de transporte genérico,
    # que jobs.ts reintenta (no mata el sondeo).
    assert "backend" in r["error"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
