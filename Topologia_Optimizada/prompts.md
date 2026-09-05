Lo único que queda pendiente es el punto 1 (real): cambiar el except Exception: pass de _finish_rubber_band() por logging explícito, mismo criterio que ya aplicaron en la tessellation:

Python:
except Exception:
    logger.exception("rubber-band selection failed")

Con eso, el bloque de picking + multi-selección + rubber-band queda cerrado por completo, alineado con el comportamiento real de Onshape en los tres frentes: click/shift/ctrl puntual, precisión de tangentes, y selección por rectángulo con oclusión pasante.