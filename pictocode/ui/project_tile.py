from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class ProjectTile(QWidget):
    """Widget affichant une miniature de projet avec un overlay au survol."""

    def __init__(
        self,
        icon: QIcon,
        title: str,
        width=128,
        height=None,
        parent=None,
    ):
        super().__init__(parent)
        self._width = int(width)
        self._height = int(height or width)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.preview = QLabel(self)
        self.preview.setFixedSize(self._width, self._height)
        self.preview.setPixmap(icon.pixmap(self._width, self._height))
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setScaledContents(True)
        layout.addWidget(self.preview)

        self.overlay = QLabel(title, self)
        self.overlay.setAlignment(Qt.AlignCenter)
        self.overlay.setStyleSheet(
            "background-color: rgba(0, 0, 0, 120); color: white;"
        )
        self.overlay.hide()

    def enterEvent(self, event):
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.overlay.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.overlay.hide()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def sizeHint(self):
        return self.preview.size()
