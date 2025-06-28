import json
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSplitter,
    QMenu,
    QFileDialog,
    QDrag,
    QMimeData,
)


class SplitHandle(QWidget):
    """Small widget placed in the corner of a zone to trigger splits."""

    def __init__(self, zone):
        super().__init__(zone)
        self.zone = zone
        self.setFixedSize(14, 14)
        self.start = None
        # Default cursor remains the arrow but we change it when hovering
        self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, event):
        """Show a cross cursor when hovering the handle."""
        self.setCursor(Qt.SizeAllCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = event.globalPos()
        elif event.button() == Qt.RightButton:
            self.zone.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self.start is None:
            return
        delta = event.globalPos() - self.start
        if delta.manhattanLength() > 20:
            orient = Qt.Horizontal if abs(delta.x()) > abs(delta.y()) else Qt.Vertical
            self.zone.request_split(orient)
            self.start = None

    def mouseReleaseEvent(self, event):
        self.start = None


class ZoneWidget(QWidget):
    """Editor zone that can be split and joined."""

    _id_counter = 1
    editors = ["Empty", "3D View", "Script", "Timeline", "UV/Image"]

    def __init__(self):
        super().__init__()
        self.zone_id = ZoneWidget._id_counter
        ZoneWidget._id_counter += 1
        self._drag_start = None
        self.setAcceptDrops(True)
        self._build()

    def _build(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(2)
        top = QHBoxLayout()
        self.selector = QComboBox(self)
        self.selector.addItems(self.editors)
        self.selector.currentTextChanged.connect(self._editor_changed)
        top.addWidget(self.selector)
        top.addStretch(1)
        self.layout.addLayout(top)
        self.content = QLabel(f"Zone {self.zone_id}: {self.selector.currentText()}")
        self.content.setAlignment(Qt.AlignCenter)
        self.content.setStyleSheet("background:#444;color:white")
        self.layout.addWidget(self.content, 1)
        self.handle = SplitHandle(self)
        self.handle.raise_()
        # cross icon shown when hovering the zone to clarify splitting
        self.hover_icon = QLabel(self)
        self.hover_icon.setFixedSize(16, 16)
        self.hover_icon.setStyleSheet("background: transparent;")
        pix = QPixmap(16, 16)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setPen(Qt.white)
        painter.drawLine(0, 0, 15, 15)
        painter.drawLine(0, 15, 15, 0)
        painter.end()
        self.hover_icon.setPixmap(pix)
        self.hover_icon.hide()
        self.hover_icon.move(self.width() // 2 - 8, self.height() // 2 - 8)

    # ------------------------------------------------------------------
    # Drag & drop support
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.selector.geometry().contains(event.pos()):
            self._drag_start = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start and (event.pos() - self._drag_start).manhattanLength() > QApplication.startDragDistance():
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.selector.currentText())
            drag.setMimeData(mime)
            drag.exec_(Qt.MoveAction)
            self._drag_start = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def enterEvent(self, event):
        self.hover_icon.show()
        self.setCursor(Qt.CrossCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_icon.hide()
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def dropEvent(self, event):
        text = event.mimeData().text()
        if text in self.editors:
            source = event.source()
            self.selector.setCurrentText(text)
            if isinstance(source, ZoneWidget) and source is not self:
                source.selector.setCurrentIndex(0)
            event.acceptProposedAction()
        else:
            event.ignore()

    # ------------------------------------------------------------------
    # Drag & drop support
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.selector.geometry().contains(event.pos()):
            self._drag_start = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start and (event.pos() - self._drag_start).manhattanLength() > QApplication.startDragDistance():
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.selector.currentText())
            drag.setMimeData(mime)
            drag.exec_(Qt.MoveAction)
            self._drag_start = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        text = event.mimeData().text()
        if text in self.editors:
            source = event.source()
            self.selector.setCurrentText(text)
            if isinstance(source, ZoneWidget) and source is not self:
                source.selector.setCurrentIndex(0)
            event.acceptProposedAction()
        else:
            event.ignore()

    def resizeEvent(self, event):
        self.handle.move(self.width() - self.handle.width(), 0)
        self.hover_icon.move(self.width() // 2 - 8, self.height() // 2 - 8)
        super().resizeEvent(event)

    def _editor_changed(self, text):
        self.content.setText(f"Zone {self.zone_id}: {text}")

    def request_split(self, orientation):
        parent = self.parent()
        split_zone(self, orientation)

    def show_context_menu(self, pos):
        menu = QMenu()
        close_act = menu.addAction("Fermer la zone")
        join_left = menu.addAction("Fusionner \u2190")
        join_right = menu.addAction("Fusionner \u2192")
        join_up = menu.addAction("Fusionner \u2191")
        join_down = menu.addAction("Fusionner \u2193")
        act = menu.exec_(pos)
        if act == close_act:
            close_zone(self)
        elif act == join_left:
            join_zone(self, "left")
        elif act == join_right:
            join_zone(self, "right")
        elif act == join_up:
            join_zone(self, "up")
        elif act == join_down:
            join_zone(self, "down")


def split_zone(zone, orientation):
    parent = zone.parent()
    new_zone = ZoneWidget()
    if isinstance(parent, QSplitter):
        if parent.orientation() == orientation:
            idx = parent.indexOf(zone)
            parent.insertWidget(idx + 1, new_zone)
        else:
            idx = parent.indexOf(zone)
            splitter = QSplitter(orientation)
            parent.insertWidget(idx, splitter)
            parent.widget(idx + 1).setParent(None)
            splitter.addWidget(zone)
            splitter.addWidget(new_zone)
    else:
        splitter = QSplitter(orientation)
        zone.setParent(splitter)
        splitter.addWidget(zone)
        splitter.addWidget(new_zone)
        lay = parent.layout()
        lay.addWidget(splitter)


def close_zone(zone):
    parent = zone.parent()
    if not isinstance(parent, QSplitter):
        return
    idx = parent.indexOf(zone)
    zone.deleteLater()
    parent.setStretchFactor(max(idx - 1, 0), 1)
    if parent.count() == 1:
        child = parent.widget(0)
        grand = parent.parent()
        if isinstance(grand, QSplitter):
            gidx = grand.indexOf(parent)
            parent.widget(0).setParent(grand)
            grand.insertWidget(gidx, child)
            parent.deleteLater()
        else:
            lay = grand.layout()
            lay.addWidget(child)
            parent.deleteLater()


def join_zone(zone, direction):
    parent = zone.parent()
    if not isinstance(parent, QSplitter):
        return
    idx = parent.indexOf(zone)
    if parent.orientation() == Qt.Horizontal:
        if direction == "left" and idx > 0:
            to_close = parent.widget(idx - 1)
        elif direction == "right" and idx < parent.count() - 1:
            to_close = parent.widget(idx + 1)
        else:
            return
    else:
        if direction == "up" and idx > 0:
            to_close = parent.widget(idx - 1)
        elif direction == "down" and idx < parent.count() - 1:
            to_close = parent.widget(idx + 1)
        else:
            return
    close_zone(to_close)


def serialize(widget):
    if isinstance(widget, ZoneWidget):
        return {
            "type": "zone",
            "id": widget.zone_id,
            "editor": widget.selector.currentText(),
        }
    elif isinstance(widget, QSplitter):
        return {
            "type": "splitter",
            "orientation": int(widget.orientation()),
            "sizes": widget.sizes(),
            "children": [serialize(widget.widget(i)) for i in range(widget.count())],
        }


def deserialize(data):
    if data["type"] == "zone":
        zone = ZoneWidget()
        zone.zone_id = data.get("id", zone.zone_id)
        zone.selector.setCurrentText(data.get("editor", zone.selector.currentText()))
        zone._editor_changed(zone.selector.currentText())
        return zone
    else:
        splitter = QSplitter(Qt.Orientation(data.get("orientation", int(Qt.Horizontal))))
        for child in data.get("children", []):
            splitter.addWidget(deserialize(child))
        if "sizes" in data:
            splitter.setSizes([int(s) for s in data["sizes"]])
        return splitter


class LayoutWindow(QMainWindow):
    """Main window demonstrating dynamic zone layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Split Layout Demo")
        self.root = QSplitter(Qt.Horizontal)
        self.root.addWidget(ZoneWidget())
        self.setCentralWidget(self.root)
        self._create_menu()

    def _create_menu(self):
        m = self.menuBar().addMenu("Layout")
        save_act = m.addAction("Sauvegarder...")
        save_act.triggered.connect(self.save_layout)
        load_act = m.addAction("Charger...")
        load_act.triggered.connect(self.load_layout)

    def save_layout(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder", "layout.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf8") as f:
                json.dump(serialize(self.root), f, indent=2)

    def load_layout(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger", "layout.json", "JSON (*.json)")
        if path:
            with open(path, "r", encoding="utf8") as f:
                data = json.load(f)
            self.root.deleteLater()
            self.root = deserialize(data)
            self.setCentralWidget(self.root)


if __name__ == "__main__":
    app = QApplication([])
    w = LayoutWindow()
    w.show()
    app.exec_()
