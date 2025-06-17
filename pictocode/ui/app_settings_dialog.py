
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDialogButtonBox,
    QLineEdit, QColorDialog, QSpinBox
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class AppSettingsDialog(QDialog):
    """Dialog to adjust global application settings like appearance."""

    def __init__(self, current_theme: str = "Light", accent: QColor | str = QColor(42, 130, 218), font_size: int = 10, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres de l'application")
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        main_layout.addLayout(form)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        idx = self.theme_combo.findText(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)


        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)


