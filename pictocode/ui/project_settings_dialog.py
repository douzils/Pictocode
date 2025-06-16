from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QComboBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt

class ProjectSettingsDialog(QDialog):
    def __init__(self, params: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres du projet")
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        main_layout.addLayout(form)

        self.name_edit = QLineEdit(params.get('name', ''))
        form.addRow("Nom :", self.name_edit)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(int(params.get('width', 800)))
        form.addRow("Largeur :", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(int(params.get('height', 800)))
        form.addRow("Hauteur :", self.height_spin)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["px", "pt", "mm", "cm", "in"])
        idx = self.unit_combo.findText(params.get('unit', 'px'))
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)
        form.addRow("Unité :", self.unit_combo)

        self.orient_combo = QComboBox()
        self.orient_combo.addItems(["Portrait", "Paysage"])
        idx = 0 if params.get('orientation', 'portrait') == 'portrait' else 1
        self.orient_combo.setCurrentIndex(idx)
        form.addRow("Orientation :", self.orient_combo)

        self.color_combo = QComboBox()
        self.color_combo.addItems(["RGB", "CMJN", "Niveaux de gris"])
        idx = self.color_combo.findText(params.get('color_mode', 'RGB'))
        if idx >= 0:
            self.color_combo.setCurrentIndex(idx)
        form.addRow("Mode couleur :", self.color_combo)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(1, 1200)
        self.dpi_spin.setValue(int(params.get('dpi', 72)))
        form.addRow("DPI :", self.dpi_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_parameters(self) -> dict:
        return {
            'name': self.name_edit.text().strip(),
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'unit': self.unit_combo.currentText(),
            'orientation': 'portrait'
                          if self.orient_combo.currentText() == 'Portrait'
                          else 'landscape',
            'color_mode': self.color_combo.currentText(),
            'dpi': self.dpi_spin.value(),
        }
