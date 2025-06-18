from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QAction,
    QAbstractItemView,
    QGraphicsItem,
    QGraphicsItemGroup,
)
from PyQt5.QtCore import Qt
from .animated_menu import AnimatedMenu


class LayersWidget(QWidget):
    """Affiche la liste des objets du canvas avec options de calque."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = None
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Nom", "Visible", "Verrou"])
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)

        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._open_menu)
        self.tree.viewport().setAcceptDrops(True)

    # ------------------------------------------------------------------
    def update_layers(self, canvas):
        self.canvas = canvas
        self.tree.clear()
        if not canvas:
            return

        def add_item(gitem, parent=None):
            if gitem is getattr(canvas, "_frame_item", None):
                return
            if parent is None:
                qitem = QTreeWidgetItem(self.tree)
            else:
                qitem = QTreeWidgetItem(parent)
            name = getattr(gitem, "layer_name", type(gitem).__name__)
            qitem.setText(0, name)
            qitem.setData(0, Qt.UserRole, gitem)
            qitem.setFlags(qitem.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            qitem.setCheckState(1, Qt.Checked if gitem.isVisible() else Qt.Unchecked)
            locked = not (gitem.flags() & QGraphicsItem.ItemIsMovable)
            qitem.setCheckState(2, Qt.Checked if locked else Qt.Unchecked)
            if isinstance(gitem, QGraphicsItemGroup):
                for child in reversed(gitem.childItems()):
                    add_item(child, qitem)

        # ajoute seulement les top-level (pas déjà dans un groupe)
        for it in reversed(canvas.scene.items()):
            if it is getattr(canvas, "_frame_item", None):
                continue
            if it.parentItem() is None:
                add_item(it)

        self._assign_z_values()

    # ------------------------------------------------------------------
    def highlight_item(self, item):
        def walk(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, Qt.UserRole) is item:
                    self.tree.setCurrentItem(child)
                    return True
                if walk(child):
                    return True
            return False

        walk(self.tree.invisibleRootItem())

    # ------------------------------------------------------------------
    def _on_item_changed(self, titem, column):
        gitem = titem.data(0, Qt.UserRole)
        if not gitem:
            return
        if column == 1:
            gitem.setVisible(titem.checkState(1) == Qt.Checked)
        elif column == 2:
            locked = titem.checkState(2) == Qt.Checked
            gitem.setFlag(QGraphicsItem.ItemIsMovable, not locked)
            gitem.setFlag(QGraphicsItem.ItemIsSelectable, not locked)

    def _on_selection_changed(self):
        if not self.canvas:
            return
        items = self.tree.selectedItems()
        if items:
            gitem = items[0].data(0, Qt.UserRole)
            if gitem:
                self.canvas.scene.clearSelection()
                gitem.setSelected(True)

    def _open_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item or not self.canvas:
            return
        gitem = item.data(0, Qt.UserRole)
        menu = AnimatedMenu(self)
        act_delete = QAction("Supprimer", menu)
        menu.addAction(act_delete)
        act_group = QAction("Grouper la sélection", menu)
        menu.addAction(act_group)
        if isinstance(gitem, QGraphicsItemGroup):
            act_ungroup = QAction("Dégrouper", menu)
            menu.addAction(act_ungroup)
        else:
            act_ungroup = None
        action = menu.exec_(self.tree.mapToGlobal(pos))
        if action is act_delete:
            self.canvas.scene.removeItem(gitem)
            self.update_layers(self.canvas)
        elif action is act_group:
            group = self.canvas.group_selected()
            if group:
                self.update_layers(self.canvas)
                self.highlight_item(group)
        elif action is act_ungroup:
            self.canvas.ungroup_item(gitem)
            self.update_layers(self.canvas)

    # ------------------------------------------------------------------
    def dropEvent(self, event):
        super().dropEvent(event)
        self._assign_z_values()

    def _assign_z_values(self):
        if not self.canvas:
            return
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(root.childCount() - 1 - i)
            gitem = item.data(0, Qt.UserRole)
            if gitem:
                gitem.setZValue(i)

