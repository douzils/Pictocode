from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QDialogButtonBox
from PyQt5.QtCore import Qt

class AppSettingsDialog(QDialog):
    """Dialog to adjust global application settings like appearance."""
    def __init__(self, current_theme: str = "Light", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Param\u00e8tres de l'application")
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        main_layout.addLayout(form)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        idx = self.theme_combo.findText(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        form.addRow("Th\u00e8me :", self.theme_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_theme(self) -> str:
        return self.theme_combo.currentText()
