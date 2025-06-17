# pictocode/shapes.py

from PyQt5.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsTextItem,
    QGraphicsPixmapItem,
    QGraphicsItem,
)
from PyQt5.QtGui import QPen, QBrush, QColor, QPainterPath, QFont, QPixmap
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
    """Ajoute des poignées de redimensionnement et la logique associée."""

    handle_size = 8

    def __init__(self):
        super().__init__()
        self._resizing = False
        self._start_pos = QPointF()
        self._start_rect = QRectF()
        self._active_handle = None  # 0: TL, 1: TR, 2: BR, 3: BL

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            r = self.rect()
            s = self.handle_size
            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(Qt.black))
            handles = [
                QRectF(r.left() - s / 2, r.top() - s / 2, s, s),
                QRectF(r.right() - s / 2, r.top() - s / 2, s, s),
                QRectF(r.right() - s / 2, r.bottom() - s / 2, s, s),
                QRectF(r.left() - s / 2, r.bottom() - s / 2, s, s),
            ]
            for handle in handles:
                painter.drawRect(handle)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            r = self.rect()
            s = self.handle_size
            handles = [
                QRectF(r.left() - s / 2, r.top() - s / 2, s, s),
                QRectF(r.right() - s / 2, r.top() - s / 2, s, s),
                QRectF(r.right() - s / 2, r.bottom() - s / 2, s, s),
                QRectF(r.left() - s / 2, r.bottom() - s / 2, s, s),
            ]
            for idx, handle in enumerate(handles):
                if handle.contains(event.pos()):
                    self._resizing = True
                    self._active_handle = idx
                    self._start_pos = event.scenePos()
                    self._start_rect = QRectF(r)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.scenePos() - self._start_pos
            x = self._start_rect.x()
            y = self._start_rect.y()
            w = self._start_rect.width()
            h = self._start_rect.height()
            if self._active_handle == 0:  # top-left
                x += delta.x()
                y += delta.y()
                w -= delta.x()
                h -= delta.y()
            elif self._active_handle == 1:  # top-right
                y += delta.y()
                w += delta.x()
                h -= delta.y()
            elif self._active_handle == 2:  # bottom-right
                w += delta.x()
                h += delta.y()
            elif self._active_handle == 3:  # bottom-left
                x += delta.x()
                w -= delta.x()
                h += delta.y()
            if event.modifiers() & Qt.ShiftModifier:
                aspect = (
                    self._start_rect.width() / self._start_rect.height()
                    if self._start_rect.height()
                    else 1
                )
                if abs(w) / aspect > abs(h):
                    h = abs(w) / aspect * (1 if h >= 0 else -1)
                else:
                    w = abs(h) * aspect * (1 if w >= 0 else -1)
            self.setRect(x, y, w, h)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._active_handle = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class Rect(ResizableMixin, SnapToGridMixin, QGraphicsRectItem):
    """Rectangle déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x, y, w, h, color: QColor = QColor("black")):
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

    def rect(self):
        return self.boundingRect()

    def setRect(self, x, y, w, h):
        self.setPos(x, y)
        br = self.boundingRect()
        if br.width() and br.height():
            sx = w / br.width()
            sy = h / br.height()
            self.setScale(min(sx, sy))


class Ellipse(ResizableMixin, SnapToGridMixin, QGraphicsEllipseItem):
    """Ellipse déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x, y, w, h, color: QColor = QColor("black")):
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


class LineResizableMixin:
    """Ajoute des poignées de redimensionnement pour les lignes."""

    handle_size = 8

    def __init__(self):
        super().__init__()
        self._resizing = False
        self._active = None
        self._start_pos = QPointF()
        self._start_line = None

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            line = self.line()
            s = self.handle_size
            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(Qt.black))
            handles = [
                QRectF(line.p1().x() - s / 2, line.p1().y() - s / 2, s, s),
                QRectF(line.p2().x() - s / 2, line.p2().y() - s / 2, s, s),
            ]
            for h in handles:
                painter.drawRect(h)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            line = self.line()
            s = self.handle_size
            handles = [
                QRectF(line.p1().x() - s / 2, line.p1().y() - s / 2, s, s),
                QRectF(line.p2().x() - s / 2, line.p2().y() - s / 2, s, s),
            ]
            for idx, h in enumerate(handles):
                if h.contains(event.pos()):
                    self._resizing = True
                    self._active = idx
                    self._start_pos = event.scenePos()
                    self._start_line = self.line()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.scenePos() - self._start_pos
            line = self._start_line
            if self._active == 0:
                p1 = line.p1() + delta
                self.setLine(p1.x(), p1.y(), line.p2().x(), line.p2().y())
            else:
                p2 = line.p2() + delta
                self.setLine(line.p1().x(), line.p1().y(), p2.x(), p2.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._active = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class Line(LineResizableMixin, SnapToGridMixin, QGraphicsLineItem):
    """Ligne déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x1, y1, x2, y2, color: QColor = QColor("black")):
        LineResizableMixin.__init__(self)
        QGraphicsLineItem.__init__(self, x1, y1, x2, y2)
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


class FreehandPath(ResizableMixin, SnapToGridMixin, QGraphicsPathItem):
    """
    Tracé libre.
    Utilisez `from_points` pour construire à partir d’une liste de QPointF.
    """

    def __init__(
        self, path=None, pen_color: QColor = QColor("black"), pen_width: int = 2
    ):
        ResizableMixin.__init__(self)
        QGraphicsPathItem.__init__(self)
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


class TextItem(ResizableMixin, SnapToGridMixin, QGraphicsTextItem):
    """Bloc de texte éditable, déplaçable et redimensionnable."""

    def __init__(
        self,
        x: float,
        y: float,
        text: str = "",
        font_size: int = 12,
        color: QColor = QColor("black"),
    ):
        ResizableMixin.__init__(self)
        QGraphicsTextItem.__init__(self, text)
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

    def rect(self):
        return self.boundingRect()

    def setRect(self, x, y, w, h):
        self.setPos(x, y)
        self.setTextWidth(w)
        br = self.boundingRect()
        if br.height() != 0:
            self.setScale(h / br.height())


class ImageItem(ResizableMixin, SnapToGridMixin, QGraphicsPixmapItem):
    """Image insérée dans le canvas."""

    def __init__(self, x: float, y: float, path: str):
        self.path = path
        pix = QPixmap(path)
        ResizableMixin.__init__(self)
        QGraphicsPixmapItem.__init__(self, pix)
        self._orig_pixmap = pix
        self.setPos(x, y)
        self.setFlags(
            QGraphicsPixmapItem.ItemIsMovable
            | QGraphicsPixmapItem.ItemIsSelectable
            | QGraphicsPixmapItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

    def rect(self):
        return QRectF(0, 0, self.pixmap().width(), self.pixmap().height())

    def setRect(self, x, y, w, h):
        self.setPos(x, y)
        if w > 0 and h > 0:
            scaled = self._orig_pixmap.scaled(
                w,
                h,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.setPixmap(scaled)
