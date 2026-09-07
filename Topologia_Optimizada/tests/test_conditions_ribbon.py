"""Ribbon: el grupo Condiciones existe como dropdown y dispara handlers."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.ui.components.workspace import WorkspaceBuilder
from desktop.ui.components.widgets import RibbonTool


class _Props:
    class _Size:
        def value(self):
            return 2.0

    _element_size = _Size()


class _Owner:
    def __init__(self):
        self.condition_ops = []
        self.properties = _Props()

    def _on_import(self):
        pass

    def _on_generate_mesh(self, *a):
        pass

    def _on_generate_adaptive_mesh(self):
        pass

    def _on_run_fea(self):
        pass

    def _on_boolean_op(self, *a):
        pass

    def _on_transform_op(self):
        pass

    def _on_mirror_op(self):
        pass

    def _on_pattern_op(self):
        pass

    def _on_condition_op(self, kind):
        self.condition_ops.append(kind)

    def _on_focus_filter(self):
        pass

    def _on_run_optimization_default(self):
        pass

    def _on_visualize_result(self):
        pass

    def _on_export(self):
        pass

    def _on_export_step(self):
        pass

    def _on_validate(self):
        pass

    def statusBar(self):
        class _Bar:
            def showMessage(self, *a):
                pass

        return _Bar()


def _app():
    return QApplication.instance() or QApplication([])


def test_conditions_dropdown_builds_and_fires():
    _app()
    owner = _Owner()
    ribbon = WorkspaceBuilder(owner).build_ribbon()
    btn = owner.rb_conditions
    assert isinstance(btn, RibbonTool)
    labels = [a.text() for a in btn.menu().actions()]
    assert labels == ["Carga", "Elasticidad", "Obstrucción", "Región protegida"]
    for action, kind in zip(btn.menu().actions(),
                            ["load", "elasticity", "obstruction", "protected"]):
        action.trigger()
        assert owner.condition_ops[-1] == kind
    assert ribbon is not None
