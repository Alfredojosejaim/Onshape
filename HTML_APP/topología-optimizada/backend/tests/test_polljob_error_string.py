"""JOB-ERR-STR: el error de un job fallido viaja como string a la UI.

Antes `pollJob` devolvía el dict de `_err()` y `src/lib/jobs.ts` (que solo
muestra el detalle si es string) caía al genérico "El job terminó con error",
ocultando la causa real.
"""
import time

from api import Api


def test_polljob_exposes_string_error_for_failed_job():
    api = Api()

    def _boom():
        raise RuntimeError("fallo simulado del solver")

    jid = api._submit("test", _boom)
    poll = None
    for _ in range(200):
        poll = api.pollJob(jid)
        if poll.get("state") in ("done", "error", "failed"):
            break
        time.sleep(0.05)
    assert poll is not None
    assert poll["state"] == "error"
    err = poll["error"]
    assert isinstance(err, str), type(err)
    assert "RuntimeError" in err and "fallo simulado" in err
