from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QToolButton,
    QHBoxLayout,
)
from PyQt5.QtCore import Qt


class LayersWidget(QWidget):
    """Layer manager with selection bar and lock/visibility toggles."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main = main_window

        self.combo = QComboBox(self)
        self.combo.currentTextChanged.connect(self._on_combo_changed)
        add_btn = QToolButton(self)
        add_btn.setText("+")
        add_btn.clicked.connect(self._add_layer)
        del_btn = QToolButton(self)
        del_btn.setText("-")
        del_btn.clicked.connect(self._remove_layer)
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(self.combo)
        bar.addWidget(add_btn)
        bar.addWidget(del_btn)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Calque", "Délock", "Visible"])
        self.tree.itemChanged.connect(self._on_item_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(self.tree)

    def populate(self):
        """Refresh combo and list from canvas layers."""
        self.combo.blockSignals(True)
        self.tree.blockSignals(True)
        self.combo.clear()
        self.tree.clear()
        canvas = self.main.canvas
        for name in canvas.layer_names():
            layer = canvas.layers[name]
            self.combo.addItem(name)
            node = QTreeWidgetItem([name, "", ""])
            node.setData(0, Qt.UserRole, name)
            node.setFlags(node.flags() | Qt.ItemIsUserCheckable)
            node.setCheckState(1, Qt.Checked if not getattr(layer, "locked", False) else Qt.Unchecked)
            node.setCheckState(2, Qt.Checked if layer.isVisible() else Qt.Unchecked)
            self.tree.addTopLevelItem(node)
            if canvas.current_layer and canvas.current_layer.layer_name == name:
                self.combo.setCurrentText(name)
                self.tree.setCurrentItem(node)
        self.combo.blockSignals(False)
        self.tree.blockSignals(False)

    def _on_item_changed(self, item, column):
        name = item.data(0, Qt.UserRole)
        if column == 1:
            locked = item.checkState(1) != Qt.Checked
            self.main.canvas.set_layer_locked(name, locked)
        elif column == 2:
            visible = item.checkState(2) == Qt.Checked
            self.main.canvas.set_layer_visible(name, visible)

    def _on_combo_changed(self, name: str):
        if name:
            self.main.canvas.set_current_layer(name)
            self.populate()

    def _add_layer(self):
        canvas = self.main.canvas
        base = f"Layer {len(canvas.layers) + 1}"
        canvas.create_layer(base)
        self.populate()

    def _remove_layer(self):
        name = self.combo.currentText()
        if name:
            self.main.canvas.remove_layer(name)
            self.populate()
