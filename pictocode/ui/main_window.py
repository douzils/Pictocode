# pictocode/ui/main_window.py
import os, json
from PyQt5.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QMenuBar,
    QAction,
    QFileDialog,
    QMessageBox,
    QDialog,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import Qt, QSettings, QPropertyAnimation
from PyQt5.QtGui import QPalette, QColor, QKeySequence
from PyQt5.QtWidgets import QApplication
from ..utils import generate_pycode
from ..canvas import CanvasWidget
from .toolbar import Toolbar
from .title_bar import TitleBar
from .inspector import Inspector
from .home_page import HomePage
from .new_project_dialog import NewProjectDialog
from .animated_menu import AnimatedMenu
from .shortcut_settings_dialog import ShortcutSettingsDialog

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Projects")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
        self.menu_bar = QMenuBar(self._menu_container)
        _ml.addWidget(self.menu_bar)
        self.setMenuWidget(self._menu_container)

        # Page accueil
        self.home = HomePage(self)
        self.stack.addWidget(self.home)

        # Page canvas
        self.canvas = CanvasWidget(self)
        container = self.canvas
        self.stack.addWidget(container)

        # Toolbar & inspecteur (cachés par défaut)
        self.toolbar = Toolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setVisible(False)

        self.inspector = Inspector(self)
        dock = QDockWidget("Inspecteur", self)
        dock.setWidget(self.inspector)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        dock.setVisible(False)
        self.inspector_dock = dock

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
            "duplicate": "Ctrl+D",
            "delete": "Delete",
            "select_all": "Ctrl+A",
            "zoom_in": "Ctrl++",
            "zoom_out": "Ctrl+-",
            "toggle_grid": "Ctrl+G",
            "toggle_snap": "Ctrl+Shift+G",
        }

        # Connexions
        self.home.new_btn.clicked.connect(self.open_new_project_dialog)

        # état courant
        self.current_project_path = None
        self.unsaved_changes = False
        self._current_anim = None

        # Paramètres de l'application
        self.settings = QSettings("pictocode", "pictocode")
        self.current_theme = self.settings.value("theme", "Light")
        self.accent_color = QColor(self.settings.value("accent_color", "#2a82da"))
        self.font_size = int(self.settings.value("font_size", 10))
        self.menu_color = QColor(
            self.settings.value("menu_color", self.accent_color.name())
        )
        self.toolbar_color = QColor(
            self.settings.value("toolbar_color", self.accent_color.name())
        )
        self.dock_color = QColor(
            self.settings.value("dock_color", self.accent_color.name())
        )
        self.menu_font_size = int(self.settings.value("menu_font_size", self.font_size))
        self.toolbar_font_size = int(
            self.settings.value("toolbar_font_size", self.font_size)
        )
        self.dock_font_size = int(self.settings.value("dock_font_size", self.font_size))
        self.show_splash = self.settings.value("show_splash", True, type=bool)
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
        )
        self._load_shortcuts()

    def _build_menu(self):
        mb = self.menu_bar
        from .animated_menu import AnimatedMenu

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

        dup_act = QAction("Dupliquer", self)
        dup_act.triggered.connect(self.duplicate_selection)
        editm.addAction(dup_act)
        self.actions["duplicate"] = dup_act

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

        prefm = AnimatedMenu("Préférences", self)
        mb.addMenu(prefm)
        app_act = QAction("Apparence…", self)
        app_act.triggered.connect(self.open_app_settings)
        prefm.addAction(app_act)
        self.actions["appearance"] = app_act

        short_act = QAction("Raccourcis…", self)
        short_act.triggered.connect(self.open_shortcut_settings)
        prefm.addAction(short_act)
        self.actions["shortcuts"] = short_act

    # ─── Gestion de l'état modifié ─────────────────────────────
    def set_dirty(self, value: bool = True):
        self.unsaved_changes = value
        title = self.windowTitle().lstrip("* ").strip()
        if value:
            self.setWindowTitle("* " + title)
        else:
            self.setWindowTitle(title)

    def maybe_save(self) -> bool:
        if not self.unsaved_changes:
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

        # affiche toolbar & inspector
        self.toolbar.setVisible(True)
        self.inspector_dock.setVisible(True)
        # bascule sur le canvas
        self._switch_page(self.canvas)
        self.current_project_path = None
        self.set_dirty(False)

    def _on_file_open(self):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un projet", PROJECTS_DIR, "Pictocode (*.json)"
        )
        if path:
            try:
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
                self.open_project(path, params, data.get("shapes", []))
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir : {e}")

    def open_project(self, path, params, shapes=None):
        """Charge un projet existant (optionnellement avec formes)."""
        if not self.maybe_save():
            return
        self.current_project_path = path
        # crée document
        self.canvas.new_document(**params)
        # charge formes
        self.canvas.load_shapes(shapes or [])
        # bascule UI
        self.toolbar.setVisible(True)
        self.inspector_dock.setVisible(True)
        self._switch_page(self.canvas)
        self.setWindowTitle(f"Pictocode — {params.get('name','')}")
        self.set_dirty(False)

    def save_project(self):
        if not self.current_project_path:
            return self.save_as_project()
        data = self.canvas.export_project()
        try:
            with open(self.current_project_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.set_dirty(False)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer : {e}")

    def save_as_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer sous", PROJECTS_DIR, "Pictocode (*.json)"
        )
        if path:
            if not path.endswith(".json"):
                path += ".json"
            self.current_project_path = path
            self.save_project()
            self.setWindowTitle(f"Pictocode — {os.path.basename(path)[:-5]}")

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
                QMessageBox.critical(self, "Erreur", f"Impossible d'exporter : {e}")

    def back_to_home(self):
        if not self.maybe_save():
            return
        self._switch_page(self.home)
        self.toolbar.setVisible(False)
        self.inspector_dock.setVisible(False)

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

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    # ------------------------------------------------------------------
    def open_app_settings(self):
        from .app_settings_dialog import AppSettingsDialog

        dlg = AppSettingsDialog(
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
            )
            self.settings.setValue("show_splash", self.show_splash)

    def open_shortcut_settings(self):
        current = {
            name: act.shortcut().toString() for name, act in self.actions.items()
        }
        dlg = ShortcutSettingsDialog(current, self)
        if dlg.exec_() == QDialog.Accepted:
            values = dlg.get_shortcuts()
            for name, seq in values.items():
                action = self.actions.get(name)
                if action is not None:
                    action.setShortcut(QKeySequence(seq))
                    self.settings.setValue(f"shortcut_{name}", seq)

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
    ):
        """Applique un thème clair ou sombre ainsi que des réglages personnalisés."""
        app = QApplication.instance()
        accent = accent or self.accent_color
        font_size = font_size or self.font_size
        menu_color = menu_color or self.menu_color
        toolbar_color = toolbar_color or self.toolbar_color
        dock_color = dock_color or self.dock_color
        menu_font_size = menu_font_size or self.menu_font_size
        toolbar_font_size = toolbar_font_size or self.toolbar_font_size
        dock_font_size = dock_font_size or self.dock_font_size

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
            pal.setColor(QPalette.HighlightedText, Qt.black)
            app.setPalette(pal)
            app.setStyle("Fusion")
        else:
            pal = app.style().standardPalette()
            pal.setColor(QPalette.Highlight, accent)
            app.setPalette(pal)
            app.setStyle("Fusion")

        font = app.font()
        font.setPointSize(int(font_size))
        app.setFont(font)

        self.setStyleSheet(
            f"QToolBar {{ background: {toolbar_color.name()}; color: white; font-size: {toolbar_font_size}pt; }}\n"
            f"QMenuBar {{ background: {menu_color.name()}; color: white; font-size: {menu_font_size}pt; border-radius: 4px; }}\n"
            f"QWidget#title_bar {{ background: {toolbar_color.name()}; color: white; font-size: {toolbar_font_size}pt; }}\n"
            f"QWidget#title_bar QPushButton {{ border: none; background: transparent; color: white; padding: 4px; }}\n"
            f"QWidget#title_bar QPushButton:hover {{ background: {toolbar_color.darker(110).name()}; }}\n"
            f"QMenuBar::item:selected {{ background: {menu_color.darker(120).name()}; }}\n"
            f"QMenu {{ background-color: {menu_color.name()}; color: white; border-radius: 6px; }}\n"
            f"QMenu::item:selected {{ background-color: {menu_color.darker(130).name()}; }}"
        )
        self.inspector_dock.setStyleSheet(
            f"QDockWidget {{ background: {dock_color.name()}; }}"
        )
        self.inspector.setStyleSheet(f"font-size: {dock_font_size}pt;")

        self.current_theme = theme
        self.accent_color = accent
        self.font_size = font_size
        self.menu_color = menu_color
        self.toolbar_color = toolbar_color
        self.dock_color = dock_color
        self.menu_font_size = menu_font_size
        self.toolbar_font_size = toolbar_font_size
        self.dock_font_size = dock_font_size
        self.settings.setValue("theme", theme)
        self.settings.setValue("accent_color", accent.name())
        self.settings.setValue("font_size", font_size)
        self.settings.setValue("menu_color", menu_color.name())
        self.settings.setValue("toolbar_color", toolbar_color.name())
        self.settings.setValue("dock_color", dock_color.name())
        self.settings.setValue("menu_font_size", menu_font_size)
        self.settings.setValue("toolbar_font_size", toolbar_font_size)
        self.settings.setValue("dock_font_size", dock_font_size)

    def _load_shortcuts(self):
        self.actions = getattr(self, "actions", {})
        for name, action in self.actions.items():
            seq = self.settings.value(
                f"shortcut_{name}", self.default_shortcuts.get(name, "")
            )
            if seq:
                action.setShortcut(QKeySequence(seq))


def main(app, argv):
    win = MainWindow()
    win.show()
    return app.exec_()
