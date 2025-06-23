from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QPlainTextEdit,
    QDialogButtonBox,
    QApplication,
)
from PyQt5.QtCore import Qt


class DebugDialog(QDialog):
    """Simple dialog to display debug information with a copy button."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Debug")
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(text)
        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, Qt.Horizontal, self)
        copy_btn = buttons.addButton("Copier", QDialogButtonBox.ActionRole)
        copy_btn.clicked.connect(self._copy)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _copy(self):
        QApplication.clipboard().setText(self.text_edit.toPlainText())
