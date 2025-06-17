# pictocode/ui/home_page.py

import os
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox, QHBoxLayout
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

        # Layout principal
        vbox = QVBoxLayout(self)
        title = QLabel("📂 Mes projets Pictocode")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        vbox.addWidget(title)

        # Liste des projets
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_project_double_click)
        vbox.addWidget(self.list_widget, 1)

        # Boutons bas
        hbox = QHBoxLayout()
        self.new_btn = QPushButton("➕ Nouveau projet")
        self.new_btn.clicked.connect(self.parent.open_new_project_dialog)
        hbox.addWidget(self.new_btn)

        self.refresh_btn = QPushButton("🔄 Rafraîchir")
        self.refresh_btn.clicked.connect(self.populate_projects)
        hbox.addWidget(self.refresh_btn)

        vbox.addLayout(hbox)

        # Remplit la liste au démarrage
        self.populate_projects()

    def populate_projects(self):
        """Scanne PROJECTS_DIR et affiche chaque projet (fichiers .json)."""
        self.list_widget.clear()
        for fname in sorted(os.listdir(self.PROJECTS_DIR)):
            if fname.endswith(".json"):
                path = os.path.join(self.PROJECTS_DIR, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    display = meta.get("name", fname[:-5])
                except Exception:
                    display = fname[:-5]
                item = QListWidgetItem(display)
                item.setData(Qt.UserRole, path)
                self.list_widget.addItem(item)
        if self.list_widget.count() == 0:
            self.list_widget.addItem("(Aucun projet trouvé)")

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
        params = {k: data.get(k) for k in (
            "name", "width", "height", "unit",
            "orientation", "color_mode", "dpi",
        )}
        shapes = data.get("shapes", [])

        # Appelle MainWindow pour ouvrir le projet
        self.parent.open_project(path, params, shapes)
