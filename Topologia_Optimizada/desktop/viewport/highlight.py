"""HighlightRenderer - resaltado multi-cara por celda (prompts.md §3).

El highlight NO puede vivir en la property del actor (eso limita a una sola
cara resaltada porque es global al actor). Se colorean celdas individuales
via vtkUnsignedCharArray como CellData scalars.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence


class HighlightRenderer:
    """Colorea celdas individuales de un vtkPolyData segun seleccion/hover."""

    SELECTED_RGB = (255, 165, 0)   # naranja Onshape-like
    HOVER_RGB = (120, 190, 255)    # azul claro prehover

    def __init__(self, polydata, base_colors: Optional[Dict[int, tuple]] = None,
                 default_color: tuple = (139, 158, 189)) -> None:
        from vtkmodules.vtkCommonCore import vtkUnsignedCharArray

        self.polydata = polydata
        n = int(polydata.GetNumberOfCells())
        self.base_colors: Dict[int, tuple] = (
            dict(base_colors) if base_colors is not None
            else {cid: tuple(default_color) for cid in range(n)}
        )
        self._default = tuple(default_color)
        self.colors = vtkUnsignedCharArray()
        self.colors.SetNumberOfComponents(3)
        self.colors.SetName("Colors")
        self.colors.SetNumberOfTuples(n)
        for cid in range(n):
            rgb = self.base_colors.get(cid, self._default)
            self.colors.SetTuple3(cid, int(rgb[0]), int(rgb[1]), int(rgb[2]))
        self.polydata.GetCellData().SetScalars(self.colors)
        # Asegurar que el mapper use los scalars de celda.
        try:
            self.polydata.Modified()
        except Exception:
            pass

    def update(self, selected_cell_ids: set[int],
               hovered_cell_id: Optional[int] = None) -> None:
        n = int(self.polydata.GetNumberOfCells())
        if self.colors.GetNumberOfTuples() != n:
            self.colors.SetNumberOfTuples(n)
        sel = set(int(c) for c in (selected_cell_ids or set()))
        for cid in range(n):
            if cid in sel:
                rgb = self.SELECTED_RGB
            elif hovered_cell_id is not None and cid == int(hovered_cell_id):
                rgb = self.HOVER_RGB
            else:
                rgb = self.base_colors.get(cid, self._default)
            self.colors.SetTuple3(cid, int(rgb[0]), int(rgb[1]), int(rgb[2]))
        try:
            self.polydata.Modified()
        except Exception:
            pass

    def set_base_colors_from_faces(self, cell_to_face: Sequence[int],
                                   palette: Optional[Dict[int, tuple]] = None) -> None:
        """Recolorea base por cara (opcional, para distinguir caras)."""
        import colorsys

        cell_to_face = list(cell_to_face)
        faces = sorted({int(f) for f in cell_to_face if int(f) >= 0})
        for i, f in enumerate(faces):
            if palette and f in palette:
                rgb = palette[f]
            else:
                h = (i * 0.37) % 1.0
                r, g, b = colorsys.hsv_to_rgb(h, 0.25, 0.9)
                rgb = (int(r * 255), int(g * 255), int(b * 255))
            for cid, cf in enumerate(cell_to_face):
                if int(cf) == f:
                    self.base_colors[cid] = rgb
        self.update(set())
