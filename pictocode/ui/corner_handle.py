from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen


class CornerHandle(QWidget):
    """Small handle shown in the bottom right corner of dock widgets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("corner_handle")
        self.setFixedSize(12, 12)
        # Use a diagonal resize cursor so users know the handle creates
        # or resizes a dock when dragged from the corner.
        self.setCursor(Qt.SizeFDiagCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self.palette().color(self.foregroundRole()), 1)
        painter.setPen(pen)
        for i in range(3):
            offset = 3 + i * 3
            painter.drawLine(0, self.height() - offset, self.width() - offset, self.height())
        painter.end()
