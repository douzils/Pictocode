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
    QFrame,
)
from PyQt5.QtCore import Qt, QPropertyAnimation
from PyQt5.QtWidgets import QGraphicsObject
from PyQt5.QtGui import QBrush, QColor
from .animated_menu import AnimatedMenu


class LayersTreeWidget(QTreeWidget):
    """QTreeWidget with custom drag preview highlighting."""

    def __init__(self, parent=None, *, drop_color: QColor | None = None, group_color: QColor | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self._parent = parent
        pal = self.palette()
        self.drop_color = drop_color or pal.highlight().color()
        self.group_color = group_color or pal.highlight().color()
        self._drop_line = QFrame(self.viewport())
        self._drop_line.setFixedHeight(2)
        self._drop_line.setStyleSheet(f"background:{self.drop_color.name()};")
        self._drop_line.hide()
        self._highlight_item = None

    def _clear_highlight(self):
        if self._highlight_item:
            for c in range(self.columnCount()):
                self._highlight_item.setBackground(c, QBrush())
            self._highlight_item = None

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        item = self.itemAt(event.pos())
        pos = self.dropIndicatorPosition()

        if pos in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem) and item:
            rect = self.visualItemRect(item)
            y = rect.top() if pos == QAbstractItemView.AboveItem else rect.bottom()
            self._drop_line.setGeometry(0, y, self.viewport().width(), 2)
            self._drop_line.show()
        else:
            self._drop_line.hide()

        if pos == QAbstractItemView.OnItem and item:
            if self._highlight_item is not item:
                self._clear_highlight()
                self._highlight_item = item
                brush = QBrush(self.group_color)
                for c in range(self.columnCount()):
                    item.setBackground(c, brush)
        else:
            self._clear_highlight()

    def _handle_tree_drop(self, event):
        self._drop_line.hide()
        self._clear_highlight()
        super().dropEvent(event)
        if self._parent and hasattr(self._parent, "_handle_tree_drop"):
            self._parent._handle_tree_drop(event)

    def dragLeaveEvent(self, event):
        self._drop_line.hide()
        self._clear_highlight()
        super().dragLeaveEvent(event)


class LayersWidget(QWidget):
    """Affiche la liste des objets du canvas avec options de calque."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = None
        self.tree = LayersTreeWidget(self)
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Nom", "👁", "🔒"])
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.SelectedClicked
        )
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)

        self._apply_styles()

        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._open_menu)
        self.tree.viewport().setAcceptDrops(True)

    def _apply_styles(self):
        """Applique un style plus moderne a la liste des calques."""
        pal = self.tree.palette()
        base = pal.base().color().name()
        alt = pal.alternateBase().color().name()
        text = pal.text().color().name()
        highlight = pal.highlight().color().name()
        highlight_text = pal.highlightedText().color().name()
        header_bg = pal.window().color().name()
        border = pal.mid().color().name()

        self.tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background: {base};
                alternate-background-color: {alt};
                color: {text};
                border: 1px solid {border};
            }}
            QTreeWidget::item {{
                padding: 4px 2px;
            }}
            QTreeWidget::item:selected {{
                background: {highlight};
                color: {highlight_text};
            }}
            QHeaderView::section {{
                background: {header_bg};
                padding: 2px;
                border: none;
            }}
            """
        )

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
            flags = (
                qitem.flags()
                | Qt.ItemIsEditable
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )
            qitem.setFlags(flags)
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

        self._sync_scene_from_tree()

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
        if not self.canvas:
            return

        item = self.tree.itemAt(pos)
        root = self.tree.invisibleRootItem().child(0)

        def insert_group(index: int):
            group = self.canvas.create_collection()
            self.update_layers(self.canvas)
            self.highlight_item(group)
            qitem = self.tree.currentItem()
            root.takeChild(root.indexOfChild(qitem))
            root.insertChild(index, qitem)
            self._sync_scene_from_tree()

        if item is None:
            menu = AnimatedMenu(self)
            act_new_group = QAction("Nouvelle collection", menu)
            menu.addAction(act_new_group)
            if menu.exec_(self.tree.mapToGlobal(pos)) == act_new_group:
                idx = self.tree.indexAt(pos).row()
                if idx < 0:
                    idx = root.childCount()
                insert_group(idx)
            return

        gitem = item.data(0, Qt.UserRole)
        if gitem is None:
            menu = AnimatedMenu(self)
            act_new_group = QAction("Nouvelle collection", menu)
            menu.addAction(act_new_group)
            if menu.exec_(self.tree.mapToGlobal(pos)) == act_new_group:
                insert_group(root.childCount())
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
                self._sync_scene_from_tree()
        elif action is act_down:
            parent = item.parent() or self.tree.invisibleRootItem().child(0)
            idx = parent.indexOfChild(item)
            if idx < parent.childCount() - 1:
                parent.takeChild(idx)
                parent.insertChild(idx + 1, item)
                self._sync_scene_from_tree()
        elif action is act_group:
            group = self.canvas.group_selected()
            if group:
                self.update_layers(self.canvas)
                self.highlight_item(group)
        elif action is act_ungroup:
            self.canvas.ungroup_item(gitem)
            self.update_layers(self.canvas)

    # ------------------------------------------------------------------
    def _handle_tree_drop(self, event):
        target_item = self.tree.itemAt(event.pos())
        drop_pos = self.tree.dropIndicatorPosition()
        selected = [it.data(0, Qt.UserRole) for it in self.tree.selectedItems()]

        if (
            target_item
            and drop_pos == QAbstractItemView.OnItem
            and selected
            and target_item not in self.tree.selectedItems()
            and self.canvas
        ):
            target_gitem = target_item.data(0, Qt.UserRole)
            if target_gitem and not isinstance(target_gitem, QGraphicsItemGroup):
                self.canvas.scene.clearSelection()
                target_gitem.setSelected(True)
                for g in selected:
                    g.setSelected(True)
                group = self.canvas.group_selected()
                if group:
                    event.accept()
                    self.update_layers(self.canvas)
                    self.highlight_item(group)
                    return

        super().dropEvent(event)
        self._sync_scene_from_tree()

    def _sync_scene_from_tree(self):
        """Apply the current tree hierarchy to the QGraphicsScene."""
        if not self.canvas:
            return

        def apply_children(tparent, gparent):
            for idx in range(tparent.childCount()):
                child = tparent.child(idx)
                gitem = child.data(0, Qt.UserRole)
                if gitem:
                    target_parent = gparent if isinstance(gparent, QGraphicsItemGroup) else None
                    if gitem.parentItem() is not target_parent:
                        gitem.setParentItem(target_parent)
                    self._animate_z(gitem, idx)
                apply_children(child, gitem)

        root = self.tree.invisibleRootItem()
        if root.childCount() == 1 and root.child(0).data(0, Qt.UserRole) is None:
            root = root.child(0)
        apply_children(root, None)

    def _animate_z(self, gitem, z):
        if isinstance(gitem, QGraphicsObject):
            anim = QPropertyAnimation(gitem, b"zValue", self)
            anim.setDuration(150)
            anim.setStartValue(gitem.zValue())
            anim.setEndValue(z)
            anim.start(QPropertyAnimation.DeleteWhenStopped)
        else:
            gitem.setZValue(z)
