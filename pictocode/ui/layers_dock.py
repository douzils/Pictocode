from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt

class LayersWidget(QWidget):
    """Affiche la liste des objets du canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)

    def update_layers(self, canvas):
        self.list.clear()
        if not canvas:
            return
        for item in reversed(canvas.scene.items()):
            if item is getattr(canvas, "_frame_item", None):
                continue
            lw = QListWidgetItem(type(item).__name__)
            lw.setData(Qt.UserRole, item)
            self.list.addItem(lw)

    def highlight_item(self, item):
        for row in range(self.list.count()):
            lw = self.list.item(row)
            if lw.data(Qt.UserRole) is item:
                self.list.setCurrentRow(row)
                break
