# pictocode/shapes.py

from PyQt5.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsTextItem,
    QGraphicsItem,
)
from PyQt5.QtGui import QPen, QBrush, QColor, QPainterPath, QFont
from PyQt5.QtCore import Qt, QPointF, QRectF


class SnapToGridMixin:
    """Mixin ajoutant l'alignement à la grille lors du déplacement."""

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            view = self.scene().views()[0] if self.scene().views() else None
            if view and getattr(view, "snap_to_grid", False):
                scale = view.transform().m11() or 1
                grid = view.grid_size / scale
                value.setX(round(value.x() / grid) * grid)
                value.setY(round(value.y() / grid) * grid)
        return super().itemChange(change, value)


class ResizableMixin:
    """Ajoute une poignée de redimensionnement et la logique associée."""

    handle_size = 8

    def __init__(self):
        super().__init__()
        self._resizing = False
        self._start_pos = QPointF()
        self._start_rect = QRectF()

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            r = self.rect()
            s = self.handle_size
            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(Qt.black))
            painter.drawRect(r.right() - s, r.bottom() - s, s, s)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            r = self.rect()
            handle = QRectF(
                r.right() - self.handle_size,
                r.bottom() - self.handle_size,
                self.handle_size,
                self.handle_size,
            )
            if handle.contains(event.pos()):
                self._resizing = True
                self._start_pos = event.scenePos()
                self._start_rect = QRectF(r)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.scenePos() - self._start_pos
            w = self._start_rect.width() + delta.x()
            h = self._start_rect.height() + delta.y()
            if event.modifiers() & Qt.ShiftModifier:
                aspect = (
                    self._start_rect.width() / self._start_rect.height()
                    if self._start_rect.height()
                    else 1
                )
                if abs(delta.x()) > abs(delta.y()):
                    h = w / aspect
                else:
                    w = h * aspect
            self.setRect(self._start_rect.x(), self._start_rect.y(), w, h)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


class Rect(ResizableMixin, SnapToGridMixin, QGraphicsRectItem):
    """Rectangle déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x, y, w, h, color: QColor = QColor("white")):
        # Initialise explicitement les différentes bases pour
        # éviter que ``ResizableMixin`` ne reçoive des arguments
        # inattendus via ``super()``.
        ResizableMixin.__init__(self)
        QGraphicsRectItem.__init__(self, x, y, w, h)
        pen = QPen(color)
        pen.setWidth(2)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.white))
        self.setFlags(
            QGraphicsRectItem.ItemIsMovable
            | QGraphicsRectItem.ItemIsSelectable
            | QGraphicsRectItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setToolTip("Clique droit pour modifier")


class Ellipse(ResizableMixin, SnapToGridMixin, QGraphicsEllipseItem):
    """Ellipse déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x, y, w, h, color: QColor = QColor("white")):
        ResizableMixin.__init__(self)
        QGraphicsEllipseItem.__init__(self, x, y, w, h)
        pen = QPen(color)
        pen.setWidth(2)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.white))
        self.setFlags(
            QGraphicsEllipseItem.ItemIsMovable
            | QGraphicsEllipseItem.ItemIsSelectable
            | QGraphicsEllipseItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setToolTip("Clique droit pour modifier")


class Line(SnapToGridMixin, QGraphicsLineItem):
    """Ligne déplaçable et sélectionnable."""

    def __init__(self, x1, y1, x2, y2, color: QColor = QColor("black")):
        super().__init__(x1, y1, x2, y2)
        pen = QPen(color)
        pen.setWidth(2)
        self.setPen(pen)
        self.setFlags(
            QGraphicsLineItem.ItemIsMovable
            | QGraphicsLineItem.ItemIsSelectable
            | QGraphicsLineItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setToolTip("Clique droit pour modifier")


class FreehandPath(SnapToGridMixin, QGraphicsPathItem):
    """
    Tracé libre.
    Utilisez `from_points` pour construire à partir d’une liste de QPointF.
    """

    def __init__(
        self, path=None, pen_color: QColor = QColor("black"), pen_width: int = 2
    ):
        super().__init__()
        pen = QPen(pen_color)
        pen.setWidth(pen_width)
        self.setPen(pen)
        if path is not None:
            self.setPath(path)
        self.setFlags(
            QGraphicsPathItem.ItemIsMovable
            | QGraphicsPathItem.ItemIsSelectable
            | QGraphicsPathItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setToolTip("Clique droit pour modifier")

    @classmethod
    def from_points(
        cls,
        points: list[QPointF],
        pen_color: QColor = QColor("black"),
        pen_width: int = 2,
    ):
        painter_path = QPainterPath()
        if points:
            painter_path.moveTo(points[0])
            for pt in points[1:]:
                painter_path.lineTo(pt)
        return cls(painter_path, pen_color, pen_width)


class TextItem(QGraphicsTextItem):
    """Bloc de texte éditable et déplaçable."""

    def __init__(
        self,
        x: float,
        y: float,
        text: str = "",
        font_size: int = 12,
        color: QColor = QColor("black"),
    ):
        super().__init__(text)
        font = QFont()
        font.setPointSize(font_size)
        self.setFont(font)
        self.setDefaultTextColor(color)
        self.setPos(x, y)
        # Permet l’édition au double-clic
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFlags(
            QGraphicsTextItem.ItemIsMovable
            | QGraphicsTextItem.ItemIsSelectable
            | QGraphicsTextItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setToolTip("Clique droit pour modifier")

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            view = self.scene().views()[0] if self.scene().views() else None
            if view and getattr(view, "snap_to_grid", False):
                scale = view.transform().m11() or 1
                grid = view.grid_size / scale
                value.setX(round(value.x() / grid) * grid)
                value.setY(round(value.y() / grid) * grid)
        return super().itemChange(change, value)
