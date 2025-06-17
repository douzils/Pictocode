# pictocode/ui/new_project_dialog.py

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau projet")
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        main_layout.addLayout(form)

        # — Nom du projet —
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Mon super projet")
        form.addRow("Nom du projet :", self.name_edit)

        # — Largeur —
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(800)
        form.addRow("Largeur :", self.width_spin)

        # — Hauteur —
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(800)
        form.addRow("Hauteur :", self.height_spin)

        # — Unité —
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["px", "pt", "mm", "cm", "in"])
        form.addRow("Unité :", self.unit_combo)

        # — Orientation —
        self.orient_combo = QComboBox()
        self.orient_combo.addItems(["Portrait", "Paysage"])
        form.addRow("Orientation :", self.orient_combo)

        # — Mode couleur —
        self.color_combo = QComboBox()
        self.color_combo.addItems(["RGB", "CMJN", "Niveaux de gris"])
        form.addRow("Mode couleur :", self.color_combo)

        # — Résolution DPI —
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(1, 1200)
        self.dpi_spin.setValue(72)
        form.addRow("Résolution (DPI) :", self.dpi_spin)

        # Boutons OK / Annuler
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_parameters(self) -> dict:
        """
        Retourne tous les paramètres, y compris le nom.
        """
        return {
            "name": self.name_edit.text().strip(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "unit": self.unit_combo.currentText(),
            "orientation": (
                "portrait"
                if self.orient_combo.currentText() == "Portrait"
                else "landscape"
            ),
            "color_mode": self.color_combo.currentText(),
            "dpi": self.dpi_spin.value(),
        }
