"""menus - construcción de la barra de menú (Archivo · Editar · Operaciones ...

Extrae de MainWindow la construcción visual de los menús. Los handlers a los que
se conectan las acciones (`_on_import`, `_on_boolean_op`, ...) siguen viviendo en
MainWindow; aquí solo se ensamblan los QAction y se devuelven las referencias que
la ventana necesita (acciones de vista con checkable, etc.).

ANTES → DESPUÉS → CONEXIÓN PRESERVADA
  MainWindow._build_menus (187-302)
      → MenuBuilder.build(owner).menu_bar / .action_view
        → clicks/triggers conectados a owner._on_* igual que antes.
"""

from __future__ import annotations

from PySide6.QtGui import QAction

from desktop.viewport.camera import StandardView


class MenuBuilder:
    """Construye la barra de menú de la ventana.

    ``owner`` es el objeto (MainWindow) que implementa los handlers de UI
    (``_on_*``) a los que las acciones se conectan. La ventana se mantiene como
    coordinador; este componente solo ensambla el menú.
    """

    def __init__(self, owner) -> None:
        self.owner = owner
        self.action_view: dict[str, QAction] = {}

    def build(self):
        """Crea la barra de menú completa y devuelve (menu_bar, action_view)."""
        owner = self.owner
        menubar = owner.menuBar()

        self._build_file(menubar, owner)
        self._build_edit(menubar, owner)
        self._build_operations(menubar, owner)
        self._build_conditions(menubar, owner)
        self._build_study(menubar, owner)
        self._build_view(menubar, owner)
        self._build_tools(menubar, owner)
        self._build_help(menubar, owner)
        return menubar, self.action_view

    # -- Archivo -----------------------------------------------------
    def _build_file(self, menubar, owner) -> None:
        file_menu = menubar.addMenu("&Archivo")
        act_open = QAction("Importar archivo STEP...", owner)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(owner._on_import)
        file_menu.addAction(act_open)
        act_exp = QAction("Exportar resultado...", owner)
        act_exp.triggered.connect(owner._on_export)
        file_menu.addAction(act_exp)
        file_menu.addSeparator()
        act_quit = QAction("Salir", owner)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(owner.close)
        file_menu.addAction(act_quit)

    # -- Editar ------------------------------------------------------
    def _build_edit(self, menubar, owner) -> None:
        edit_menu = menubar.addMenu("&Editar")
        act_clr = QAction("Limpiar selección", owner)
        act_clr.triggered.connect(owner._on_clear_selection)
        edit_menu.addAction(act_clr)
        act_reset = QAction("Reiniciar flujo", owner)
        act_reset.triggered.connect(owner._on_reset_flow)
        edit_menu.addAction(act_reset)

    # -- Operaciones (CAD) -------------------------------------------
    def _build_operations(self, menubar, owner) -> None:
        ops_menu = menubar.addMenu("&Operaciones")
        boolean_sub = ops_menu.addMenu("Boolean")
        for label, op in [("Unión", "union"), ("Corte", "difference"),
                          ("Intersección", "intersection")]:
            act = QAction(label, owner)
            act.triggered.connect(lambda _=False, o=op: owner._on_boolean_op(o))
            boolean_sub.addAction(act)
        for label, handler in [("Transformar...", owner._on_transform_op),
                               ("Simetría...", owner._on_mirror_op),
                               ("Patrón...", owner._on_pattern_op)]:
            act = QAction(label, owner)
            act.triggered.connect(handler)
            ops_menu.addAction(act)

    # -- Condiciones ------------------------------------------------
    def _build_conditions(self, menubar, owner) -> None:
        cond_menu = menubar.addMenu("&Condiciones")
        for label, kind in [("Carga", "load"), ("Elasticidad", "elasticity"),
                            ("Obstrucción", "obstruction"),
                            ("Región protegida", "protected")]:
            act = QAction(label, owner)
            act.triggered.connect(lambda _=False, k=kind: owner._on_condition_op(k))
            cond_menu.addAction(act)

    # -- Estudio ----------------------------------------------------
    def _build_study(self, menubar, owner) -> None:
        study_menu = menubar.addMenu("&Estudio")
        act_new = QAction("Nuevo estudio de optimización...", owner)
        act_new.triggered.connect(owner._on_create_study)
        study_menu.addAction(act_new)
        act_run = QAction("Ejecutar estudio (topología)", owner)
        act_run.triggered.connect(owner._on_run_study)
        study_menu.addAction(act_run)

    # -- Diseño (vistas) --------------------------------------------
    def _build_view(self, menubar, owner) -> None:
        view_menu = menubar.addMenu("&Diseño")
        presets = [
            ("Isométrica", StandardView.ISO),
            ("Frontal", StandardView.FRONT),
            ("Superior", StandardView.TOP),
            ("Lateral derecha", StandardView.RIGHT),
        ]
        for label, key in presets:
            act = QAction(label, owner)
            act.setCheckable(True)
            act.triggered.connect(lambda _=False, k=key: owner._on_view(k))
            view_menu.addAction(act)
            self.action_view[key] = act
        view_menu.addSeparator()
        act_fit = QAction("Ajustar a pantalla", owner)
        act_fit.setShortcut("F")
        act_fit.triggered.connect(lambda: owner.viewport.fit_to_view())
        view_menu.addAction(act_fit)
        act_center = QAction("Centrar modelo", owner)
        act_center.triggered.connect(lambda: owner.viewport.center_model())
        view_menu.addAction(act_center)

    # -- Herramientas -----------------------------------------------
    def _build_tools(self, menubar, owner) -> None:
        tools_menu = menubar.addMenu("&Herramientas")
        act_gm = QAction("Generar malla", owner)
        act_gm.triggered.connect(
            lambda: owner._on_generate_mesh(owner.properties._element_size.value()))
        tools_menu.addAction(act_gm)
        act_fea = QAction("Análisis FEM", owner)
        act_fea.triggered.connect(owner._on_run_fea)
        tools_menu.addAction(act_fea)
        act_opt = QAction("Optimizar SIMP", owner)
        act_opt.triggered.connect(owner._on_run_optimization_default)
        tools_menu.addAction(act_opt)

    # -- Ayuda ------------------------------------------------------
    def _build_help(self, menubar, owner) -> None:
        help_menu = menubar.addMenu("Ay&uda")
        act_about = QAction("Acerca de", owner)
        act_about.triggered.connect(owner._on_about)
        help_menu.addAction(act_about)


__all__ = ["MenuBuilder"]
