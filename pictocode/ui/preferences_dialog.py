from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QPushButton,
    QComboBox, QColorDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor

class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pr\xe9f\xe9rences")
        self.setModal(True)
        self.settings = QSettings("pictocode", "pictocode")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # Qt style/theme
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Fusion", "Windows", "WindowsVista"])
        current_style = self.settings.value("ui/style", "Fusion")
        idx = self.style_combo.findText(current_style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)
        form.addRow("Style Qt :", self.style_combo)

        # Background color
        self.bg_btn = QPushButton()
        self.bg_color = QColor(self.settings.value("colors/background", "#ffffff"))
        self._update_button(self.bg_btn, self.bg_color)
        self.bg_btn.clicked.connect(lambda: self._choose_color("bg"))
        form.addRow("Couleur du fond :", self.bg_btn)

        # Grid color
        self.grid_btn = QPushButton()
        self.grid_color = QColor(self.settings.value("colors/grid", "#dcdcdc"))
        self._update_button(self.grid_btn, self.grid_color)
        self.grid_btn.clicked.connect(lambda: self._choose_color("grid"))
        form.addRow("Couleur de la grille :", self.grid_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    # internal helpers
    def _update_button(self, btn: QPushButton, color: QColor):
        btn.setText(color.name())
        btn.setStyleSheet(f"background-color: {color.name()};")

    def _choose_color(self, which: str):
        initial = self.bg_color if which == "bg" else self.grid_color
        col = QColorDialog.getColor(initial, self)
        if col.isValid():
            if which == "bg":
                self.bg_color = col
                self._update_button(self.bg_btn, col)
            else:
                self.grid_color = col
                self._update_button(self.grid_btn, col)

    def accept(self):
        self.settings.setValue("ui/style", self.style_combo.currentText())
        self.settings.setValue("colors/background", self.bg_color.name())
        self.settings.setValue("colors/grid", self.grid_color.name())
        super().accept()
