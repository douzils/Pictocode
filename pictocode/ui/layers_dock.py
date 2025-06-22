from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt


class LayersWidget(QWidget):
    """Simple layer manager listing layers with visibility toggles."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main = main_window
        self.list = QListWidget()
        self.list.itemChanged.connect(self._on_item_changed)
        self.list.currentTextChanged.connect(self._on_current_changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list)

    def populate(self):
        """Refresh list from canvas layers."""
        self.list.blockSignals(True)
        self.list.clear()
        canvas = self.main.canvas
        for name in canvas.layer_names():
            layer = canvas.layers[name]
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if layer.isVisible() else Qt.Unchecked)
            self.list.addItem(item)
            if canvas.current_layer and canvas.current_layer.layer_name == name:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)

    def _on_item_changed(self, item):
        visible = item.checkState() == Qt.Checked
        self.main.canvas.set_layer_visible(item.text(), visible)

    def _on_current_changed(self, name: str):
        if name:
            self.main.canvas.set_current_layer(name)
