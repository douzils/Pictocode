from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QToolButton,
    QMenu,
    QWidgetAction,
)
from PyQt5.QtCore import Qt, QPoint


class LayersWidget(QWidget):
    """Compact drop-down layer manager."""


    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main = main_window


        self.button = QToolButton(self)
        self.button.setPopupMode(QToolButton.InstantPopup)
        self.button.clicked.connect(self._update_menu_text)

        self.menu = QMenu(self)
        self.menu.aboutToShow.connect(self.populate)
        action = QWidgetAction(self.menu)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Calque", "Lock", "Vis.", ""])
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        action.setDefaultWidget(self.tree)
        self.menu.addAction(action)
        self.button.setMenu(self.menu)

        add_btn = QToolButton(self)
        add_btn.setText("+")
        add_btn.clicked.connect(self._add_layer)
        del_btn = QToolButton(self)
        del_btn.setText("-")
        del_btn.clicked.connect(self._remove_layer)


        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)
        layout.addWidget(add_btn)
        layout.addWidget(del_btn)


    # ------------------------------------------------------------------
    def populate(self):

        """Refresh drop-down list from canvas layers."""
        self.tree.blockSignals(True)

        self.tree.clear()
        canvas = self.main.canvas
        for name in canvas.layer_names():
            layer = canvas.layers[name]
            node = QTreeWidgetItem([name, "", "", ""])
            node.setData(0, Qt.UserRole, name)
            node.setFlags(
                node.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsEditable
                | Qt.ItemIsSelectable
            )
            node.setCheckState(1, Qt.Checked if not getattr(layer, "locked", False) else Qt.Unchecked)
            node.setCheckState(2, Qt.Checked if layer.isVisible() else Qt.Unchecked)
            btn = QToolButton()
            btn.setText("-")
            btn.clicked.connect(lambda _, n=name: self._remove_layer_by_name(n))
            self.tree.addTopLevelItem(node)
            self.tree.setItemWidget(node, 3, btn)
            if canvas.current_layer and canvas.current_layer.layer_name == name:
                self.tree.setCurrentItem(node)
                self.button.setText(name)
        self.tree.blockSignals(False)

    # ------------------------------------------------------------------
    def _on_item_clicked(self, item, column):
        name = item.data(0, Qt.UserRole)
        if name:
            self.main.canvas.set_current_layer(name)
            self.button.setText(name)
            self.menu.hide()

    def _on_item_changed(self, item, column):
        name = item.data(0, Qt.UserRole)
        if column == 0:
            new_name = item.text(0)
            if new_name and new_name != name:
                self.main.canvas.rename_layer(name, new_name)
                item.setData(0, Qt.UserRole, new_name)
                self.button.setText(new_name)
        elif column == 1:
            locked = item.checkState(1) != Qt.Checked
            self.main.canvas.set_layer_locked(name, locked)
        elif column == 2:
            visible = item.checkState(2) == Qt.Checked
            self.main.canvas.set_layer_visible(name, visible)

    def _update_menu_text(self):
        layer = self.main.canvas.current_layer
        if layer:
            self.button.setText(layer.layer_name)

    # ------------------------------------------------------------------
    def _add_layer(self):
        base = f"Layer {len(self.main.canvas.layers) + 1}"
        self.main.canvas.create_layer(base)
        self.populate()

    def _remove_layer(self):
        item = self.tree.currentItem()
        name = item.data(0, Qt.UserRole) if item else None
        if name:
            self.main.canvas.remove_layer(name)
            self.populate()

    def _remove_layer_by_name(self, name: str):
        self.main.canvas.remove_layer(name)
        self.populate()

    # ------------------------------------------------------------------
    def _on_context_menu(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        if not item:
            return
        name = item.data(0, Qt.UserRole)
        menu = QMenu(self)
        dup = menu.addAction("Dupliquer")
        up = menu.addAction("Monter")
        down = menu.addAction("Descendre")
        delete = menu.addAction("Supprimer")
        act = menu.exec_(self.tree.mapToGlobal(pos))
        if act == dup:
            self.main.canvas.duplicate_layer(name)
        elif act == up:
            self.main.canvas.move_layer(name, -1)
        elif act == down:
            self.main.canvas.move_layer(name, 1)
        elif act == delete:
            self.main.canvas.remove_layer(name)
        self.populate()

