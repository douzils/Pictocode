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

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        idx = self.theme_combo.findText(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        form.addRow("Thème :", self.theme_combo)

        # Accent color
        self.accent_color = QColor(accent)
        self.color_edit = QLineEdit(self.accent_color.name())
        self.color_edit.setReadOnly(True)
        self.color_edit.mousePressEvent = self._choose_color
        form.addRow("Couleur d'accent :", self.color_edit)

        # Global font size
        self.font_spin = QSpinBox()
        self.font_spin.setRange(6, 32)
        self.font_spin.setValue(int(font_size))
        form.addRow("Taille de police :", self.font_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    # --- accessors -------------------------------------------------------
    def _choose_color(self, event):
        col = QColorDialog.getColor(self.accent_color, self)
        if col.isValid():
            self.accent_color = col
            self.color_edit.setText(col.name())

    def get_theme(self) -> str:
        return self.theme_combo.currentText()

    def get_accent_color(self) -> QColor:
        return self.accent_color

    def get_font_size(self) -> int:
        return self.font_spin.value()
