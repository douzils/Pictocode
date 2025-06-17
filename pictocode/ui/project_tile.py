from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt

class ProjectTile(QWidget):
    """Widget affichant une miniature de projet avec un overlay au survol."""

    def __init__(self, icon: QIcon, title: str, size=128, parent=None):
        super().__init__(parent)
        self._size = size
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.preview = QLabel(self)
        self.preview.setPixmap(icon.pixmap(size, size))
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

    def sizeHint(self):
        return self.preview.pixmap().size()
