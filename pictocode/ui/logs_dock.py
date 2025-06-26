from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from ..logger import log_emitter

class LogsWidget(QWidget):
    """Simple widget that displays application logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumSize(0, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_edit)
        log_emitter.log_record.connect(self.text_edit.appendPlainText)
