# pictocode/ui/main_window.py
import os
import json
import logging
from PyQt5.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QMenuBar,
    QLabel,
    QAction,
    QFileDialog,
    QMessageBox,
    QDialog,
    QGraphicsOpacityEffect,
    QToolBar,
    QWIDGETSIZE_MAX,
    QStyle,
    QTabWidget,
)
from PyQt5.QtCore import (
    Qt,
    QSettings,
    QPropertyAnimation,
    QTimer,
    QEvent,
    QPointF,
    QPoint,
    QRect,
    QObject,
)
from .corner_tabs import CornerTabs
from PyQt5.QtGui import QPalette, QColor, QKeySequence, QCursor
from PyQt5.QtWidgets import QApplication
from ..utils import generate_pycode, get_contrast_color
from ..canvas import CanvasWidget
from .toolbar import Toolbar
from .title_bar import TitleBar
from .inspector import Inspector
from .home_page import HomePage
from .new_project_dialog import NewProjectDialog
from .animated_menu import AnimatedMenu
from .shortcut_settings_dialog import ShortcutSettingsDialog
from .imports_dock import ImportsWidget
from .layers_dock import LayersWidget
from .layout_dock import LayoutWidget
from .corner_handle import CornerHandle

from .logs_dock import LogsWidget
from .debug_dialog import DebugDialog

logger = logging.getLogger(__name__)
PROJECTS_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "Projects")


class _ReleaseFilter(QObject):
    """Global filter to reset the cursor after resizing."""

    def __init__(self, window):
        super().__init__(window)
        self._window = window

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease and self._window._resizing:
            self._window._resizing = False
            self._window.unsetCursor()
        return False


class MainWindow(QMainWindow):
    EDGE_MARGIN = 6
    CORNER_REGION = 20
    # minimum dock dimension when collapsed/expanded
    MIN_DOCK_SIZE = 0

    def _dock_frame_width(self, dock):
        """Return the frame width of ``dock`` using the current style."""
        return dock.style().pixelMetric(QStyle.PM_DockWidgetFrameWidth, None, dock)

    def _header_min_size(self, dock, orientation):
        """Return dock header size including frame."""
        frame = self._dock_frame_width(dock) * 2
        return self.MIN_DOCK_SIZE + frame
    # ensure drag related attributes exist before __init__ runs
    _corner_current_dock = None
    _split_current_dock = None  # backward compatibility with older versions
    _split_start_size = 0
    def __init__(self):
        super().__init__()
        logger.debug("MainWindow initialized")
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setWindowTitle("Pictocode")
        self.resize(1024, 768)

        # crée dossier projects
        os.makedirs(PROJECTS_DIR, exist_ok=True)

        # Stack home ↔ document
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Custom title bar and menu
        self._menu_container = QWidget(self)
        _ml = QVBoxLayout(self._menu_container)
        _ml.setContentsMargins(0, 0, 0, 0)
        _ml.setSpacing(0)
        self.title_bar = TitleBar(self)
        _ml.addWidget(self.title_bar)
        self.save_status = QLabel("", self._menu_container)
        self.save_status.setObjectName("save_status")
        self.save_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.save_status.hide()
        self.menu_bar = QMenuBar(self._menu_container)
        self.menu_bar.setCornerWidget(self.save_status, Qt.TopRightCorner)
        _ml.addWidget(self.menu_bar)
        self.setMenuWidget(self._menu_container)
        self._status_timer = None
        self._resizing = False
        self._resize_edges = Qt.Edges()
        self._start_pos = None
        self._start_geom = None
        # Compatibility flag for older code paths
        # that expected ``_corner_dragging`` to exist.
        self._corner_dragging = False
        self._corner_dragging_dock = None
        self._corner_start = QPointF()
        self._corner_current_dock = None
        # maintain attribute used by older versions
        self._split_current_dock = None
        self._split_orientation = Qt.Horizontal
        self._split_preview = None
        self._split_start_size = 0

        # Global filter to ensure cursor resets after window resizing
        self._release_filter = _ReleaseFilter(self)
        QApplication.instance().installEventFilter(self._release_filter)

        # Paramètres de l'application
        self.settings = QSettings("pictocode", "pictocode")
        self.favorite_projects = self.settings.value(
            "favorite_projects", [], type=list)
        self.recent_projects = self.settings.value(
            "recent_projects", [], type=list)
        self.imported_images = self.settings.value(
            "imported_images", [], type=list)
        self.template_projects = self.settings.value(
            "template_projects", [], type=list)
        self.autosave_enabled = self.settings.value(
            "autosave_enabled", False, type=bool)
        self.autosave_interval = int(
            self.settings.value("autosave_interval", 5))
        self.auto_show_inspector = self.settings.value(
            "auto_show_inspector", True, type=bool)
        # By default dock widgets are attached to the main window
        self.float_docks = self.settings.value(
            "float_docks", False, type=bool)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave)
        if self.autosave_enabled:
            self._autosave_timer.start(self.autosave_interval * 60000)

        # Page accueil
        self.home = HomePage(self)
        self.stack.addWidget(self.home)

        # Page projet avec interface à onglets
        self.canvas = CanvasWidget(self)

        # Toolbar & inspecteur (cachés par défaut)
        self.toolbar = Toolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setVisible(False)

        self.inspector = Inspector(self)
        self.imports = ImportsWidget(self)
        for img in self.imported_images:
            self.imports.add_image(img)
        self.layout = LayoutWidget(self)
        self.logs_widget = LogsWidget(self)
        self.category_widgets = {
            "Plan de travail": self.canvas,
            "Propriétés": self.inspector,
            "Imports": self.imports,
            "Objets": self.layout,
            "Logs": self.logs_widget,
        }

        # Interface par onglets contenant toutes les sections
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setStyleSheet(
            "QTabBar::tab { padding: 6px 12px; }"
        )
        for label, widget in self.category_widgets.items():
            self.tabs.addTab(widget, label)
        self.stack.addWidget(self.tabs)
        self.widget_docks = {}
        self.dock_headers = {}
        self.dock_current_widget = {}

        # état courant
        self.current_project_path = None
        self.unsaved_changes = False
        self._current_anim = None

        # Paramètres de thème et raccourcis
        self.current_theme = self.settings.value("theme", "Light")
        self.accent_color = QColor(self.settings.value("accent_color", "#0078d7"))
        self.font_size = int(self.settings.value("font_size", 10))
        self.menu_color = QColor(self.settings.value("menu_color", self.accent_color.name()))
        self.toolbar_color = QColor(self.settings.value("toolbar_color", self.accent_color.name()))
        self.dock_color = QColor(self.settings.value("dock_color", self.accent_color.name()))
        self.dock_title_colors = {
            name: QColor(
                self.settings.value(
                    f"dock_title_color_{name}", self.toolbar_color.name()
                )
            )
            for name in (
                "Plan de travail",
                "Propriétés",
                "Imports",
                "Objets",
                "Logs",
            )
        }
        self.flag_active_color = QColor(self.settings.value("flag_active_color", "#0078d7"))
        self.flag_inactive_color = QColor(self.settings.value("flag_inactive_color", "#3a3f44"))
        self.menu_font_size = int(self.settings.value("menu_font_size", self.font_size))
        self.toolbar_font_size = int(self.settings.value("toolbar_font_size", self.font_size))
        self.dock_font_size = int(self.settings.value("dock_font_size", self.font_size))
        self.show_splash = self.settings.value("show_splash", True, type=bool)
        self.handle_size = int(self.settings.value("handle_size", 12))
        self.rotation_offset = int(self.settings.value("rotation_offset", 20))
        self.handle_color = QColor(self.settings.value("handle_color", "#000000"))
        self.rotation_handle_color = QColor(
            self.settings.value("rotation_handle_color", "#ff0000")
        )
        # taille par défaut des onglets dépliés
        self.default_dock_size = int(self.settings.value("default_dock_size", 200))

        self.layers = LayersWidget(self)
        self.toolbar.addWidget(self.layers)

        # plus de panneaux flottants, tout est dans les onglets
        self.inspector_dock = None
        self.imports_dock = None
        self.layout_dock = None
        self.logs_dock = None
        self.docks = []
        self.corner_tabs = None

        # Indicateur de glissement pour les anciennes fonctionnalités
        self.drag_indicator = QWidget(self)
        self.drag_indicator.setObjectName("drag_indicator")
        self.drag_indicator.setFixedSize(10, 10)
        self.drag_indicator.hide()

        # Dialog nouveau projet
        self.new_proj_dlg = NewProjectDialog(self)
        self.new_proj_dlg.accepted.connect(self._on_new_project_accepted)

        # Barre de menu
        self._build_menu()

        self.default_shortcuts = {
            "new": "Ctrl+N",
            "open": "Ctrl+O",
            "save": "Ctrl+S",
            "saveas": "Ctrl+Shift+S",
            "export_image": "Ctrl+E",
            "export_svg": "",
            "export_code": "",
            "home": "Ctrl+H",
            "exit": "Ctrl+Q",
            "project_props": "Ctrl+P",
            "appearance": "",
            "shortcuts": "",
            "copy": "Ctrl+C",
            "cut": "Ctrl+X",
            "paste": "Ctrl+V",
            "undo": "Ctrl+Z",
            "redo": "Ctrl+Shift+Z",
            "duplicate": "Ctrl+D",
            "delete": "Delete",
            "select_all": "Ctrl+A",
            "flip_horizontal": "",
            "flip_vertical": "",
            "zoom_in": "Ctrl++",
            "zoom_out": "Ctrl+-",
            "toggle_grid": "Ctrl+G",
            "toggle_snap": "Ctrl+Shift+G",
            "grid_size": "",
            "export_pdf": "",
        }
        self.apply_theme(
            self.current_theme,
            self.accent_color,
            self.font_size,
            self.menu_color,
            self.toolbar_color,
            self.dock_color,
            self.menu_font_size,
            self.toolbar_font_size,
            self.dock_font_size,
            self.flag_active_color,
            self.flag_inactive_color,
        )
        self._apply_handle_settings()
        self._load_shortcuts()
        self._set_project_actions_enabled(False)

        # page par défaut : accueil, les onglets restent cachés

    def _create_dock(self, label, area):
        dock = QDockWidget(label, self)

        # header placed in the title bar
        header = CornerTabs(dock, color=self.dock_title_colors.get(label))
        header.selector.setCurrentText(label)
        header.tab_selected.connect(
            lambda text, d=dock: self.set_dock_category(d, text)
        )
        dock.setTitleBarWidget(header)
        frame = self._dock_frame_width(dock) * 2

        container = QWidget()
        container.setMinimumSize(0, 0)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        widget = self.category_widgets[label]
        widget.setMinimumSize(0, 0)
        lay.addWidget(widget)
        container.setLayout(lay)

        combo_size = header.selector.sizeHint()
        dock.setMinimumHeight(self.MIN_DOCK_SIZE)
        dock.setMinimumWidth(self.MIN_DOCK_SIZE)

        handle = CornerHandle(dock)
        handle.installEventFilter(self)
        header.set_handle(handle)
        dock.setWidget(container)
        if self.float_docks:
            dock.setAllowedAreas(Qt.NoDockWidgetArea)
        else:
            dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.addDockWidget(area, dock)
        dock.setFloating(self.float_docks)
        dock.setVisible(True)
        self.widget_docks[widget] = dock
        self.dock_headers[dock] = header
        self.dock_current_widget[dock] = widget
        dock.installEventFilter(self)
        if dock.widget():
            dock.widget().installEventFilter(self)
        # also monitor the contained widget for drag events
        if widget:
            widget.installEventFilter(self)
        self.docks.append(dock)
        return dock

    def _build_menu(self):
        mb = self.menu_bar
        filem = AnimatedMenu("Fichier", self)
        mb.addMenu(filem)
        self.actions = {}

        editm = AnimatedMenu("Édition", self)
        mb.addMenu(editm)

        copy_act = QAction("Copier", self)
        copy_act.triggered.connect(self.copy_selection)
        editm.addAction(copy_act)
        self.actions["copy"] = copy_act

        cut_act = QAction("Couper", self)
        cut_act.triggered.connect(self.cut_selection)
        editm.addAction(cut_act)
        self.actions["cut"] = cut_act

        paste_act = QAction("Coller", self)
        paste_act.triggered.connect(self.paste_clipboard)
        editm.addAction(paste_act)
        self.actions["paste"] = paste_act

        editm.addSeparator()

        undo_act = QAction("Annuler", self)
        undo_act.triggered.connect(self.undo)
        editm.addAction(undo_act)
        self.actions["undo"] = undo_act

        redo_act = QAction("Rétablir", self)
        redo_act.triggered.connect(self.redo)
        editm.addAction(redo_act)
        self.actions["redo"] = redo_act

        dup_act = QAction("Dupliquer", self)
        dup_act.triggered.connect(self.duplicate_selection)
        editm.addAction(dup_act)
        self.actions["duplicate"] = dup_act

        flip_h_act = QAction("Miroir horizontal", self)
        flip_h_act.triggered.connect(self.flip_horizontal)
        editm.addAction(flip_h_act)
        self.actions["flip_horizontal"] = flip_h_act

        flip_v_act = QAction("Miroir vertical", self)
        flip_v_act.triggered.connect(self.flip_vertical)
        editm.addAction(flip_v_act)
        self.actions["flip_vertical"] = flip_v_act

        del_act = QAction("Supprimer", self)
        del_act.triggered.connect(self.delete_selection)
        editm.addAction(del_act)
        self.actions["delete"] = del_act

        sel_all_act = QAction("Tout sélectionner", self)
        sel_all_act.triggered.connect(self.select_all)
        editm.addAction(sel_all_act)
        self.actions["select_all"] = sel_all_act

        editm.addSeparator()

        zoom_in_act = QAction("Zoom avant", self)
        zoom_in_act.triggered.connect(self.zoom_in)
        editm.addAction(zoom_in_act)
        self.actions["zoom_in"] = zoom_in_act

        zoom_out_act = QAction("Zoom arrière", self)
        zoom_out_act.triggered.connect(self.zoom_out)
        editm.addAction(zoom_out_act)
        self.actions["zoom_out"] = zoom_out_act

        grid_act = QAction("Afficher/Masquer grille", self)
        grid_act.triggered.connect(self.toggle_grid)
        editm.addAction(grid_act)
        self.actions["toggle_grid"] = grid_act

        snap_act = QAction("Magnétisme grille", self)
        snap_act.triggered.connect(self.toggle_snap)
        editm.addAction(snap_act)
        self.actions["toggle_snap"] = snap_act

        grid_size_act = QAction("Taille de grille…", self)
        grid_size_act.triggered.connect(self.set_grid_size)
        editm.addAction(grid_size_act)
        self.actions["grid_size"] = grid_size_act

        new_act = QAction("Nouveau…", self)
        new_act.triggered.connect(self.open_new_project_dialog)
        filem.addAction(new_act)
        self.actions["new"] = new_act

        open_act = QAction("Ouvrir…", self)
        open_act.triggered.connect(self._on_file_open)
        filem.addAction(open_act)
        self.actions["open"] = open_act

        filem.addSeparator()

        save_act = QAction("Enregistrer", self)
        save_act.triggered.connect(self.save_project)
        filem.addAction(save_act)
        self.actions["save"] = save_act

        saveas_act = QAction("Enregistrer sous…", self)
        saveas_act.triggered.connect(self.save_as_project)
        filem.addAction(saveas_act)
        self.actions["saveas"] = saveas_act

        export_img_act = QAction("Exporter en image…", self)
        export_img_act.triggered.connect(self.export_image)
        filem.addAction(export_img_act)
        self.actions["export_image"] = export_img_act

        export_svg_act = QAction("Exporter en SVG…", self)
        export_svg_act.triggered.connect(self.export_svg)
        filem.addAction(export_svg_act)
        self.actions["export_svg"] = export_svg_act

        export_pdf_act = QAction("Exporter en PDF…", self)
        export_pdf_act.triggered.connect(self.export_pdf)
        filem.addAction(export_pdf_act)
        self.actions["export_pdf"] = export_pdf_act

        export_code_act = QAction("Exporter en code Python…", self)
        export_code_act.triggered.connect(self.export_pycode)
        filem.addAction(export_code_act)
        self.actions["export_code"] = export_code_act

        filem.addSeparator()

        home_act = QAction("Accueil", self)
        home_act.triggered.connect(self.back_to_home)
        filem.addAction(home_act)
        self.actions["home"] = home_act

        exit_act = QAction("Quitter", self)
        exit_act.triggered.connect(self.close)
        filem.addAction(exit_act)
        self.actions["exit"] = exit_act

        projectm = AnimatedMenu("Projet", self)
        mb.addMenu(projectm)
        props_act = QAction("Paramètres…", self)
        props_act.triggered.connect(self.open_project_settings)
        projectm.addAction(props_act)
        self.actions["project_props"] = props_act

        debug_act = QAction("Debug", self)
        debug_act.triggered.connect(self.show_debug_dialog)
        projectm.addAction(debug_act)
        self.actions["debug"] = debug_act

        prefm = AnimatedMenu("Préférences", self)
        mb.addMenu(prefm)
        prefs_act = QAction("Paramètres…", self)
        prefs_act.triggered.connect(self.open_settings_dialog)
        prefm.addAction(prefs_act)
        self.actions["preferences"] = prefs_act

    # ─── Gestion de l'état modifié ─────────────────────────────
    def set_dirty(self, value: bool = True):
        self.unsaved_changes = value
        title = self.windowTitle().lstrip("* ").strip()
        if value:
            self.setWindowTitle("* " + title)
        else:
            self.setWindowTitle(title)

    def maybe_save(self) -> bool:
        if self.stack.currentWidget() is self.home or not self.unsaved_changes:
            return True
        resp = QMessageBox.question(
            self,
            "Projet non enregistré",
            "Voulez-vous enregistrer les modifications ?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if resp == QMessageBox.Save:
            self.save_project()
            return not self.unsaved_changes
        return resp == QMessageBox.Discard

    def open_new_project_dialog(self):
        if self.maybe_save():
            self.new_proj_dlg.open()

    def open_project_settings(self):
        if not hasattr(self.canvas, "current_meta"):
            return
        from .project_settings_dialog import ProjectSettingsDialog

        dlg = ProjectSettingsDialog(self.canvas.current_meta, self)
        if dlg.exec_() == QDialog.Accepted:
            params = dlg.get_parameters()
            self.canvas.update_document_properties(**params)
            self.set_dirty(True)

    def _on_new_project_accepted(self):
        """Récupère les paramètres, crée le document et bascule sur canvas."""
        params = self.new_proj_dlg.get_parameters()
        project_name = params.get("name") or "Sans titre"
        # exemple : changer le titre de la fenêtre
        self.setWindowTitle(f"Pictocode — {project_name}")

        # crée le document dans le canvas
        self.canvas.new_document(
            width=params["width"],
            height=params["height"],
            unit=params["unit"],
            orientation=params["orientation"],
            color_mode=params["color_mode"],
            dpi=params["dpi"],
            name=params.get("name", ""),
        )
        self.layers.populate()

        self.layout.populate()

        # affiche la barre d'outils et l'interface à onglets
        self.toolbar.setVisible(True)
        self.tabs.setCurrentWidget(self.canvas)

        self._set_project_actions_enabled(True)
        # bascule sur l'interface à onglets
        self._switch_page(self.tabs)
        self.current_project_path = None
        self.set_dirty(False)

    def _on_file_open(self):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir un projet",
            PROJECTS_DIR,
            "Pictocode (*.json *.ptc)",
        )
        if path:
            try:
                if path.lower().endswith(".ptc"):
                    import zipfile
                    import tempfile

                    with zipfile.ZipFile(path, "r") as zf:
                        with zf.open("project.json") as f:
                            data = json.load(f)
                        tmp = tempfile.mkdtemp(prefix="pictocode_")
                        for name in zf.namelist():
                            if name.startswith("images/"):
                                zf.extract(name, tmp)
                        for shp in data.get("shapes", []):
                            if shp.get("type") == "image":
                                shp["path"] = os.path.join(tmp, shp["path"])
                else:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                params = {
                    k: data[k]
                    for k in (
                        "name",
                        "width",
                        "height",
                        "unit",
                        "orientation",
                        "color_mode",
                        "dpi",
                    )
                }
                shapes = data.get("shapes", [])
                layers = data.get("layers", [])
                self.open_project(path, params, shapes, layers)
            except Exception as e:
                QMessageBox.critical(
                    self, "Erreur", f"Impossible d'ouvrir : {e}")

    def open_project(self, path, params, shapes=None, layers=None):
        """Charge un projet existant."""
        if not self.maybe_save():
            return
        self.current_project_path = path
        # crée document
        self.canvas.new_document(**params)
        # calques
        self.canvas.setup_layers(layers or [])

        self.layers.populate()
        self.layout.populate()

        # charge formes
        self.canvas.load_shapes(shapes or [])
        # bascule UI
        self.toolbar.setVisible(True)
        self.tabs.setCurrentWidget(self.canvas)

        self._set_project_actions_enabled(True)
        self._switch_page(self.tabs)
        self.setWindowTitle(f"Pictocode — {params.get('name', '')}")
        self.set_dirty(False)
        self.add_recent_project(path)
        self.home.populate_lists()

    def save_project(self):
        if not self.current_project_path:
            return self.save_as_project()
        data = self.canvas.export_project()
        self.show_status("Enregistrement…")
        try:
            if self.current_project_path.lower().endswith(".ptc"):
                import zipfile
                import tempfile

                tmp_thumb = tempfile.mkstemp(suffix=".png")[1]
                self.canvas.export_image(tmp_thumb, "PNG")

                images = []
                for shp in data.get("shapes", []):
                    if (
                        shp.get("type") == "image"
                        and os.path.exists(shp["path"])
                    ):
                        images.append(
                            (shp["path"], os.path.basename(shp["path"])))
                        shp["path"] = f"images/{os.path.basename(shp['path'])}"

                with zipfile.ZipFile(self.current_project_path, "w") as zf:
                    zf.writestr(
                        "project.json",
                        json.dumps(data, indent=2, ensure_ascii=False),
                    )
                    zf.write(tmp_thumb, "thumbnail.png")
                    os.remove(tmp_thumb)
                    for src, name in images:
                        zf.write(src, f"images/{name}")
            else:
                with open(
                    self.current_project_path, "w", encoding="utf-8"
                ) as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                # also save preview
                thumb = os.path.splitext(self.current_project_path)[0] + ".png"
                self.canvas.export_image(thumb, "PNG")
            self.set_dirty(False)
            self.show_status("Projet enregistré")
            self.add_recent_project(self.current_project_path)
            self.home.populate_lists()
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur", f"Impossible d'enregistrer : {e}")

    def _autosave(self):
        if (
            self.autosave_enabled
            and self.current_project_path
            and self.unsaved_changes
        ):
            self.save_project()

    def save_as_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            PROJECTS_DIR,
            "Pictocode (*.json *.ptc)",
        )
        if path:
            if not path.lower().endswith(('.json', '.ptc')):
                path += '.json'
            self.current_project_path = path
            self.save_project()
            base = os.path.basename(os.path.splitext(path)[0])
            self.setWindowTitle(f"Pictocode — {base}")

    def export_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter comme image",
            PROJECTS_DIR,
            "PNG (*.png);;JPEG (*.jpg *.jpeg)",
        )
        if path:
            fmt = "PNG"
            lower = path.lower()
            if lower.endswith(".jpg") or lower.endswith(".jpeg"):
                fmt = "JPEG"
            self.canvas.export_image(path, fmt)

    def export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter comme SVG", PROJECTS_DIR, "SVG (*.svg)"
        )
        if path:
            if not path.lower().endswith(".svg"):
                path += ".svg"
            self.canvas.export_svg(path)

    def export_pycode(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter en code Python", PROJECTS_DIR, "Python (*.py)"
        )
        if path:
            if not path.lower().endswith(".py"):
                path += ".py"
            shapes = [
                it
                for it in self.canvas.scene.items()
                if it is not self.canvas._frame_item
            ]
            code = generate_pycode(shapes)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(code)
            except Exception as e:
                QMessageBox.critical(
                    self, "Erreur", f"Impossible d'exporter : {e}")

    def back_to_home(self):
        if not self.maybe_save():
            return
        # Réinitialise le canvas et oublie le projet courant
        self.canvas.scene.clear()
        self.current_project_path = None
        if hasattr(self.canvas, "current_meta"):
            self.canvas.current_meta = {}
        self.setWindowTitle("Pictocode")
        self._switch_page(self.home)
        self.toolbar.setVisible(False)
        # les onglets sont masqués en revenant à l'accueil
        self._set_project_actions_enabled(False)

    # --- Edit actions -------------------------------------------------
    def copy_selection(self):
        from PyQt5.QtWidgets import QApplication
        import json

        data = self.canvas.copy_selected()
        if data:
            QApplication.clipboard().setText(json.dumps(data))

    def cut_selection(self):
        from PyQt5.QtWidgets import QApplication
        import json

        data = self.canvas.cut_selected()
        if data:
            QApplication.clipboard().setText(json.dumps(data))

    def paste_clipboard(self):
        from PyQt5.QtWidgets import QApplication
        import json

        try:
            data = json.loads(QApplication.clipboard().text())
        except Exception:
            data = None
        if data:
            self.canvas.paste_item(data)

    def duplicate_selection(self):
        self.canvas.duplicate_selected()

    def flip_horizontal(self):
        self.canvas.flip_horizontal_selected()

    def flip_vertical(self):
        self.canvas.flip_vertical_selected()

    def delete_selection(self):
        self.canvas.delete_selected()

    def select_all(self):
        self.canvas.select_all()

    def zoom_in(self):
        self.canvas.zoom_in()

    def zoom_out(self):
        self.canvas.zoom_out()

    def toggle_grid(self):
        self.canvas._toggle_grid()

    def toggle_snap(self):
        self.canvas._toggle_snap()

    def undo(self):
        self.canvas.undo()

    def redo(self):
        self.canvas.redo()

    def set_grid_size(self):
        from PyQt5.QtWidgets import QInputDialog

        size, ok = QInputDialog.getInt(
            self,
            "Taille de la grille",
            "Pixels :",
            self.canvas.grid_size,
            1,
            200,
        )
        if ok:
            self.canvas.set_grid_size(size)

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter en PDF", PROJECTS_DIR, "PDF (*.pdf)"
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.canvas.export_pdf(path)

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self.maybe_save():
            QApplication.instance().removeEventFilter(self._release_filter)
            event.accept()
        else:
            event.ignore()

    # ------------------------------------------------------------------

    def open_settings_dialog(self):
        """Display the unified settings dialog."""
        current_shortcuts = {
            name: act.shortcut().toString()
            for name, act in self.actions.items()
        }
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(
            current_shortcuts,
            self.current_theme,
            self.accent_color,
            self.font_size,
            self.menu_color,
            self.toolbar_color,
            self.dock_color,
            self.menu_font_size,
            self.toolbar_font_size,
            self.dock_font_size,
            self.show_splash,
            self.autosave_enabled,
            self.autosave_interval,
            self.auto_show_inspector,
            self.float_docks,
            self.dock_title_colors,
            self,
        )
        if dlg.exec_() == QDialog.Accepted:
            theme = dlg.get_theme()
            accent = dlg.get_accent_color()
            font_size = dlg.get_font_size()
            menu_col = dlg.get_menu_color()
            toolbar_col = dlg.get_toolbar_color()
            dock_col = dlg.get_dock_color()
            menu_fs = dlg.get_menu_font_size()
            toolbar_fs = dlg.get_toolbar_font_size()
            dock_fs = dlg.get_dock_font_size()
            self.show_splash = dlg.get_show_splash()
            self.autosave_enabled = dlg.get_autosave_enabled()
            self.autosave_interval = dlg.get_autosave_interval()
            self.auto_show_inspector = dlg.get_auto_show_inspector()
            self.float_docks = dlg.get_float_docks()
            self.dock_title_colors = dlg.get_dock_title_colors()
            shorts = dlg.get_shortcuts()
            for name, seq in shorts.items():
                action = self.actions.get(name)
                if action is not None:
                    action.setShortcut(QKeySequence(seq))
                    self.settings.setValue(f"shortcut_{name}", seq)
            if self.auto_show_inspector:
                items = self.canvas.scene.selectedItems()
                if items:
                    self.tabs.setCurrentWidget(self.inspector)
            self._apply_float_docks()
            self.apply_theme(
                theme,
                accent,
                font_size,
                menu_col,
                toolbar_col,
                dock_col,
                menu_fs,
                toolbar_fs,
                dock_fs,
                self.flag_active_color,
                self.flag_inactive_color,
            )
            self.settings.setValue("show_splash", self.show_splash)
            self.settings.setValue("autosave_enabled", self.autosave_enabled)
            self.settings.setValue("autosave_interval", self.autosave_interval)
            self.settings.setValue(
                "auto_show_inspector", self.auto_show_inspector
            )
            self.settings.setValue("float_docks", self.float_docks)
            for name, col in self.dock_title_colors.items():
                self.settings.setValue(
                    f"dock_title_color_{name}", col.name()
                )
            if self.autosave_enabled:
                self._autosave_timer.start(self.autosave_interval * 60000)
            else:
                self._autosave_timer.stop()

    # backward compatibility
    def open_app_settings(self):
        self.open_settings_dialog()

    def open_shortcut_settings(self):
        self.open_settings_dialog()
    def show_debug_dialog(self):
        """Display a dialog with debug information about the project."""
        if not hasattr(self, "canvas"):
            return
        logger.debug("Generating debug report")
        text = self.canvas.get_debug_report()
        dlg = DebugDialog(text, self)
        dlg.exec_()

    def _switch_page(self, widget):
        current = self.stack.currentWidget()
        if current is widget:
            return
        out_eff = QGraphicsOpacityEffect(current)
        current.setGraphicsEffect(out_eff)
        out_anim = QPropertyAnimation(out_eff, b"opacity", self)
        out_anim.setDuration(200)
        out_anim.setStartValue(1)
        out_anim.setEndValue(0)

        def _on_fade_out():
            current.setGraphicsEffect(None)
            self.stack.setCurrentWidget(widget)
            in_eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(in_eff)
            in_anim = QPropertyAnimation(in_eff, b"opacity", self)
            in_anim.setDuration(200)
            in_anim.setStartValue(0)
            in_anim.setEndValue(1)
            in_anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            in_anim.start(QPropertyAnimation.DeleteWhenStopped)
            self._current_anim = in_anim

        out_anim.finished.connect(_on_fade_out)
        out_anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._current_anim = out_anim

    def apply_theme(
        self,
        theme: str,
        accent: QColor | None = None,
        font_size: int | None = None,
        menu_color: QColor | None = None,
        toolbar_color: QColor | None = None,
        dock_color: QColor | None = None,
        menu_font_size: int | None = None,
        toolbar_font_size: int | None = None,
        dock_font_size: int | None = None,
        flag_active: QColor | None = None,
        flag_inactive: QColor | None = None,
    ):
        """Applique un thème clair ou sombre ainsi que des réglages
        personnalisés."""
        app = QApplication.instance()
        accent = accent or self.accent_color
        font_size = font_size or self.font_size
        menu_color = menu_color or self.menu_color
        toolbar_color = toolbar_color or self.toolbar_color
        dock_color = dock_color or self.dock_color
        menu_font_size = menu_font_size or self.menu_font_size
        toolbar_font_size = toolbar_font_size or self.toolbar_font_size
        dock_font_size = dock_font_size or self.dock_font_size
        flag_active = flag_active or self.flag_active_color
        flag_inactive = flag_inactive or self.flag_inactive_color

        if theme.lower() == "dark":
            pal = QPalette()
            pal.setColor(QPalette.Window, QColor(53, 53, 53))
            pal.setColor(QPalette.WindowText, Qt.white)
            pal.setColor(QPalette.Base, QColor(35, 35, 35))
            pal.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            pal.setColor(QPalette.ToolTipBase, Qt.white)
            pal.setColor(QPalette.ToolTipText, Qt.white)
            pal.setColor(QPalette.Text, Qt.white)
            pal.setColor(QPalette.Button, QColor(53, 53, 53))
            pal.setColor(QPalette.ButtonText, Qt.white)
            pal.setColor(QPalette.Highlight, accent)
            pal.setColor(QPalette.HighlightedText,
                         QColor(get_contrast_color(accent)))
            app.setPalette(pal)
            app.setStyle("Fusion")
        else:
            pal = app.style().standardPalette()
            pal.setColor(QPalette.Highlight, accent)
            pal.setColor(QPalette.HighlightedText,
                         QColor(get_contrast_color(accent)))
            app.setPalette(pal)
            app.setStyle("Fusion")

        font = app.font()
        font.setPointSize(int(font_size))
        app.setFont(font)

        active = getattr(self, "flag_active_color", QColor("#0078d7"))
        inactive = getattr(self, "flag_inactive_color", QColor("#3a3f44"))

        tb_text = get_contrast_color(toolbar_color)
        menu_text = get_contrast_color(inactive)
        menu_fg = get_contrast_color(menu_color)

        self.setStyleSheet(
            f"""
            QToolBar {{
                background: {toolbar_color.name()};
                color: {tb_text};
                font-size: {toolbar_font_size}pt;
            }}
            QMenuBar {{
                background: transparent;
                font-size: {menu_font_size}pt;
                padding: 2px;
            }}
            QMenuBar::item {{
                background: {inactive.name()};
                color: {menu_text};
                padding: 4px 8px;
                margin: 0 2px;
                border-top-left-radius:4px;
                border-top-right-radius:4px;
            }}
            QMenuBar::item:selected {{
                background: {active.name()};
                margin-top: 2px;
            }}
            QMenuBar::item:pressed {{
                background: {active.name()};
                margin-top: 2px;
            }}
            QWidget#title_bar {{
                background: {toolbar_color.name()};
                color: {tb_text};
                font-size: {toolbar_font_size}pt;
            }}
            QWidget#title_bar QPushButton {{
                border: none;
                background: transparent;
                color: {tb_text};
                padding: 4px;
            }}
            QWidget#title_bar QPushButton:hover {{
                background: {toolbar_color.darker(110).name()};
            }}
            QMenu {{
                background-color: {menu_color.name()};
                color: {menu_fg};
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {menu_color.darker(130).name()};
            }}
            QWidget#drag_indicator {{
                background: red;
                border: 1px solid {accent.darker(150).name()};
            }}
            QWidget#corner_handle {{
                background: transparent;
            }}
            QDockWidget::title {{
                padding: 0px;
                margin: 0px;
            }}
            """
        )
        self.inspector.setStyleSheet(f"font-size: {dock_font_size}pt;")
        for dock in self.docks:
            style = (
                f"QDockWidget {{ background: {dock_color.name()}; border: none; }}"
                "QDockWidget::title { padding: 0px; margin: 0px; }"
            )
            dock.setStyleSheet(style)
            widget = dock.widget()
            if widget:
                widget.setStyleSheet(f"font-size: {dock_font_size}pt;")
                if hasattr(widget, "apply_theme"):
                    widget.apply_theme()
        for dock, header in self.dock_headers.items():
            col = self.dock_title_colors.get(dock.windowTitle(), toolbar_color)
            header.set_color(col)

        self.current_theme = theme
        self.accent_color = accent
        self.font_size = font_size
        self.menu_color = menu_color
        self.toolbar_color = toolbar_color
        self.dock_color = dock_color
        self.menu_font_size = menu_font_size
        self.toolbar_font_size = toolbar_font_size
        self.dock_font_size = dock_font_size
        self.flag_active_color = flag_active
        self.flag_inactive_color = flag_inactive
        self.settings.setValue("theme", theme)
        self.settings.setValue("accent_color", accent.name())
        self.settings.setValue("font_size", font_size)
        self.settings.setValue("menu_color", menu_color.name())
        self.settings.setValue("toolbar_color", toolbar_color.name())
        self.settings.setValue("dock_color", dock_color.name())
        self.settings.setValue("menu_font_size", menu_font_size)
        self.settings.setValue("toolbar_font_size", toolbar_font_size)
        self.settings.setValue("dock_font_size", dock_font_size)
        self.settings.setValue("flag_active_color", flag_active.name())
        self.settings.setValue("flag_inactive_color", flag_inactive.name())

    def _load_shortcuts(self):
        self.actions = getattr(self, "actions", {})
        for name, action in self.actions.items():
            seq = self.settings.value(
                f"shortcut_{name}", self.default_shortcuts.get(name, "")
            )
            if seq:
                action.setShortcut(QKeySequence(seq))

    def _apply_float_docks(self):
        """Set all dock widgets to floating or dockable mode."""
        for dock in self.docks:
            if self.float_docks:
                dock.setAllowedAreas(Qt.NoDockWidgetArea)
                dock.setFloating(True)
            else:
                dock.setAllowedAreas(Qt.AllDockWidgetAreas)
                dock.setFloating(False)

    def eventFilter(self, obj, event):
        dock = None

        o = obj
        while o is not None and not isinstance(o, QDockWidget):
            o = o.parent()
        if isinstance(o, QDockWidget):
            dock = o

        if dock:
            if event.type() == QEvent.Close:
                view = self.canvas.viewport()
                old_w = view.width()
                old_h = view.height()
                hbar = self.canvas.horizontalScrollBar()
                vbar = self.canvas.verticalScrollBar()
                old_hval = hbar.value()
                old_vval = vbar.value()
                area = self.dockWidgetArea(obj)

                def restore():
                    dw = view.width() - old_w
                    dh = view.height() - old_h
                    h = old_hval
                    v = old_vval
                    if area == Qt.LeftDockWidgetArea:
                        h -= dw
                    elif area == Qt.TopDockWidgetArea:
                        v -= dh
                    hbar.setValue(h)
                    vbar.setValue(v)

                QTimer.singleShot(0, restore)
            elif event.type() == QEvent.Resize and obj is dock:
                # Always evaluate against the vertical size so docks can
                # collapse down to just the header regardless of placement
                size = dock.height()
                header_size = self._header_min_size(dock, Qt.Vertical)
                header = self.dock_headers.get(dock)

                if size <= header_size and not getattr(dock, "_collapsed", False):
                    self._collapse_dock(dock, Qt.Vertical)
                elif size > header_size and getattr(dock, "_collapsed", False):
                    self._expand_dock(dock)
                else:
                    content = dock.widget()
                    if content and not getattr(dock, "_collapsed", False):
                        if size <= header_size:
                            content.hide()
                        else:
                            content.show()
                    if header:
                        if size <= header_size:
                            header.show_handle(False)
                        else:
                            header.show_handle(True)
                        header._position_handle()
            elif event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if obj is dock:
                    pos = event.pos()
                else:
                    pos = obj.mapTo(dock, event.pos())
                r = dock.rect()
                header = self.dock_headers.get(dock)
                frame = self._dock_frame_width(dock)
                header_h = (header.height() if header else 0) + frame
                corner = QRect(
                    r.width() - self.CORNER_REGION - frame,
                    header_h - self.CORNER_REGION,
                    self.CORNER_REGION,
                    self.CORNER_REGION,
                )
            if corner.contains(pos):
                self._corner_dragging = True
                self._corner_dragging_dock = dock
                self._corner_start = event.globalPos()
                dock.setCursor(Qt.SizeFDiagCursor)
                self._show_drag_indicator(event.globalPos())
                return True
            elif event.type() == QEvent.MouseMove and self._corner_dragging and dock is self._corner_dragging_dock:
                delta = event.globalPos() - self._corner_start
                dock.setCursor(Qt.SizeFDiagCursor)
                if getattr(self, "_corner_current_dock", None) is None:
                    self._update_drag_indicator(event.globalPos())
                    if abs(delta.x()) > 5 or abs(delta.y()) > 5:
                        if abs(delta.y()) >= abs(delta.x()):
                            self._split_orientation = Qt.Vertical
                        else:
                            self._split_orientation = Qt.Horizontal
                        self._split_preview = self._start_split_preview(dock)
                        self._begin_live_split(dock, delta)
                if self._corner_current_dock:
                    self._update_live_split(dock, delta)
                elif self._split_preview:
                    func = getattr(self, "_update_split_preview", None)
                    if func:
                        func(dock, delta)
                return True
            elif event.type() == QEvent.MouseButtonRelease and self._corner_dragging and dock is self._corner_dragging_dock:
                delta = event.globalPos() - self._corner_start
                if self._corner_current_dock:
                    self._update_live_split(dock, delta)
                    if self._split_preview:
                        self._split_preview.hide()
                        self._split_preview.deleteLater()
                        self._split_preview = None
                    new_dock = self._corner_current_dock
                    self._corner_current_dock = None
                    size = new_dock.width() if self._split_orientation == Qt.Horizontal else new_dock.height()
                    header = self.dock_headers.get(new_dock)
                    min_size = self.MIN_DOCK_SIZE
                    if size <= min_size:
                        self._collapse_dock(new_dock, self._split_orientation)
                    else:
                        if self._split_orientation == Qt.Horizontal:
                            dock_header = self.dock_headers.get(dock)
                            if dock_header:
                                dock.setMinimumWidth(self.MIN_DOCK_SIZE)
                        else:
                            dock_header = self.dock_headers.get(dock)
                            if dock_header:
                                dock.setMinimumHeight(self.MIN_DOCK_SIZE)
                elif self._split_preview:
                    func = getattr(self, "_update_split_preview", None)
                    if func:
                        func(dock, delta)
                    self._split_preview.hide()
                    self._split_preview.deleteLater()
                    self._split_preview = None
                    self._split_current_dock(dock, delta)
                elif abs(delta.x()) > 5 or abs(delta.y()) > 5:
                    if abs(delta.y()) >= abs(delta.x()):
                        self._split_orientation = Qt.Vertical
                    else:
                        self._split_orientation = Qt.Horizontal
                    self._split_current_dock(dock, delta)
                self._corner_dragging = False
                self._corner_dragging_dock = None
                self._hide_drag_indicator()
                dock.unsetCursor()
                return True
        return super().eventFilter(obj, event)


    def _apply_handle_settings(self):
        from ..shapes import ResizableMixin

        ResizableMixin.handle_size = self.handle_size
        ResizableMixin.rotation_offset = self.rotation_offset
        ResizableMixin.handle_color = self.handle_color
        ResizableMixin.rotation_handle_color = self.rotation_handle_color
        ResizableMixin.handle_shape = "circle"
        ResizableMixin.rotation_handle_shape = "circle"

    def show_status(self, text: str):
        """Display a temporary status message in the menu bar."""
        from PyQt5.QtCore import QTimer

        self.save_status.setText(text)
        self.save_status.show()
        if self._status_timer:
            self._status_timer.stop()
        self._status_timer = QTimer.singleShot(2000, self.save_status.hide)

    def _set_project_actions_enabled(self, enabled: bool):
        for name in (
            "save",
            "saveas",
            "export_image",
            "export_svg",
            "export_pdf",
            "export_code",
            "project_props",
        ):
            if name in self.actions:
                self.actions[name].setEnabled(enabled)
    def _show_drag_indicator(self, gpos):
        pos = self.mapFromGlobal(gpos)
        self.drag_indicator.move(pos.x() + 5, pos.y() + 5)
        self.drag_indicator.show()
        self.drag_indicator.raise_()
    def _update_drag_indicator(self, gpos):
        if self.drag_indicator.isVisible():
            pos = self.mapFromGlobal(gpos)
            self.drag_indicator.move(pos.x() + 5, pos.y() + 5)
            self.drag_indicator.raise_()

    def _hide_drag_indicator(self):
        self.drag_indicator.hide()

    def _start_split_preview(self, dock):
        """Create a floating widget to preview the future dock."""
        preview = QWidget(self)
        preview.setObjectName("split_preview")
        preview.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        preview.setAttribute(Qt.WA_TransparentForMouseEvents)

        tl = dock.mapTo(self, dock.rect().topLeft())
        preview.setGeometry(tl.x(), tl.y(), dock.width(), dock.height())

        new_area = QWidget(preview)
        new_area.setObjectName("split_new")
        new_area.setStyleSheet("background: rgba(255,255,255,128); border: 1px dashed gray;")
        old_area = QWidget(preview)
        old_area.setObjectName("split_old")
        old_area.setStyleSheet("background: rgba(255,255,255,128); border: 1px dashed gray;")
        preview.new_area = new_area
        preview.old_area = old_area
        new_area.show()
        old_area.show()
        preview.show()
        preview.raise_()
        return preview

    def _collapse_dock(self, dock, orientation):
        dock._collapsed = True
        dock._collapse_orientation = orientation
        if orientation == Qt.Horizontal:
            dock._restore_size = dock.width()
        else:
            dock._restore_size = dock.height()
        if dock.widget():
            dock.widget().hide()
        size = self.MIN_DOCK_SIZE
        if orientation == Qt.Horizontal:
            dock.setMinimumWidth(size)
            dock.setMaximumWidth(size)
            dock.resize(size, dock.height())
        else:
            dock.setMinimumHeight(size)
            dock.setMaximumHeight(size)
            dock.resize(dock.width(), size)
        header = self.dock_headers.get(dock)
        if header:
            header.show_handle(False)
            header.set_collapsed(True)
            header._position_handle()

    def _expand_dock(self, dock):
        orientation = getattr(dock, "_collapse_orientation", Qt.Horizontal)
        min_size = self.MIN_DOCK_SIZE
        if orientation == Qt.Horizontal:
            dock.setMinimumWidth(self.MIN_DOCK_SIZE)
            dock.setMaximumWidth(QWIDGETSIZE_MAX)
            restore = max(min_size, getattr(dock, "_restore_size", self.default_dock_size))
            dock.resize(restore, dock.height())
        else:
            dock.setMinimumHeight(self.MIN_DOCK_SIZE)
            dock.setMaximumHeight(QWIDGETSIZE_MAX)
            restore = max(min_size, getattr(dock, "_restore_size", self.default_dock_size))
            dock.resize(dock.width(), restore)
        if dock.widget():
            dock.widget().show()
        dock._collapsed = False
        header = self.dock_headers.get(dock)
        if header:
            header.show_handle(True)
            header.set_collapsed(False)
            header._position_handle()

    def _toggle_dock(self, dock):
        if getattr(dock, "_collapsed", False):
            self._expand_dock(dock)
        else:
            # Always collapse vertically so only the header remains visible
            self._collapse_dock(dock, Qt.Vertical)

    def show_corner_tabs(self):
        """Display a floating tab selector near the cursor."""
        if not self.corner_tabs:
            self.corner_tabs = CornerTabs(self, overlay=True)
        pos = self.mapFromGlobal(QCursor.pos())
        self.corner_tabs.move(pos.x(), pos.y())
        self.corner_tabs.show()
        self.corner_tabs.raise_()

    def _animate_new_dock(self, dock, orientation, delta):
        """Animate ``dock`` growing from the drag start."""
        end_geom = dock.geometry()
        if orientation == Qt.Horizontal:
            if delta.x() >= 0:
                start = QRect(end_geom.left(), end_geom.top(), 1, end_geom.height())
            else:
                start = QRect(end_geom.right() - 1, end_geom.top(), 1, end_geom.height())
        else:
            if delta.y() >= 0:
                start = QRect(end_geom.left(), end_geom.top(), end_geom.width(), 1)
            else:
                start = QRect(end_geom.left(), end_geom.bottom() - 1, end_geom.width(), 1)
        dock.setGeometry(start)
        dock.show()
        anim = QPropertyAnimation(dock, b"geometry", self)
        anim.setDuration(150)
        anim.setStartValue(start)
        anim.setEndValue(end_geom)
        if not hasattr(self, "_animations"):
            self._animations = []
        self._animations.append(anim)

        def cleanup():
            if anim in self._animations:
                self._animations.remove(anim)

        anim.finished.connect(cleanup)
        anim.start()

    def _begin_live_split(self, dock, delta):
        """Create a new dock at minimal size for live resizing."""
        label = dock.windowTitle()
        header = self.dock_headers.get(dock)
        if header:
            label = header.selector.currentText()
        area = self.dockWidgetArea(dock)
        # record the size before inserting the new dock so limits stay stable
        start_size = dock.width() if self._split_orientation == Qt.Horizontal else dock.height()
        header = self.dock_headers.get(dock)
        header_size = self.MIN_DOCK_SIZE
        new_dock = self._create_dock(label, area)
        new_dock.hide()
        if self._split_orientation == Qt.Horizontal:
            new_dock.setMinimumWidth(header_size)
            new_dock.setMaximumWidth(max(header_size, start_size - header_size))
            dock.setMinimumWidth(start_size)
            dock.setMaximumWidth(start_size)
            if delta.x() >= 0:
                self.splitDockWidget(dock, new_dock, Qt.Horizontal)
                self.resizeDocks([dock, new_dock], [start_size, 1], Qt.Horizontal)
            else:
                self.splitDockWidget(new_dock, dock, Qt.Horizontal)
                self.resizeDocks([new_dock, dock], [1, start_size], Qt.Horizontal)
        else:
            new_dock.setMinimumHeight(header_size)
            new_dock.setMaximumHeight(max(header_size, start_size - header_size))
            dock.setMinimumHeight(start_size)
            dock.setMaximumHeight(start_size)
            if delta.y() >= 0:
                self.splitDockWidget(dock, new_dock, Qt.Vertical)
                self.resizeDocks([dock, new_dock], [start_size, 1], Qt.Vertical)
            else:
                self.splitDockWidget(new_dock, dock, Qt.Vertical)
                self.resizeDocks([new_dock, dock], [1, start_size], Qt.Vertical)
        new_dock.show()
        self._corner_current_dock = new_dock
        self._split_start_size = start_size

    def _update_live_split(self, dock, delta):
        """Resize the newly created dock while dragging."""
        new_dock = self._corner_current_dock
        if not new_dock:
            return
        # size constraints are based on the original dock header
        header = self.dock_headers.get(dock)
        if self._split_orientation == Qt.Horizontal:
            header_size = self.MIN_DOCK_SIZE
            min_size = header_size
            total = self._split_start_size
            max_size = total - header_size
            size = max(min_size, min(abs(delta.x()), max_size))
            if delta.x() >= 0:
                self.resizeDocks([dock, new_dock], [total - size, size], Qt.Horizontal)
            else:
                self.resizeDocks([new_dock, dock], [size, total - size], Qt.Horizontal)
        else:
            header_size = self.MIN_DOCK_SIZE
            min_size = header_size
            total = self._split_start_size
            max_size = total - header_size
            size = max(min_size, min(abs(delta.y()), max_size))
            if delta.y() >= 0:
                self.resizeDocks([dock, new_dock], [total - size, size], Qt.Vertical)
            else:
                self.resizeDocks([new_dock, dock], [size, total - size], Qt.Vertical)
        preview = self._split_preview
        if preview:
            func = getattr(self, "_update_split_preview", None)
            if func:
                func(dock, delta)



    def _split_current_dock(self, dock, delta):
        """Create a new dock based on the drag delta."""
        label = dock.windowTitle()
        header = self.dock_headers.get(dock)
        if header:
            label = header.selector.currentText()
        area = self.dockWidgetArea(dock)
        new_dock = self._create_dock(label, area)
        new_dock.hide()
        header = self.dock_headers.get(dock)
        try:
            if self._split_orientation == Qt.Horizontal:
                min_size = self.MIN_DOCK_SIZE
                size = max(min_size, min(abs(delta.x()), dock.width() - min_size))
                if delta.x() >= 0:
                    self.splitDockWidget(dock, new_dock, Qt.Horizontal)
                    self.resizeDocks([dock, new_dock], [dock.width() - size, size], Qt.Horizontal)
                else:
                    self.splitDockWidget(new_dock, dock, Qt.Horizontal)
                    self.resizeDocks([new_dock, dock], [size, dock.width() - size], Qt.Horizontal)
            else:
                min_size = self.MIN_DOCK_SIZE
                size = max(min_size, min(abs(delta.y()), dock.height() - min_size))
                if delta.y() >= 0:
                    self.splitDockWidget(dock, new_dock, Qt.Vertical)
                    self.resizeDocks([dock, new_dock], [dock.height() - size, size], Qt.Vertical)
                else:
                    self.splitDockWidget(new_dock, dock, Qt.Vertical)
                    self.resizeDocks([new_dock, dock], [size, dock.height() - size], Qt.Vertical)
        except Exception:
            pass
        self._animate_new_dock(new_dock, self._split_orientation, delta)
        header_new = self.dock_headers.get(new_dock)
        min_size = self.MIN_DOCK_SIZE
        if size <= min_size:
            self._collapse_dock(new_dock, self._split_orientation)

    def set_dock_category(self, dock, label):
        widget = self.category_widgets.get(label)
        if not widget:
            return
        current = self.dock_current_widget.get(dock)
        if current is widget:
            return
        # remove from previous dock
        prev = self.widget_docks.get(widget)
        if prev and prev is not dock:
            cont = prev.widget()
            lay = cont.layout()
            if lay.count():
                old = lay.itemAt(0).widget()
                if old is widget:
                    old.setParent(None)
            self.dock_current_widget[prev] = None
        # insert into new dock
        cont = dock.widget()
        lay = cont.layout()
        if lay.count():
            old = lay.itemAt(0).widget()
            if old:
                old.setParent(None)
        lay.insertWidget(0, widget)
        self.widget_docks[widget] = dock
        self.dock_current_widget[dock] = widget
        dock.setWindowTitle(label)
        header = self.dock_headers.get(dock)
        if header:
            header.selector.blockSignals(True)
            header.selector.setCurrentText(label)
            header.selector.blockSignals(False)

    # --- Gestion favoris et récents ------------------------------------
    def add_recent_project(self, path: str):
        if path in self.recent_projects:
            self.recent_projects.remove(path)
        self.recent_projects.insert(0, path)
        self.recent_projects = self.recent_projects[:10]
        self.settings.setValue("recent_projects", self.recent_projects)

    def toggle_favorite_project(self, path: str):
        if path in self.favorite_projects:
            self.favorite_projects.remove(path)
        else:
            self.favorite_projects.insert(0, path)
        self.settings.setValue("favorite_projects", self.favorite_projects)

    def add_imported_image(self, path: str):
        if path in self.imported_images:
            self.imported_images.remove(path)
        self.imported_images.insert(0, path)
        self.settings.setValue("imported_images", self.imported_images)
        self.imports.add_image(path)

    def add_template_project(self, path: str):
        if path in self.template_projects:
            self.template_projects.remove(path)
        self.template_projects.insert(0, path)
        self.settings.setValue("template_projects", self.template_projects)

    # --- window resizing -------------------------------------------------
    def _edges_at_pos(self, pos):
        rect = self.rect()
        edges = Qt.Edges()
        if pos.x() <= self.EDGE_MARGIN:
            edges |= Qt.LeftEdge
        if pos.x() >= rect.width() - self.EDGE_MARGIN:
            edges |= Qt.RightEdge
        if pos.y() <= self.EDGE_MARGIN:
            edges |= Qt.TopEdge
        if pos.y() >= rect.height() - self.EDGE_MARGIN:
            edges |= Qt.BottomEdge
        return edges

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edges = self._edges_at_pos(event.pos())
            if (
                not edges
                and event.pos().x() >= self.width() - self.CORNER_REGION
                and event.pos().y() >= self.height() - self.CORNER_REGION
            ):
                self._corner_dragging = True
                self._corner_start = event.pos()
                # Indicate that dragging the corner will affect layout
                self.setCursor(Qt.SizeFDiagCursor)
                return
            if edges:
                handle = self.windowHandle()
                if handle and hasattr(handle, "startSystemResize"):
                    handle.startSystemResize(edges)
                    self._resizing = True
                    # show the cursor used by the system resize so the user
                    # knows resizing has started
                    if edges == (Qt.LeftEdge | Qt.TopEdge) or edges == (
                        Qt.RightEdge | Qt.BottomEdge
                    ):
                        cursor = Qt.SizeFDiagCursor
                    elif edges == (Qt.RightEdge | Qt.TopEdge) or edges == (
                        Qt.LeftEdge | Qt.BottomEdge
                    ):
                        cursor = Qt.SizeBDiagCursor
                    elif edges & (Qt.LeftEdge | Qt.RightEdge):
                        cursor = Qt.SizeHorCursor
                    else:
                        cursor = Qt.SizeVerCursor
                    self.setCursor(cursor)
                    return
                self._resizing = True
                self._resize_edges = edges
                self._start_pos = event.globalPos()
                self._start_geom = self.geometry()
                # Apply a resize cursor immediately
                if edges == (Qt.LeftEdge | Qt.TopEdge) or edges == (
                    Qt.RightEdge | Qt.BottomEdge
                ):
                    cursor = Qt.SizeFDiagCursor
                elif edges == (Qt.RightEdge | Qt.TopEdge) or edges == (
                    Qt.LeftEdge | Qt.BottomEdge
                ):
                    cursor = Qt.SizeBDiagCursor
                elif edges & (Qt.LeftEdge | Qt.RightEdge):
                    cursor = Qt.SizeHorCursor
                else:
                    cursor = Qt.SizeVerCursor
                self.setCursor(cursor)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._corner_dragging:
            delta = event.pos() - self._corner_start
            # Keep a diagonal resize cursor during the drag so the user
            # knows the action will modify the layout.
            self.setCursor(Qt.SizeFDiagCursor)
            if abs(delta.x()) > 5 or abs(delta.y()) > 5:
                self.show_corner_tabs()
                self._corner_dragging = False
            return
        if self._resizing and (not hasattr(self.windowHandle(), "startSystemResize")):
            delta = event.globalPos() - self._start_pos
            g = self._start_geom
            left, top, width, height = g.x(), g.y(), g.width(), g.height()
            if self._resize_edges & Qt.LeftEdge:
                new_left = left + delta.x()
                width -= delta.x()
                left = new_left
            if self._resize_edges & Qt.RightEdge:
                width += delta.x()
            if self._resize_edges & Qt.TopEdge:
                new_top = top + delta.y()
                height -= delta.y()
                top = new_top
            if self._resize_edges & Qt.BottomEdge:
                height += delta.y()
            self.setGeometry(left, top, max(width, self.minimumWidth()), max(height, self.minimumHeight()))
        else:
            edges = self._edges_at_pos(event.pos())
            cursor = Qt.ArrowCursor
            if edges == (Qt.LeftEdge | Qt.TopEdge) or edges == (Qt.RightEdge | Qt.BottomEdge):
                cursor = Qt.SizeFDiagCursor
            elif edges == (Qt.RightEdge | Qt.TopEdge) or edges == (Qt.LeftEdge | Qt.BottomEdge):
                cursor = Qt.SizeBDiagCursor
            elif edges & (Qt.LeftEdge | Qt.RightEdge):
                cursor = Qt.SizeHorCursor
            elif edges & (Qt.TopEdge | Qt.BottomEdge):
                cursor = Qt.SizeVerCursor
            self.setCursor(cursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._corner_dragging:
            delta = event.pos() - self._corner_start
            if abs(delta.x()) > 5 or abs(delta.y()) > 5:
                self.show_corner_tabs()
            self._corner_dragging = False
            self.unsetCursor()
            return
        self._resizing = False
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        """Reset cursor when leaving the window."""
        if not self._resizing and not self._corner_dragging:
            self.unsetCursor()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)


def main(app, argv):
    win = MainWindow()
    win.show()
    return app.exec_()
