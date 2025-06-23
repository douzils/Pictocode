
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox

from PyQt5.QtCore import Qt, pyqtSignal

class CornerTabs(QWidget):
    """Dropdown widget used as dock header or floating overlay."""

    tab_selected = pyqtSignal(str)

    def __init__(self, parent=None, overlay=False):
        super().__init__(parent)
        self.setObjectName("corner_tabs")
        if overlay:
            self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignLeft)
        self.selector = QComboBox(self)
        self.selector.addItems(["Propriétés", "Imports", "Objets", "Logs"])
        layout.addWidget(self.selector)
        layout.addStretch()

        self.selector.currentTextChanged.connect(self._emit_change)
        if overlay:
            self.hide()


    def add_tab(self, widget, label: str):
        """Compatibility shim for the previous API.

        Only the label is used by the current dropdown based implementation.
        The ``widget`` argument is ignored but kept to avoid runtime errors if
        older code still calls :meth:`add_tab`.
        """
        self.selector.addItem(label)

    def _emit_change(self, text):
        self.tab_selected.emit(text)


