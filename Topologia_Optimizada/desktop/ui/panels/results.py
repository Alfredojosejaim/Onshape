"""ResultsPanel - reports mesh metrics and topology optimization results."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QTextEdit,
)


class ResultsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        title = QLabel("Resultados")
        title.setStyleSheet("font-weight: 600; color: #f2f2f3;")
        root.addWidget(title)

        grp = QGroupBox("Malla")
        form = QFormLayout(grp)
        self._mesh_n = QLabel("—")
        self._mesh_e = QLabel("—")
        self._mesh_t = QLabel("—")
        form.addRow("Nodos", self._mesh_n)
        form.addRow("Elementos", self._mesh_e)
        form.addRow("Tipo", self._mesh_t)
        root.addWidget(grp)

        res = QGroupBox("Optimización")
        rform = QFormLayout(res)
        self._status = QLabel("—")
        self._iter = QLabel("—")
        self._vol = QLabel("—")
        self._compliance = QLabel("—")
        self._conv = QLabel("—")
        rform.addRow("Estado", self._status)
        rform.addRow("Iteraciones", self._iter)
        rform.addRow("Volumen final", self._vol)
        rform.addRow("Compliance", self._compliance)
        rform.addRow("Convergencia", self._conv)
        root.addWidget(res)

        log = QGroupBox("Historial de convergencia")
        lform = QVBoxLayout(log)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        lform.addWidget(self._log)
        root.addWidget(log, 1)

    def set_mesh(self, num_nodes: int, num_elements: int, element_type: str, provisional: bool) -> None:
        self._mesh_n.setText(f"{num_nodes:,}")
        self._mesh_e.setText(f"{num_elements:,}")
        t = element_type.upper()
        if provisional:
            t += " (provisional)"
        self._mesh_t.setText(t)

    def set_result(self, result: dict, material_name: str | None = None) -> None:
        if not result or not result.get("success"):
            self._status.setText("Sin resultado")
            return
        self._status.setText(("Convergido" if result.get("converged") else "Máx. iteraciones") + " · " + (material_name or ""))
        self._iter.setText(str(result.get("iterations", "—")))
        vol = result.get("final_volume_fraction")
        self._vol.setText(f"{vol:.2%}" if isinstance(vol, float) else "—")
        comp = result.get("final_compliance")
        self._compliance.setText(f"{comp:.6e}" if isinstance(comp, float) else "—")
        delta = result.get("max_density_change")
        self._conv.setText(f"Δx = {delta:.4f}" if isinstance(delta, float) else "—")

    def append_history(self, iteration: int, vol: float, compliance: float) -> None:
        self._log.append(f"[iter {iteration:>3}]  V={vol:6.2%}   c={compliance:.4e}")

    def clear_history(self) -> None:
        self._log.clear()

    def reset_all(self) -> None:
        self._mesh_n.setText("—")
        self._mesh_e.setText("—")
        self._mesh_t.setText("—")
        self._status.setText("—")
        self._iter.setText("—")
        self._vol.setText("—")
        self._compliance.setText("—")
        self._conv.setText("—")
        self._log.clear()
