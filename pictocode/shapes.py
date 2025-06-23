# pictocode/shapes.py

from PyQt5.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsTextItem,
    QGraphicsPixmapItem,
    QGraphicsItem,
)
from PyQt5.QtGui import (
    QPen,
    QBrush,
    QColor,
    QPainterPath,
    QPainter,
    QFont,
    QPixmap,
    QTransform,
    QPolygonF,
    QCursor,
)
import math
from PyQt5.QtCore import Qt, QPointF, QRectF
import logging

logger = logging.getLogger(__name__)


_cursor_cache: dict[int, QCursor] = {}


def _resize_cursor(angle: float) -> QCursor:
    """Return a double arrow cursor rotated to the given angle."""
    key = int(round(angle)) % 360
    if key not in _cursor_cache:
        size = 32
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(size / 2, size / 2)
        painter.rotate(key)
        pen = QPen(Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)
        l = size / 4
        head = 6
        p1 = QPointF(-l, 0)
        p2 = QPointF(l, 0)
        painter.drawLine(p1, p2)
        painter.drawLine(p1, QPointF(-l + head, -head))
        painter.drawLine(p1, QPointF(-l + head, head))
        painter.drawLine(p2, QPointF(l - head, -head))
        painter.drawLine(p2, QPointF(l - head, head))
        painter.end()
        _cursor_cache[key] = QCursor(pix, size // 2, size // 2)
    return _cursor_cache[key]


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
            logger.debug(
                f"{getattr(self, 'layer_name', type(self).__name__)} moving to "
                f"{value.x():.1f},{value.y():.1f}"
            )
        elif change == QGraphicsItem.ItemPositionHasChanged:
            logger.debug(
                f"{getattr(self, 'layer_name', type(self).__name__)} position "
                f"changed to {value.x():.1f},{value.y():.1f}"
            )
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            logger.debug(
                f"{getattr(self, 'layer_name', type(self).__name__)} selected="
                f"{bool(value)}"
            )
        return super().itemChange(change, value)




class ResizableMixin:
    """Ajoute des poignées de redimensionnement et la logique associée."""

    handle_size = 12
    handle_color = Qt.black
    handle_shape = "circle"  # or "circle"

    rotation_handle_size = 12
    rotation_handle_color = Qt.red
    rotation_handle_shape = "circle"
    rotation_offset = 20

    def __init__(self):
        super().__init__()
        self._resizing = False
        self._rotating = False
        self._start_scene_pos = QPointF()
        self._start_rect = QRectF()
        self._start_item_pos = QPointF()
        self._start_center = QPointF()
        # 0: TL, 1: TR, 2: BR, 3: BL, 4: T, 5: R, 6: B, 7: L, 8: rotation
        self._active_handle = None
        self._start_angle = 0.0
        self._anchor_scene = QPointF()

    # ------------------------------------------------------------------
    def _corner_handles(self) -> list[QRectF]:
        """Return rectangles for the 4 corner handles."""
        r = self.rect()
        s = self.handle_size
        return [
            QRectF(r.left() - s / 2, r.top() - s / 2, s, s),
            QRectF(r.right() - s / 2, r.top() - s / 2, s, s),
            QRectF(r.right() - s / 2, r.bottom() - s / 2, s, s),
            QRectF(r.left() - s / 2, r.bottom() - s / 2, s, s),
        ]

    def _side_rects(self) -> list[QRectF]:
        """Return rectangles for the 4 side hit zones."""
        r = self.rect()
        s = self.handle_size
        return [
            QRectF(r.left(), r.top() - s / 2, r.width(), s),
            QRectF(r.right() - s / 2, r.top(), s, r.height()),
            QRectF(r.left(), r.bottom() - s / 2, r.width(), s),
            QRectF(r.left() - s / 2, r.top(), s, r.height()),
        ]

    def _rotation_rect(self) -> QRectF:
        r = self.rect()
        rot_s = self.rotation_handle_size
        return QRectF(
            r.center().x() - rot_s / 2,
            r.top() - self.rotation_offset - rot_s / 2,
            rot_s,
            rot_s,
        )

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)

    # -- Geometry ----------------------------------------------------
    def boundingRect(self):
        """Extend the base bounding rect so handles are always repainted."""
        br = super().boundingRect()
        pad = self.handle_size
        rot_pad = self.rotation_offset + self.rotation_handle_size
        return br.adjusted(-pad, -rot_pad, pad, pad)

    def shape(self):
        """Extend the shape with resize and rotation handles for hit tests."""
        path = super().shape()
        extra = QPainterPath()
        for h in self._corner_handles():
            if self.handle_shape == "circle":
                extra.addEllipse(h)
            else:
                extra.addRect(h)
        for rect in self._side_rects():
            extra.addRect(rect)

        rot_handle = self._rotation_rect()
        if self.rotation_handle_shape == "circle":
            extra.addEllipse(rot_handle)
        else:
            extra.addRect(rot_handle)

        return path.united(extra)

    def _get_anchor_point(self, handle: int, w: float, h: float) -> QPointF:
        """Return the local anchor point for a given handle index."""
        if handle == 0:
            return QPointF(w, h)
        if handle == 1:
            return QPointF(0, h)
        if handle == 2:
            return QPointF(0, 0)
        if handle == 3:
            return QPointF(w, 0)
        if handle == 4:
            return QPointF(w / 2, h)
        if handle == 5:
            return QPointF(0, h / 2)
        if handle == 6:
            return QPointF(w / 2, 0)
        return QPointF(w, h / 2)

    def _shape_path(self):
        """Return a QPainterPath representing the pure shape (without
        handles)."""
        if isinstance(self, QGraphicsPathItem):
            return QPainterPath(self.path())
        if isinstance(self, QGraphicsLineItem):
            l = self.line()
            p = QPainterPath()
            p.moveTo(l.p1())
            p.lineTo(l.p2())
            return p
        if isinstance(self, QGraphicsPolygonItem):
            p = QPainterPath()
            p.addPolygon(self.polygon())
            return p
        if hasattr(self, "rect"):
            p = QPainterPath()
            p.addRect(self.rect())
            return p
        return QPainterPath()

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            # custom selection outline following the shape
            painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self._shape_path())

            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(self.handle_color))
            for handle in self._corner_handles():
                if self.handle_shape == 'circle':
                    painter.drawEllipse(handle)
                else:
                    painter.drawRect(handle)

            rot_handle = self._rotation_rect()
            painter.setPen(QPen(self.rotation_handle_color))
            painter.setBrush(QBrush(Qt.white))
            if self.rotation_handle_shape == 'circle':
                painter.drawEllipse(rot_handle)
            else:
                painter.drawRect(rot_handle)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            r = self.rect()
            corner_handles = self._corner_handles()
            side_rects = self._side_rects()
            rot_handle = self._rotation_rect()
            for idx, handle in enumerate(corner_handles):
                if handle.contains(event.pos()):
                    self._resizing = True
                    self._active_handle = idx
                    self._start_scene_pos = event.scenePos()
                    self._start_rect = QRectF(r)
                    self._start_item_pos = QPointF(self.pos())
                    self._start_center = self.mapToScene(r.center())
                    # anchor is opposite corner or side
                    break
            else:
                for sidx, rect in enumerate(side_rects, start=4):
                    if rect.contains(event.pos()):
                        self._resizing = True
                        self._active_handle = sidx
                        self._start_scene_pos = event.scenePos()
                        self._start_rect = QRectF(r)
                        self._start_item_pos = QPointF(self.pos())
                        self._start_center = self.mapToScene(r.center())
                        break
            if self._resizing:
                anchor_local = self._get_anchor_point(self._active_handle, r.width(), r.height())
                self._anchor_scene = self.mapToScene(anchor_local)
                event.accept()
                return
            if rot_handle.contains(event.pos()):
                self._rotating = True
                self._active_handle = 8
                self._start_scene_pos = event.scenePos()
                self._start_angle = self.rotation()
                self._start_center = self.mapToScene(r.center())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            # Compute movement both in item coordinates and scene coordinates
            # to keep the handle aligned with the mouse even when the item is
            # rotated.
            start_local = self.mapFromScene(self._start_scene_pos)
            current_local = self.mapFromScene(event.scenePos())
            delta_item = current_local - start_local

            x = self._start_item_pos.x()
            y = self._start_item_pos.y()
            w = self._start_rect.width()
            h = self._start_rect.height()

            if self._active_handle == 0:  # top-left
                w -= delta_item.x()
                h -= delta_item.y()
            elif self._active_handle == 1:  # top-right
                w += delta_item.x()
                h -= delta_item.y()
            elif self._active_handle == 2:  # bottom-right
                w += delta_item.x()
                h += delta_item.y()
            elif self._active_handle == 3:  # bottom-left
                w -= delta_item.x()
                h += delta_item.y()
            elif self._active_handle == 4:  # top
                h -= delta_item.y()
            elif self._active_handle == 5:  # right
                w += delta_item.x()
            elif self._active_handle == 6:  # bottom
                h += delta_item.y()
            elif self._active_handle == 7:  # left
                w -= delta_item.x()

            if event.modifiers() & Qt.ShiftModifier and w and h:
                aspect = self._start_rect.width() / self._start_rect.height()
                if abs(w) / aspect > abs(h):
                    h = abs(w) / aspect * (1 if h >= 0 else -1)
                else:
                    w = abs(h) * aspect * (1 if w >= 0 else -1)

            angle_rad = math.radians(self.rotation())
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            origin_x = w / 2
            origin_y = h / 2

            anchor_local_new = self._get_anchor_point(self._active_handle, w, h)
            dx = cos_a * (anchor_local_new.x() - origin_x) - sin_a * (
                anchor_local_new.y() - origin_y
            )
            dy = sin_a * (anchor_local_new.x() - origin_x) + cos_a * (
                anchor_local_new.y() - origin_y
            )
            x = self._anchor_scene.x() - dx - origin_x
            y = self._anchor_scene.y() - dy - origin_y

            self.setRect(x, y, w, h)
            event.accept()
            return
        if self._rotating:
            center = self._start_center
            start_vec = self._start_scene_pos - center
            current_vec = event.scenePos() - center
            start_angle = math.degrees(
                math.atan2(start_vec.y(), start_vec.x()))
            curr_angle = math.degrees(math.atan2(
                current_vec.y(), current_vec.x()))
            self.setRotation(self._start_angle + curr_angle - start_angle)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing or self._rotating:
            self._resizing = False
            self._rotating = False
            self._active_handle = None
            self._anchor_scene = QPointF()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # -- Hover -------------------------------------------------------
    def hoverMoveEvent(self, event):
        if self.isSelected():
            pos = event.pos()
            for idx, rect in enumerate(self._corner_handles()):
                if rect.contains(pos):
                    base = 135 if idx in (0, 2) else 45
                    angle = base + self.rotation()
                    self.setCursor(_resize_cursor(angle))
                    return
            for idx, rect in enumerate(self._side_rects(), start=4):
                if rect.contains(pos):
                    base = {4: 90, 5: 0, 6: -90, 7: 180}[idx]
                    angle = base + self.rotation()
                    self.setCursor(_resize_cursor(angle))
                    return
            if self._rotation_rect().contains(pos):
                self.setCursor(Qt.CrossCursor)
                return
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)


class Rect(ResizableMixin, SnapToGridMixin, QGraphicsRectItem):
    """Rectangle déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x, y, w, h, color: QColor = QColor("black")):
        # Initialise explicitement les différentes bases pour
        # éviter que ``ResizableMixin`` ne reçoive des arguments
        # inattendus via ``super()``.
        ResizableMixin.__init__(self)
        QGraphicsRectItem.__init__(self, 0, 0, w, h)
        self.setPos(x, y)
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
        self.var_name = ""
        self.setToolTip("Clique droit pour modifier")
        self.setTransformOriginPoint(w / 2, h / 2)

    def rect(self):
        return QGraphicsRectItem.rect(self)

    def setRect(self, x, y, w, h):
        r = QRectF(x, y, w, h).normalized()
        QGraphicsRectItem.setRect(self, 0, 0, r.width(), r.height())
        self.setPos(r.x(), r.y())
        self.setTransformOriginPoint(r.width() / 2, r.height() / 2)


class Ellipse(ResizableMixin, SnapToGridMixin, QGraphicsEllipseItem):
    """Ellipse déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x, y, w, h, color: QColor = QColor("black")):
        ResizableMixin.__init__(self)
        QGraphicsEllipseItem.__init__(self, 0, 0, w, h)
        self.setPos(x, y)
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
        self.var_name = ""
        self.setToolTip("Clique droit pour modifier")
        self.setTransformOriginPoint(w / 2, h / 2)

    def rect(self):
        return QGraphicsEllipseItem.rect(self)

    def setRect(self, x, y, w, h):
        r = QRectF(x, y, w, h).normalized()
        QGraphicsEllipseItem.setRect(self, 0, 0, r.width(), r.height())
        self.setPos(r.x(), r.y())
        self.setTransformOriginPoint(r.width() / 2, r.height() / 2)


class Triangle(ResizableMixin, SnapToGridMixin, QGraphicsPolygonItem):
    """Triangle déplaçable, sélectionnable et redimensionnable."""

    def __init__(self, x, y, w, h, color: QColor = QColor("black")):
        ResizableMixin.__init__(self)
        QGraphicsPolygonItem.__init__(self)
        self.setPos(x, y)
        pen = QPen(color)
        pen.setWidth(2)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.white))
        self.setFlags(
            QGraphicsPolygonItem.ItemIsMovable
            | QGraphicsPolygonItem.ItemIsSelectable
            | QGraphicsPolygonItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.var_name = ""
        self.setToolTip("Clique droit pour modifier")
        self.setTransformOriginPoint(w / 2, h / 2)
        self._w = w
        self._h = h
        self.setRect(0, 0, w, h)

    def rect(self):
        return QRectF(0, 0, self._w, self._h)

    def setRect(self, x, y, w, h):
        r = QRectF(x, y, w, h).normalized()
        self._w, self._h = r.width(), r.height()
        poly = QPolygonF(
            [
                QPointF(r.width() / 2, 0),
                QPointF(r.width(), r.height()),
                QPointF(0, r.height()),
            ]
        )
        self.setPolygon(poly)
        self.setPos(r.x(), r.y())
        self.setTransformOriginPoint(r.width() / 2, r.height() / 2)


class LineResizableMixin:
    """Ajoute des poignées de redimensionnement pour les lignes."""

    handle_size = 12

    def __init__(self):
        super().__init__()
        self._resizing = False
        self._active = None
        self._start_scene_pos = QPointF()
        self._start_line = None

    def _handle_rects(self) -> list[QRectF]:
        line = self.line()
        s = self.handle_size
        return [
            QRectF(line.p1().x() - s / 2, line.p1().y() - s / 2, s, s),
            QRectF(line.p2().x() - s / 2, line.p2().y() - s / 2, s, s),
        ]

    def shape(self):
        path = QGraphicsLineItem.shape(self)
        extra = QPainterPath()
        for h in self._handle_rects():
            extra.addRect(h)
        return path.united(extra)

    def paint(self, painter, option, widget=None):
        # Draw the line without the default Qt selection rectangle.
        painter.setPen(self.pen())
        painter.drawLine(self.line())
        if self.isSelected():
            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(Qt.black))
            for h in self._handle_rects():
                painter.drawRect(h)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSelected():
            for idx, h in enumerate(self._handle_rects()):
                if h.contains(event.pos()):
                    self._resizing = True
                    self._active = idx
                    self._start_scene_pos = event.scenePos()
                    self._start_line = self.line()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.scenePos() - self._start_scene_pos
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

    def hoverMoveEvent(self, event):
        if self.isSelected():
            pos = event.pos()
            for idx, rect in enumerate(self._handle_rects()):
                if rect.contains(pos):
                    self.setCursor(Qt.SizeAllCursor)
                    return
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)


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
        self.var_name = ""
        self.setToolTip("Clique droit pour modifier")
        br = self.boundingRect()
        self.setTransformOriginPoint(br.center())


class FreehandPath(ResizableMixin, SnapToGridMixin, QGraphicsPathItem):
    """
    Tracé libre.
    Utilisez `from_points` pour construire à partir d’une liste de QPointF.
    """

    def __init__(
        self,
        path=None,
        pen_color: QColor = QColor("black"),
        pen_width: int = 2,
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
        self.var_name = ""
        self.setToolTip("Clique droit pour modifier")
        br = self.boundingRect()
        self.setTransformOriginPoint(br.width() / 2, br.height() / 2)

    def rect(self):
        return self.path().boundingRect()

    def setRect(self, x, y, w, h):
        br = self.path().boundingRect()
        if br.width() == 0 or br.height() == 0:
            return
        sx = w / br.width()
        sy = h / br.height()
        transform = QTransform()
        transform.scale(sx, sy)
        new_path = transform.map(self.path())
        self.setPath(new_path)
        self.setPos(x, y)
        self.setTransformOriginPoint(w / 2, h / 2)

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
        self.var_name = ""
        self.alignment = "left"
        self.setToolTip("Clique droit pour modifier")
        br = self.boundingRect()
        self.setTransformOriginPoint(br.width() / 2, br.height() / 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            view = self.scene().views()[0] if self.scene().views() else None
            if view and getattr(view, "snap_to_grid", False):
                scale = view.transform().m11() or 1
                grid = view.grid_size / scale
                value.setX(round(value.x() / grid) * grid)
                value.setY(round(value.y() / grid) * grid)
            logger.debug(
                f"{getattr(self, 'layer_name', type(self).__name__)} moving to "
                f"{value.x():.1f},{value.y():.1f}"
            )
        elif change == QGraphicsItem.ItemPositionHasChanged:
            logger.debug(
                f"{getattr(self, 'layer_name', type(self).__name__)} position "
                f"changed to {value.x():.1f},{value.y():.1f}"
            )

        elif change == QGraphicsItem.ItemSelectedHasChanged:
            logger.debug(
                f"{getattr(self, 'layer_name', type(self).__name__)} selected="
                f"{bool(value)}"
            )

        return super().itemChange(change, value)

    def rect(self):
        return self.boundingRect()

    def setRect(self, x, y, w, h):
        self.setPos(x, y)
        self.setTextWidth(w)
        br = self.boundingRect()
        if br.height() != 0:
            self.setScale(h / br.height())
        self.setTransformOriginPoint(w / 2, h / 2)


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
        self.setTransformOriginPoint(pix.width() / 2, pix.height() / 2)
        self.var_name = ""

    def rect(self):
        return QRectF(0, 0, self.pixmap().width(), self.pixmap().height())

    def setRect(self, x, y, w, h):
        self.setPos(x, y)
        if w > 0 and h > 0:
            scaled = self._orig_pixmap.scaled(
                int(round(w)),
                int(round(h)),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.setPixmap(scaled)
        self.setTransformOriginPoint(w / 2, h / 2)
