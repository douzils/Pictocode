from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QDialogButtonBox,
    QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QLinearGradient, QBrush


class GradientPreview(QWidget):
    """Simple widget drawing a horizontal gradient."""

    def __init__(self, start: QColor, end: QColor, pos1: float, pos2: float):
        super().__init__()
        self.start = start
        self.end = end
        self.pos1 = pos1
        self.pos2 = pos2
        self.setMinimumHeight(30)

    def set_colors(self, c1: QColor, c2: QColor):
        self.start = c1
        self.end = c2
        self.update()

    def set_positions(self, p1: float, p2: float):
        self.pos1 = p1
        self.pos2 = p2
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(self.pos1, self.start)
        grad.setColorAt(self.pos2, self.end)
        painter.fillRect(self.rect(), QBrush(grad))


class GradientEditorDialog(QDialog):
    """Dialog allowing simple two-color gradient editing."""

    def __init__(
        self,
        start: QColor = QColor("white"),
        end: QColor = QColor("black"),
        pos1: float = 0.0,
        pos2: float = 1.0,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Dégradé")
        self._start = start
        self._end = end
        self._p1 = pos1
        self._p2 = pos2

        layout = QVBoxLayout(self)
        self.preview = GradientPreview(start, end, pos1, pos2)
        layout.addWidget(self.preview)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton()
        self.start_btn.setFixedWidth(40)
        self.start_btn.clicked.connect(lambda: self._choose_color(1))
        btn_layout.addWidget(self.start_btn)
        self.end_btn = QPushButton()
        self.end_btn.setFixedWidth(40)
        self.end_btn.clicked.connect(lambda: self._choose_color(2))
        btn_layout.addWidget(self.end_btn)
        layout.addLayout(btn_layout)

        slider_layout = QHBoxLayout()
        self.slider1 = QSlider(Qt.Horizontal)
        self.slider1.setRange(0, 100)
        self.slider1.setValue(int(pos1 * 100))
        self.slider1.valueChanged.connect(self._update)
        slider_layout.addWidget(self.slider1)
        self.slider2 = QSlider(Qt.Horizontal)
        self.slider2.setRange(0, 100)
        self.slider2.setValue(int(pos2 * 100))
        self.slider2.valueChanged.connect(self._update)
        slider_layout.addWidget(self.slider2)
        layout.addLayout(slider_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_buttons()
        self._update()

    def _choose_color(self, which: int):
        from PyQt5.QtWidgets import QColorDialog

        col = QColorDialog.getColor(parent=self)
        if not col.isValid():
            return
        if which == 1:
            self._start = col
        else:
            self._end = col
        self._update_buttons()
        self._update()

    def _update_buttons(self):
        self.start_btn.setStyleSheet(f"background:{self._start.name()};")
        self.end_btn.setStyleSheet(f"background:{self._end.name()};")

    def _update(self):
        self._p1 = self.slider1.value() / 100
        self._p2 = self.slider2.value() / 100
        self.preview.set_colors(self._start, self._end)
        self.preview.set_positions(self._p1, self._p2)

    def get_gradient(self):
        return self._start, self._end, self._p1, self._p2

