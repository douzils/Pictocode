# pictocode/ui/main_window.py
import os, json
from PyQt5.QtWidgets import (
    QMainWindow, QDockWidget, QStackedWidget, QWidget,
    QAction, QFileDialog, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication

from ..canvas import CanvasWidget
from .toolbar import Toolbar
from .inspector import Inspector
from .home_page import HomePage
from .new_project_dialog import NewProjectDialog

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Projects")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Pictocode')
        self.resize(1024, 768)

        # crée dossier projects
        os.makedirs(PROJECTS_DIR, exist_ok=True)

        # Stack home ↔ document
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

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

        # Connexions
        self.home.new_btn.clicked.connect(self.open_new_project_dialog)

        # état courant
        self.current_project_path = None
        self.unsaved_changes = False

        # Paramètres de l'application
        self.settings = QSettings("pictocode", "pictocode")
        self.current_theme = self.settings.value("theme", "Light")

        self.accent_color = QColor(self.settings.value("accent_color", "#2a82da"))
        self.font_size = int(self.settings.value("font_size", 10))
        self.apply_theme(self.current_theme, self.accent_color, self.font_size)


    def _build_menu(self):
        mb = self.menuBar()
        filem = mb.addMenu("Fichier")

        new_act = QAction("Nouveau…", self)
        new_act.triggered.connect(self.open_new_project_dialog)
        filem.addAction(new_act)

        open_act = QAction("Ouvrir…", self)
        open_act.triggered.connect(self._on_file_open)
        filem.addAction(open_act)

        filem.addSeparator()

        save_act = QAction("Enregistrer", self)
        save_act.triggered.connect(self.save_project)
        filem.addAction(save_act)

        saveas_act = QAction("Enregistrer sous…", self)
        saveas_act.triggered.connect(self.save_as_project)
        filem.addAction(saveas_act)

        export_img_act = QAction("Exporter en image…", self)
        export_img_act.triggered.connect(self.export_image)
        filem.addAction(export_img_act)

        export_svg_act = QAction("Exporter en SVG…", self)
        export_svg_act.triggered.connect(self.export_svg)
        filem.addAction(export_svg_act)

        export_code_act = QAction("Exporter en code Python…", self)
        export_code_act.triggered.connect(self.export_pycode)
        filem.addAction(export_code_act)

        filem.addSeparator()

        home_act = QAction("Accueil", self)
        home_act.triggered.connect(self.back_to_home)
        filem.addAction(home_act)

        exit_act = QAction("Quitter", self)
        exit_act.triggered.connect(self.close)
        filem.addAction(exit_act)

        projectm = mb.addMenu("Projet")
        props_act = QAction("Paramètres…", self)
        props_act.triggered.connect(self.open_project_settings)
        projectm.addAction(props_act)

        prefm = mb.addMenu("Préférences")
        app_act = QAction("Apparence…", self)
        app_act.triggered.connect(self.open_app_settings)
        prefm.addAction(app_act)

    # ─── Gestion de l'état modifié ─────────────────────────────
    def set_dirty(self, value: bool = True):
        self.unsaved_changes = value
        title = self.windowTitle().lstrip('* ').strip()
        if value:
            self.setWindowTitle('* ' + title)
        else:
            self.setWindowTitle(title)

    def maybe_save(self) -> bool:
        if not self.unsaved_changes:
            return True
        resp = QMessageBox.question(
            self, 'Projet non enregistré',
            'Voulez-vous enregistrer les modifications ?',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        if resp == QMessageBox.Save:
            self.save_project()
            return not self.unsaved_changes
        return resp == QMessageBox.Discard

    def open_new_project_dialog(self):
        if self.maybe_save():
            self.new_proj_dlg.open()

    def open_project_settings(self):
        if not hasattr(self.canvas, 'current_meta'):
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
        project_name = params.get('name') or "Sans titre"
        # exemple : changer le titre de la fenêtre
        self.setWindowTitle(f'Pictocode — {project_name}')

        # crée le document dans le canvas
        self.canvas.new_document(
            width=params['width'],
            height=params['height'],
            unit=params['unit'],
            orientation=params['orientation'],
            color_mode=params['color_mode'],
            dpi=params['dpi'],
            name=params.get('name', '')
        )
        
        # affiche toolbar & inspector
        self.toolbar.setVisible(True)
        self.inspector_dock.setVisible(True)
        # bascule sur le canvas
        self.stack.setCurrentWidget(self.canvas)
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
                params = {k: data[k] for k in ("name","width","height","unit","orientation","color_mode","dpi")}
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
        self.stack.setCurrentWidget(self.canvas)
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
            "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        if path:
            fmt = "PNG"
            lower = path.lower()
            if lower.endswith(".jpg") or lower.endswith(".jpeg"):
                fmt = "JPEG"
            self.canvas.export_image(path, fmt)

    def export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter comme SVG",
            PROJECTS_DIR,
            "SVG (*.svg)"
        )
        if path:
            if not path.lower().endswith('.svg'):
                path += '.svg'
            self.canvas.export_svg(path)

    def export_pycode(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter en code Python",
            PROJECTS_DIR,
            "Python (*.py)"
        )
        if path:
            if not path.lower().endswith('.py'):
                path += '.py'
            shapes = [it for it in self.canvas.scene.items() if it is not self.canvas._frame_item]
            code = generate_pycode(shapes)
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(code)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible d'exporter : {e}")

    def back_to_home(self):
        if not self.maybe_save():
            return
        self.stack.setCurrentWidget(self.home)
        self.toolbar.setVisible(False)
        self.inspector_dock.setVisible(False)

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    # ------------------------------------------------------------------
    def open_app_settings(self):
        from .app_settings_dialog import AppSettingsDialog

        dlg = AppSettingsDialog(self.current_theme, self.accent_color, self.font_size, self)
        if dlg.exec_() == QDialog.Accepted:
            theme = dlg.get_theme()
            accent = dlg.get_accent_color()
            font_size = dlg.get_font_size()
            self.apply_theme(theme, accent, font_size)
    def apply_theme(self, theme: str, accent: QColor | None = None, font_size: int | None = None):
        """Applique un thème clair ou sombre ainsi que des réglages personnels."""
        app = QApplication.instance()
        accent = accent or self.accent_color
        font_size = font_size or self.font_size

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

            pal.setColor(QPalette.Highlight, QColor(42, 130, 218))

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
            f"QToolBar {{ background: {accent.name()}; color: white; }}\n" +
            f"QMenuBar {{ background: {accent.darker(120).name()}; color: white; }}\n" +
            f"QMenuBar::item:selected {{ background: {accent.darker(140).name()}; }}"
        )

        self.current_theme = theme
        self.accent_color = accent
        self.font_size = font_size
        self.settings.setValue("theme", theme)
        self.settings.setValue("accent_color", accent.name())
        self.settings.setValue("font_size", font_size)



def main(app, argv):
    win = MainWindow()
    win.show()
    return app.exec_()
