from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
import os

class ImportsWidget(QWidget):
    """Liste simple des images importées."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)

    def add_image(self, path: str):
        name = os.path.basename(path)
        item = QListWidgetItem(name)
        item.setToolTip(path)
        self.list.addItem(item)
