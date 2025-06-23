from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QStackedLayout,
)
from PyQt5.QtCore import Qt

class CornerTabs(QWidget):
    """Small tab widget that appears in the bottom-right corner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("corner_tabs")
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.selector = QComboBox(self)
        layout.addWidget(self.selector)
        self.stack = QStackedLayout()
        layout.addLayout(self.stack)
        self.selector.currentIndexChanged.connect(
            self.stack.setCurrentIndex
        )
        self.hide()

    def add_tab(self, widget, label):
        """Add a new tab with the given widget."""
        self.selector.addItem(label)
        self.stack.addWidget(widget)


