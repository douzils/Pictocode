from PyQt5.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout
from PyQt5.QtCore import Qt


class LayoutWidget(QWidget):
    """Hierarchical view of canvas items similar to Blender's outliner."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main = main_window
        self.tree = QTreeWidget()
        self.tree.header().hide()
        self.tree.itemSelectionChanged.connect(self._on_item_selected)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

    # ------------------------------------------------------------------
    def populate(self):
        """Refresh object hierarchy from canvas."""
        self.tree.blockSignals(True)
        self.tree.clear()
        canvas = self.main.canvas
        for name in canvas.layer_names():
            layer = canvas.layers[name]
            node = QTreeWidgetItem([name])
            node.setData(0, Qt.UserRole, name)
            self.tree.addTopLevelItem(node)
            self._add_children(layer, node)
        self.tree.expandAll()
        self.tree.blockSignals(False)

    def _add_children(self, graphics_item, tree_item):
        for child in reversed(graphics_item.childItems()):
            name = getattr(child, "layer_name", type(child).__name__)
            node = QTreeWidgetItem([name])
            node.setData(0, Qt.UserRole, name)
            tree_item.addChild(node)
            if hasattr(child, "childItems") and child.childItems():
                self._add_children(child, node)

    # ------------------------------------------------------------------
    def _on_item_selected(self):
        current = self.tree.currentItem()
        if not current:
            return
        name = current.data(0, Qt.UserRole)
        self.main.canvas.select_item_by_name(name)
