from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QKeySequenceEdit,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt


class ShortcutSettingsDialog(QDialog):
    """Dialog to customize keyboard shortcuts."""

    def __init__(self, shortcuts: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Raccourcis clavier")
        self.setModal(True)

        self._edits = {}

        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        main_layout.addLayout(form)

        for name, seq in shortcuts.items():
            edit = QKeySequenceEdit(seq, self)
            form.addRow(name + " :", edit)
            self._edits[name] = edit

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_shortcuts(self) -> dict[str, str]:
        return {
            name: edit.keySequence().toString()
            for name, edit in self._edits.items()
        }
