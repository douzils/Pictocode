import json
from PyQt5.QtCore import Qt, QPoint
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
)


class SplitHandle(QWidget):
    """Small widget placed in the corner of a zone to trigger splits."""

    def __init__(self, zone):
        super().__init__(zone)
        self.zone = zone
        self.setFixedSize(14, 14)
        self.start = None
        self.setCursor(Qt.SizeAllCursor)

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
    editors = ["3D View", "Script", "Timeline", "UV/Image"]

    def __init__(self):
        super().__init__()
        self.zone_id = ZoneWidget._id_counter
        ZoneWidget._id_counter += 1
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

    def resizeEvent(self, event):
        self.handle.move(self.width() - self.handle.width(), 0)
        super().resizeEvent(event)

    def _editor_changed(self, text):
        self.content.setText(f"Zone {self.zone_id}: {text}")

    def request_split(self, orientation):
        parent = self.parent()
        split_zone(self, orientation)

    def show_context_menu(self, pos):
        menu = QMenu()
        close_act = menu.addAction("Fermer la zone")
        act = menu.exec_(pos)
        if act == close_act:
            close_zone(self)


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
