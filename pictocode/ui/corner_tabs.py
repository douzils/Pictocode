
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox
from PyQt5.QtCore import Qt, pyqtSignal

class CornerTabs(QWidget):
    """Dropdown widget used as dock header or floating overlay."""

    tab_selected = pyqtSignal(str)

    def __init__(self, parent=None, overlay=False):
        super().__init__(parent)
        self.setObjectName("corner_tabs")
        if overlay:
            self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.selector = QComboBox(self)
        self.selector.addItems(["Propriétés", "Imports", "Objets", "Logs"])
        layout.addWidget(self.selector)
        self.selector.currentTextChanged.connect(self._emit_change)
        if overlay:
            self.hide()

    def _emit_change(self, text):
        self.tab_selected.emit(text)



