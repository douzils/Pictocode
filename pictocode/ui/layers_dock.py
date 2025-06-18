from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QAction,
    QAbstractItemView,
    QGraphicsItem,
    QGraphicsItemGroup,
    QHeaderView,
)
from PyQt5.QtCore import Qt, QPropertyAnimation
from PyQt5.QtWidgets import QGraphicsObject
from .animated_menu import AnimatedMenu


class LayersWidget(QWidget):
    """Affiche la liste des objets du canvas avec options de calque."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = None
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Nom", "👁", "🔒"])
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)

        self.tree.itemClicked.connect(self._on_item_clicked)
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

        project_name = getattr(canvas, "current_meta", {}).get("name") or "Projet"
        root_item = QTreeWidgetItem(self.tree)
        root_item.setText(0, project_name)
        root_item.setData(0, Qt.UserRole, None)
        root_item.setExpanded(True)
        root_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsDropEnabled)
        root_item.setFirstColumnSpanned(True)

        def add_item(gitem, parent=root_item):
            if gitem is getattr(canvas, "_frame_item", None):
                return
            qitem = QTreeWidgetItem(parent)
            name = getattr(gitem, "layer_name", type(gitem).__name__)
            qitem.setText(0, name)
            qitem.setData(0, Qt.UserRole, gitem)
            qitem.setFlags(
                qitem.flags()
                | Qt.ItemIsEditable
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )
            qitem.setText(1, "👁" if gitem.isVisible() else "🚫")
            locked = not (gitem.flags() & QGraphicsItem.ItemIsMovable)
            qitem.setText(2, "🔒" if locked else "🔓")
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
    def _on_item_clicked(self, titem, column):
        gitem = titem.data(0, Qt.UserRole)
        if not gitem:
            return
        if column == 1:
            vis = not gitem.isVisible()
            gitem.setVisible(vis)
            titem.setText(1, "👁" if vis else "🚫")
        elif column == 2:
            locked = not (gitem.flags() & QGraphicsItem.ItemIsMovable)
            locked = not locked
            gitem.setFlag(QGraphicsItem.ItemIsMovable, not locked)
            gitem.setFlag(QGraphicsItem.ItemIsSelectable, not locked)
            titem.setText(2, "🔒" if locked else "🔓")

    def _on_item_changed(self, titem, column):
        if column == 0:
            gitem = titem.data(0, Qt.UserRole)
            if gitem:
                gitem.layer_name = titem.text(0)

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
        if gitem is None:
            menu = AnimatedMenu(self)
            act_new_group = QAction("Nouvelle collection", menu)
            menu.addAction(act_new_group)
            if menu.exec_(self.tree.mapToGlobal(pos)) == act_new_group:
                group = self.canvas.create_collection()
                self.update_layers(self.canvas)
                self.highlight_item(group)
            return
        menu = AnimatedMenu(self)
        act_delete = QAction("Supprimer", menu)
        menu.addAction(act_delete)
        act_dup = QAction("Dupliquer", menu)
        menu.addAction(act_dup)
        menu.addSeparator()
        act_up = QAction("Monter", menu)
        menu.addAction(act_up)
        act_down = QAction("Descendre", menu)
        menu.addAction(act_down)
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
        elif action is act_dup:
            self.canvas.scene.clearSelection()
            gitem.setSelected(True)
            self.canvas.duplicate_selected()
            new_item = self.canvas.scene.selectedItems()[0]
            self.update_layers(self.canvas)
            self.highlight_item(new_item)
        elif action is act_up:
            parent = item.parent() or self.tree.invisibleRootItem().child(0)
            idx = parent.indexOfChild(item)
            if idx > 0:
                parent.takeChild(idx)
                parent.insertChild(idx - 1, item)
                self._assign_z_values()
        elif action is act_down:
            parent = item.parent() or self.tree.invisibleRootItem().child(0)
            idx = parent.indexOfChild(item)
            if idx < parent.childCount() - 1:
                parent.takeChild(idx)
                parent.insertChild(idx + 1, item)
                self._assign_z_values()
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
        if root.childCount() == 1 and root.child(0).data(0, Qt.UserRole) is None:
            root = root.child(0)
        for i in range(root.childCount()):
            item = root.child(i)
            gitem = item.data(0, Qt.UserRole)
            if gitem:
                self._animate_z(gitem, i)

    def _animate_z(self, gitem, z):
        if isinstance(gitem, QGraphicsObject):
            anim = QPropertyAnimation(gitem, b"zValue", self)
            anim.setDuration(150)
            anim.setStartValue(gitem.zValue())
            anim.setEndValue(z)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        else:
            gitem.setZValue(z)
