from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QPoint


class TitleBar(QWidget):
    """Custom window title bar with move and control buttons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.setObjectName("title_bar")
        self._mouse_pos = QPoint()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)

        self.title_label = QLabel("Pictocode", self)
        self.title_label.setObjectName("titlebar_label")
        layout.addWidget(self.title_label, 1)

        self.min_btn = QPushButton("–", self)
        self.min_btn.setObjectName("titlebar_min")
        self.min_btn.clicked.connect(parent.showMinimized)
        layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("☐", self)
        self.max_btn.setObjectName("titlebar_max")
        self.max_btn.clicked.connect(self._toggle_max)
        layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("✕", self)
        self.close_btn.setObjectName("titlebar_close")
        self.close_btn.clicked.connect(parent.close)
        layout.addWidget(self.close_btn)

        self._maximized = False

    def _toggle_max(self):
        if self._maximized:
            self._parent.showNormal()
        else:
            self._parent.showMaximized()
        self._maximized = not self._maximized

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_pos = event.globalPos() - self._parent.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self._maximized:
            self._parent.move(event.globalPos() - self._mouse_pos)
        super().mouseMoveEvent(event)
