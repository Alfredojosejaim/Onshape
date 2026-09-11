"""HighlightRenderer - resaltado multi-cara por celda (prompts.md §3).

El highlight NO puede vivir en la property del actor (eso limita a una sola
cara resaltada porque es global al actor). Se colorean celdas individuales
via array RGB como CellData scalars.

Version vectorizada (prompt nuevo §1): el loop Python por celda
(``SetTuple3`` en ``range(n)``) escala mal en STEPs con decenas de miles de
triangulos — cada click recalculaba el array completo en Python puro,
justo cuando multi-seleccion mas caras = mas celdas. Ahora los colores base
viven en un ``(n, 3) uint8`` precomputado y cada ``update()`` es un copy +
asignacion indexada numpy + un unico ``numpy_to_vtk``.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np


class HighlightRenderer:
    """Colorea celdas individuales de un vtkPolyData segun seleccion/hover."""

    SELECTED_RGB = (255, 165, 0)   # naranja Onshape-like
    HOVER_RGB = (120, 190, 255)    # azul claro prehover

    def __init__(self, polydata, base_colors: Optional[Dict[int, tuple]] = None,
                 default_color: tuple = (139, 158, 189)) -> None:
        self.polydata = polydata
        n = int(polydata.GetNumberOfCells())
        self._default = tuple(int(c) for c in default_color)
        # Dict legado (compat) + array numpy precomputado (via rapida).
        self.base_colors: Dict[int, tuple] = (
            {int(k): tuple(int(c) for c in v) for k, v in base_colors.items()}
            if base_colors is not None
            else {cid: self._default for cid in range(n)}
        )
        self.base_colors_np = np.empty((n, 3), dtype=np.uint8)
        for cid in range(n):
            self.base_colors_np[cid] = self.base_colors.get(cid, self._default)
        self._push_colors(self.base_colors_np)

    # ------------------------------------------------------------------ #
    def update(self, selected_cell_ids: set[int],
               hovered_cell_id: Optional[int] = None) -> None:
        """Recolorea: full-copy del base + slices indexados (O(n) en C)."""
        n = int(self.polydata.GetNumberOfCells())
        if self.base_colors_np.shape[0] != n:
            self._rebuild_base(n)
        rgb = self.base_colors_np.copy()
        if selected_cell_ids:
            idx = np.fromiter(
                (int(c) for c in selected_cell_ids), dtype=np.int64,
                count=len(selected_cell_ids),
            )
            idx = idx[(idx >= 0) & (idx < n)]  # ids rancios no tumban el frame
            rgb[idx] = self.SELECTED_RGB
        if hovered_cell_id is not None:
            h = int(hovered_cell_id)
            if 0 <= h < n:
                rgb[h] = self.HOVER_RGB
        self._push_colors(rgb)

    def set_base_colors_from_faces(self, cell_to_face: Sequence[int],
                                   palette: Optional[Dict[int, tuple]] = None) -> None:
        """Recolorea base por cara (opcional, para distinguir caras)."""
        import colorsys

        cell_to_face = np.asarray(list(cell_to_face), dtype=np.int64)
        faces = sorted({int(f) for f in cell_to_face if int(f) >= 0})
        for i, f in enumerate(faces):
            if palette and f in palette:
                rgb = tuple(int(c) for c in palette[f])
            else:
                h = (i * 0.37) % 1.0
                r, g, b = colorsys.hsv_to_rgb(h, 0.25, 0.9)
                rgb = (int(r * 255), int(g * 255), int(b * 255))
            self.base_colors_np[cell_to_face == f] = rgb
            for cid in np.nonzero(cell_to_face == f)[0]:
                self.base_colors[int(cid)] = rgb
        self.update(set())

    # ------------------------------------------------------------------ #
    def _push_colors(self, rgb: np.ndarray) -> None:
        from vtkmodules.util.numpy_support import numpy_to_vtk

        arr = numpy_to_vtk(np.ascontiguousarray(rgb, dtype=np.uint8), deep=True)
        arr.SetName("Colors")
        self.polydata.GetCellData().SetScalars(arr)
        self.colors = arr  # ref viva al array en uso (compat con version loop)
        try:
            self.polydata.Modified()
        except Exception:
            pass

    def _rebuild_base(self, n: int) -> None:
        self.base_colors_np = np.empty((n, 3), dtype=np.uint8)
        for cid in range(n):
            self.base_colors_np[cid] = self.base_colors.get(cid, self._default)
