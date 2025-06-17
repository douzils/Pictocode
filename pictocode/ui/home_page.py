# pictocode/ui/home_page.py

import os
import json
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QStyle,
    QMenu,
)
from PyQt5.QtCore import Qt


class HomePage(QWidget):
    """
    Page d’accueil :
    - Affiche la liste des projets existants (scan du dossier ./Projects)
    - Bouton « Nouveau projet »
    - Double-clic sur un projet pour l’ouvrir
    """

    PROJECTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Projects")

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Crée le dossier s’il n’existe pas
        os.makedirs(self.PROJECTS_DIR, exist_ok=True)

        self.setObjectName("home")
        # Layout principal
        vbox = QVBoxLayout(self)

        title = QLabel("🎨 Bienvenue sur Pictocode")
        title.setObjectName("title_label")
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        subtitle = QLabel("Créez et gérez vos projets graphiques")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("subtitle_label")
        vbox.addWidget(subtitle)

        # Liste des favoris
        fav_label = QLabel("Projets favoris")
        fav_label.setObjectName("section_label")
        vbox.addWidget(fav_label)
        self.fav_list = QListWidget()
        self.fav_list.setObjectName("favorites_list")
        self.fav_list.itemDoubleClicked.connect(self._on_project_double_click)
        self.fav_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.fav_list.customContextMenuRequested.connect(self._on_fav_menu)
        vbox.addWidget(self.fav_list)

        # Liste des projets récents
        recent_label = QLabel("Projets récents")
        recent_label.setObjectName("section_label")
        vbox.addWidget(recent_label)
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recent_list")
        self.recent_list.itemDoubleClicked.connect(self._on_project_double_click)
        self.recent_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_list.customContextMenuRequested.connect(self._on_recent_menu)
        vbox.addWidget(self.recent_list)

        # Liste des modèles (très simple)
        tmpl_label = QLabel("Modèles")
        tmpl_label.setObjectName("section_label")
        vbox.addWidget(tmpl_label)
        self.template_list = QListWidget()
        self.template_list.setObjectName("template_list")
        self.template_list.addItem("A4 Portrait (210×297 mm)")
        self.template_list.addItem("A4 Paysage (297×210 mm)")
        self.template_list.addItem("HD 1080p (1920×1080 px)")
        self.template_list.itemDoubleClicked.connect(self._on_template_double_click)
        vbox.addWidget(self.template_list)

        # Remplit les listes au démarrage
        self.populate_lists()

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget#home {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #374ABE, stop:1 #64B6FF);
            }
            QLabel#title_label {
                font-size: 26px;
                font-weight: bold;
                color: white;
                padding: 20px;
            }
            QLabel#subtitle_label {
                font-size: 16px;
                color: white;
                padding-bottom: 16px;
            }
            QListWidget#favorites_list,
            QListWidget#recent_list,
            QListWidget#template_list {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 10px;
                padding: 8px;
            }
            QListWidget#template_list {
                margin-top: 12px;
            }
            QListWidget#favorites_list::item,
            QListWidget#recent_list::item {
                padding: 8px;
            }
            QLabel#section_label {
                color: white;
                font-weight: bold;
                margin-top: 12px;
            }
            """
        )

    def populate_lists(self):
        self._populate_list(self.fav_list, self.parent.favorite_projects, "(Aucun favori)")
        self._populate_list(self.recent_list, self.parent.recent_projects, "(Aucun projet récent)")

    def _populate_list(self, widget: QListWidget, paths: list, empty_text: str):
        widget.clear()
        style = self.style()
        icon = style.standardIcon(QStyle.SP_FileIcon)
        valid = []
        for path in paths:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                display = meta.get("name", os.path.basename(path)[:-5])
            except Exception:
                display = os.path.basename(path)[:-5]
            item = QListWidgetItem(icon, display)
            item.setData(Qt.UserRole, path)
            widget.addItem(item)
            valid.append(path)
        if widget.count() == 0:
            widget.addItem(empty_text)
        return valid

    def _on_project_double_click(self, item: QListWidgetItem):
        """Ouvre le projet sélectionné."""
        path = item.data(Qt.UserRole)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Erreur", "Impossible de trouver le projet.")
            return

        # Charge les paramètres depuis le JSON
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de lecture de {path} :\n{e}")
            return

        # Sépare métadonnées et formes
        params = {
            k: data.get(k)
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

        # Appelle MainWindow pour ouvrir le projet
        self.parent.open_project(path, params, shapes)

    def _on_template_double_click(self, item: QListWidgetItem):
        """Pré-remplit le dialogue de nouveau projet avec un modèle."""
        text = item.text()
        dlg = self.parent.new_proj_dlg
        if "A4" in text:
            dlg.width_spin.setValue(210 if "Portrait" in text else 297)
            dlg.height_spin.setValue(297 if "Portrait" in text else 210)
            dlg.unit_combo.setCurrentText("mm")
            dlg.orient_combo.setCurrentText(
                "Portrait" if "Portrait" in text else "Paysage"
            )
        elif "1080p" in text:
            dlg.width_spin.setValue(1920)
            dlg.height_spin.setValue(1080)
            dlg.unit_combo.setCurrentText("px")
            dlg.orient_combo.setCurrentText("Paysage")
        dlg.open()

    def _on_recent_menu(self, pos):
        item = self.recent_list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.UserRole)
        menu = QMenu(self)
        if path in self.parent.favorite_projects:
            act = menu.addAction("Retirer des favoris")
        else:
            act = menu.addAction("Ajouter aux favoris")
        if menu.exec_(self.recent_list.mapToGlobal(pos)) == act:
            self.parent.toggle_favorite_project(path)
            self.populate_lists()

    def _on_fav_menu(self, pos):
        item = self.fav_list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.UserRole)
        menu = QMenu(self)
        act = menu.addAction("Retirer des favoris")
        if menu.exec_(self.fav_list.mapToGlobal(pos)) == act:
            self.parent.toggle_favorite_project(path)
            self.populate_lists()
