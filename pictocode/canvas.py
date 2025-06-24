# pictocode/canvas.py
# -*- coding: utf-8 -*-

import math
import logging
from PyQt5.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QAction,
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsObject,
)
from .ui.animated_menu import AnimatedMenu
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QPainter,
    QColor,
    QPen,
    QImage,
    QPainterPath,
    QPdfWriter,
    QTransform,
)
from collections import OrderedDict
from .shapes import Rect, Ellipse, Line, Triangle, FreehandPath, TextItem, ImageItem
logger = logging.getLogger(__name__)
from .utils import to_pixels


class TransparentItemGroup(QGraphicsObject):
    """Lightweight container that keeps children individually selectable."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Avoid painting anything while still providing a bounding rect
        self.setFlag(QGraphicsItem.ItemHasNoContents, True)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def addToGroup(self, item: QGraphicsItem):
        """Add item to this group without disabling its interactivity."""
        self.prepareGeometryChange()
        item.setParentItem(self)
        item.setFlag(QGraphicsItem.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        logger.debug(

            "Added %s to %s flags=0x%x enabled=%s",
            getattr(item, "layer_name", type(item).__name__),
            getattr(self, "layer_name", "group"),
            int(item.flags()),
            self.isEnabled(),

        )

    def removeFromGroup(self, item: QGraphicsItem):
        """Remove an item from this group."""
        if item.parentItem() is self:
            self.prepareGeometryChange()
            item.setParentItem(None)

    def boundingRect(self):
        return self.childrenBoundingRect()


    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            logger.debug(
                f"Group {getattr(self, 'layer_name', '')} selected={bool(value)}"
            )
            if hasattr(self, "setHandlesChildEvents"):
                self.setHandlesChildEvents(bool(value))
            if hasattr(self, "setFiltersChildEvents"):
                self.setFiltersChildEvents(bool(value))
            # Forward events to the children when not selected so they remain
            # individually selectable.
            self.setAcceptedMouseButtons(
                Qt.AllButtons if value else Qt.NoButton
            )
        return super().itemChange(change, value)

    def shape(self):
        """Return an empty path when not selected so children get events."""
        if self.isSelected():
            path = QPainterPath()
            path.addRect(self.boundingRect())
            return path
        return QPainterPath()


    def mousePressEvent(self, event):
        if self.isSelected():
            super().mousePressEvent(event)
        else:
            event.ignore()












class CanvasScene(QGraphicsScene):
    """QGraphicsScene emitting signals when items are added or removed."""

    itemAdded = pyqtSignal()
    itemRemoved = pyqtSignal()

    def __init__(self, *args, throttle_interval: int = 100, **kwargs):
        super().__init__(*args, **kwargs)
        self._throttle_interval = throttle_interval
        self._add_timer = QTimer(self)
        self._add_timer.setSingleShot(True)
        self._add_timer.timeout.connect(self.itemAdded)
        self._remove_timer = QTimer(self)
        self._remove_timer.setSingleShot(True)
        self._remove_timer.timeout.connect(self.itemRemoved)

    def addItem(self, item):
        super().addItem(item)
        self._add_timer.start(self._throttle_interval)

    def removeItem(self, item):
        super().removeItem(item)
        self._remove_timer.start(self._throttle_interval)


class CanvasWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("CanvasWidget initialized")

        # Scène
        self.scene = CanvasScene(self)
        self.setScene(self.scene)
        self.scene.itemAdded.connect(self._schedule_scene_changed)
        self.scene.itemRemoved.connect(self._schedule_scene_changed)

        # Hide default scroll bars for a cleaner look
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Timer to throttle layer updates when many changes occur
        self._scene_changed_timer = QTimer(self)
        self._scene_changed_timer.setSingleShot(True)
        self._scene_changed_timer.setInterval(100)
        self._scene_changed_timer.timeout.connect(self._on_scene_changed)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)

        # Outil actif
        self.current_tool = None
        self._start_pos = None
        self._freehand_points = None
        self._temp_item = None
        self._current_path_item = None
        self._polygon_points = None
        self._polygon_item = None
        self._poly_preview_line = None
        self.pen_color = QColor("black")
        self._new_item_z = 0

        # Key modifier to allow drawing over an existing item
        # (configurable via parent if needed)
        self.override_select_modifier = Qt.ShiftModifier

        # Grille et magnétisme
        # grid_size correspond à l’écart en pixels à l’échelle 1:1
        self.grid_size = 50
        self.show_grid = True
        self.snap_to_grid = False

        # Anti-aliasing
        self.setRenderHint(QPainter.Antialiasing)

        # Pan & Zoom
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._prev_drag_mode = None
        self._middle_pan = False
        self._pan_start = None

        # Cadre de la zone de travail (sera redessiné par new_document)
        self._doc_rect = QRectF(0, 0, 800, 800)
        self._frame_item = None
        self._draw_doc_frame()

        # sélection -> inspecteur
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.scene.changed.connect(lambda _: self._schedule_scene_changed())

        # Historique pour annuler/rétablir
        self._history = []
        self._history_index = -1
        self._loading_snapshot = False
        self._name_counters = {}

        # Gestion des calques
        self.layers = OrderedDict()
        self.current_layer = None
        self.lock_others = False
        self.create_layer("Layer 1")

    def _draw_doc_frame(self):
        """Dessine le contour en pointillés de la zone de travail."""
        if self._frame_item:
            self.scene.removeItem(self._frame_item)
        pen = QPen(QColor(200, 200, 200), 2, Qt.DashLine)
        self._frame_item = self.scene.addRect(self._doc_rect, pen)
        self._frame_item.setZValue(-1)

    # ------------------------------------------------------------------
    def _register_name(self, name: str):
        try:
            base, num = name.rsplit(" ", 1)
            num = int(num)
        except ValueError:
            base, num = name, 0
        base = base.lower()
        self._name_counters[base] = max(self._name_counters.get(base, 0), num)

    def _assign_layer_name(self, item, base: str | None = None):
        if base is None:
            base = type(item).__name__.lower()
        count = self._name_counters.get(base, 0) + 1
        self._name_counters[base] = count
        item.layer_name = f"{base} {count}"

    def set_tool(self, tool_name: str):
        """Définit l’outil courant depuis la toolbar."""
        logger.debug(f"Tool set to {tool_name}")
        self.current_tool = tool_name
        if tool_name == "pan":
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
        if tool_name != "freehand":
            self._freehand_points = None
            if self._current_path_item:
                self.scene.removeItem(self._current_path_item)
                self._current_path_item = None
        if tool_name != "polygon" and self._polygon_item:
            self.scene.removeItem(self._polygon_item)
            self._polygon_item = None
            if self._poly_preview_line:
                self.scene.removeItem(self._poly_preview_line)
                self._poly_preview_line = None
            self._polygon_points = None
        if self._temp_item:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None

    def new_document(
        self, width, height, unit, orientation, color_mode, dpi, name=""
    ):
        """
        Initialise un nouveau document selon les paramètres donnés.
        width/height en unité choisie, orientation et dpi sont pris en
        logger.debug(f"New document {width}x{height}{unit}")
        compte ici.
        """
        w = to_pixels(width, unit, dpi)
        h = to_pixels(height, unit, dpi)
        if orientation == "landscape" and h > w:
            w, h = h, w
        elif orientation == "portrait" and w > h:
            w, h = h, w
        self.scene.clear()
        self._frame_item = None
        self._name_counters = {}
        self.layers.clear()
        self.current_layer = None
        self.create_layer("Layer 1")
        self._doc_rect = QRectF(0, 0, w, h)
        self._draw_doc_frame()
        self.setSceneRect(self._doc_rect.adjusted(-500, -500, 500, 500))
        self.current_meta = {
            "name": name,
            "width": width,
            "height": height,
            "unit": unit,
            "orientation": orientation,
            "color_mode": color_mode,
            "dpi": dpi,
        }
        window = self.window()

        if not self._loading_snapshot:
            self._snapshot()
        if hasattr(window, "layout"):
            window.layout.populate()

    def update_document_properties(
        self, width, height, unit, orientation, color_mode, dpi, name=""
    ):
        """Met à jour les paramètres du document sans toucher aux formes."""
        w = to_pixels(width, unit, dpi)
        h = to_pixels(height, unit, dpi)
        if orientation == "landscape" and h > w:
            w, h = h, w
        elif orientation == "portrait" and w > h:
            w, h = h, w
        self._doc_rect = QRectF(0, 0, w, h)
        self._draw_doc_frame()
        self.setSceneRect(self._doc_rect.adjusted(-500, -500, 500, 500))
        if not hasattr(self, "current_meta"):
            self.current_meta = {}
        self.current_meta.update(
            {
                "name": name or self.current_meta.get("name", ""),
                "width": width,
                "height": height,
                "unit": unit,
                "orientation": orientation,
                "color_mode": color_mode,
                "dpi": dpi,
            }
        )

    def load_shapes(self, shapes):
        """Charge depuis une liste de dicts (issue de export_project)."""
        self.scene.blockSignals(True)
        logger.debug(f"Loading {len(shapes)} shapes")
        for s in shapes:
            self._create_item(s)
        self.scene.blockSignals(False)
        # Ensure layer and layout views stay in sync with the scene
        self._schedule_scene_changed()


    def export_project(self):
        """
        Exporte la meta (self.current_meta) + toutes les formes en dict.
        Prêt à sérialiser en JSON.
        """
        shapes = []
        logger.debug("Exporting project")
        for item in reversed(self.scene.items()):
            if item is self._frame_item:
                continue
            data = self._serialize_item(item)
            if data:
                shapes.append(data)
        meta = getattr(self, "current_meta", {})
        layers = [
            {
                "name": name,
                "visible": layer.isVisible(),
                "locked": getattr(layer, "locked", False),
            }
            for name, layer in self.layers.items()
        ]
        return {**meta, "shapes": shapes, "layers": layers}

    def export_image(self, path: str, img_format: str = "PNG"):
        """Enregistre la scène actuelle dans un fichier image."""
        w = int(self._doc_rect.width())
        logger.debug(f"Exporting image to {path}")
        h = int(self._doc_rect.height())
        image = QImage(w, h, QImage.Format_ARGB32)
        image.fill(Qt.white)
        painter = QPainter(image)
        self.scene.render(painter, QRectF(0, 0, w, h), self._doc_rect)
        painter.end()
        image.save(path, img_format)

    def export_svg(self, path: str):
        """Enregistre la scène actuelle au format SVG (très basique)."""
        from xml.etree.ElementTree import Element, SubElement, ElementTree
        logger.debug(f"Exporting SVG to {path}")

        w = int(self._doc_rect.width())
        h = int(self._doc_rect.height())
        root = Element(
            "svg",
            xmlns="http://www.w3.org/2000/svg",
            width=str(w),
            height=str(h),
        )

        for item in reversed(self.scene.items()):
            if item is self._frame_item:
                continue
            cls = type(item).__name__
            stroke = (
                item.pen().color().name()
                if hasattr(item, "pen")
                else "#000000"
            )

            if cls == "Rect":
                r = item.rect()
                SubElement(
                    root,
                    "rect",
                    x=str(r.x()),
                    y=str(r.y()),
                    width=str(r.width()),
                    height=str(r.height()),
                    fill="none",
                    stroke=stroke,
                )
            elif cls == "Ellipse":
                e = item.rect()
                cx = e.x() + e.width() / 2
                cy = e.y() + e.height() / 2
                SubElement(
                    root,
                    "ellipse",
                    cx=str(cx),
                    cy=str(cy),
                    rx=str(e.width() / 2),
                    ry=str(e.height() / 2),
                    fill="none",
                    stroke=stroke,
                )
            elif cls == "Line":
                line = item.line()
                SubElement(
                    root,
                    "line",
                    x1=str(line.x1()),
                    y1=str(line.y1()),
                    x2=str(line.x2()),
                    y2=str(line.y2()),
                    stroke=stroke,
                )
            elif cls == "FreehandPath":
                path = item.path()
                pts = [
                    path.elementAt(i)
                    for i in range(path.elementCount())
                ]
                if (
                    len(pts) > 2
                    and pts[0].x == pts[-1].x
                    and pts[0].y == pts[-1].y
                ):
                    points = " ".join(f"{p.x},{p.y}" for p in pts[:-1])
                    SubElement(
                        root,
                        "polygon",
                        points=points,
                        fill="none",
                        stroke=stroke,
                    )
                else:
                    cmds = []
                    for i, ept in enumerate(pts):
                        cmd = "M" if i == 0 else "L"
                        cmds.append(f"{cmd}{ept.x} {ept.y}")
                    SubElement(
                        root,
                        "path",
                        d=" ".join(cmds),
                        fill="none",
                        stroke=stroke,
                    )
            elif cls == "TextItem":
                SubElement(
                    root,
                    "text",
                    x=str(item.x()),
                    y=str(item.y() + item.font().pointSize()),
                    fill=item.defaultTextColor().name(),
                    **{"font-size": str(item.font().pointSize())},
                ).text = item.toPlainText()

        ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

    # ─── Pan & Zoom ────────────────────────────────────────────────────
    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, QTransform())
        item_name = getattr(item, "layer_name", type(item).__name__ if item else None)
        logger.debug(
            f"Mouse press {event.button()} at {scene_pos.x():.1f},{scene_pos.y():.1f} "
            f"tool={self.current_tool} item={item_name}"
        )
        if item:
            flags = int(item.flags())
            logger.debug(

                "Item flags=0x%x movable=%s selectable=%s enabled=%s",
                flags,
                bool(flags & QGraphicsItem.ItemIsMovable),
                bool(flags & QGraphicsItem.ItemIsSelectable),
                item.isEnabled(),
            )
            parent = item.parentItem()
            if parent:
                logger.debug(
                    "Parent %s enabled=%s",
                    getattr(parent, "layer_name", type(parent).__name__),
                    parent.isEnabled(),
                )

        if self.current_tool == "pan":
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MiddleButton:
            # Déplacement temporaire avec le clic molette
            self._prev_drag_mode = self.dragMode()
            self.setDragMode(QGraphicsView.NoDrag)
            self._middle_pan = True
            self._pan_start = event.pos()
        elif event.button() == Qt.LeftButton:
            if self.snap_to_grid:
                scale = self.transform().m11() or 1
                grid = self.grid_size / scale
                scene_pos.setX(round(scene_pos.x() / grid) * grid)
                scene_pos.setY(round(scene_pos.y() / grid) * grid)
            base_item = self.scene.itemAt(scene_pos, QTransform())
            # Walk up the hierarchy to find the nearest selectable ancestor
            # so clicking a child of a group selects that child unless the
            # group itself is selectable (e.g. when grouping shapes).
            item = base_item
            while (
                item
                and not (item.flags() & QGraphicsItem.ItemIsSelectable)
                and item.parentItem() is not None
            ):
                item = item.parentItem()
            base_item = item
            if base_item is self._frame_item:
                base_item = None
            # Select existing items unless Shift is held to override or using
            # the erase tool, so clicking a shape works regardless of the
            # current tool.
            if (
                base_item
                and self.current_tool != "erase"
                and not (event.modifiers() & self.override_select_modifier)
            ):
                super().mousePressEvent(event)
                return
            if base_item:
                self._new_item_z = base_item.zValue() + 0.1
            else:
                existing = [
                    it.zValue()
                    for it in self.scene.items()
                    if it is not self._frame_item
                ]
                self._new_item_z = (min(existing) if existing else 0) - 0.1
            if self.current_tool == "erase":
                items = self.scene.items(scene_pos)
                if items and items[0] is not self._frame_item:
                    self.scene.removeItem(items[0])
                    self._mark_dirty()
                    self._schedule_scene_changed()
            elif self.current_tool in ("rect", "ellipse", "line", "triangle"):
                items = [
                    it
                    for it in self.scene.items(scene_pos)
                    if it is not self._frame_item
                ]
                if items and not (
                    event.modifiers() & self.override_select_modifier
                ):
                    super().mousePressEvent(event)
                    return
                self._start_pos = scene_pos
                if self.current_tool == "rect":
                    self._temp_item = Rect(
                        scene_pos.x(), scene_pos.y(), 0, 0, self.pen_color
                    )
                elif self.current_tool == "ellipse":
                    self._temp_item = Ellipse(
                        scene_pos.x(), scene_pos.y(), 0, 0, self.pen_color
                    )
                elif self.current_tool == "line":
                    self._temp_item = Line(
                        scene_pos.x(),
                        scene_pos.y(),
                        scene_pos.x(),
                        scene_pos.y(),
                        self.pen_color,
                    )
                elif self.current_tool == "triangle":
                    self._temp_item = Triangle(
                        scene_pos.x(), scene_pos.y(), 0, 0, self.pen_color
                    )
                if self._temp_item:
                    self._temp_item.setZValue(self._new_item_z)
                    self._temp_item.setOpacity(0.6)
                    self.scene.addItem(self._temp_item)
            elif self.current_tool == "text":
                item = TextItem(scene_pos.x(), scene_pos.y(),
                                "Texte", 12, self.pen_color)
                item.setZValue(self._new_item_z)
                self.scene.addItem(item)
                if self.current_layer:
                    self.current_layer.addToGroup(item)
                    item.layer = self.current_layer.layer_name
                self._assign_layer_name(item)
                self.scene.clearSelection()
                item.setSelected(True)
                item.setTextInteractionFlags(Qt.TextEditorInteraction)
                self._mark_dirty()
                self._schedule_scene_changed()
            elif self.current_tool == "polygon":
                if self._polygon_points is None:
                    self._polygon_points = [scene_pos]
                    path = QPainterPath(scene_pos)
                    self._polygon_item = FreehandPath(path, self.pen_color, 2)
                    self._polygon_item.setZValue(self._new_item_z)
                    self._polygon_item.setOpacity(0.6)
                    self.scene.addItem(self._polygon_item)
                    self._poly_preview_line = Line(
                        scene_pos.x(),
                        scene_pos.y(),
                        scene_pos.x(),
                        scene_pos.y(),
                        self.pen_color,
                    )
                    self._poly_preview_line.setZValue(self._new_item_z)
                    self._poly_preview_line.setOpacity(0.6)
                    self.scene.addItem(self._poly_preview_line)
                else:
                    self._polygon_points.append(scene_pos)
                    path = self._polygon_item.path()
                    path.lineTo(scene_pos)
                    self._polygon_item.setPath(path)
                    self._poly_preview_line.setLine(
                        scene_pos.x(),
                        scene_pos.y(),
                        scene_pos.x(),
                        scene_pos.y(),
                    )
            elif self.current_tool == "freehand":
                self._freehand_points = [scene_pos]
                self._current_path_item = FreehandPath.from_points(
                    self._freehand_points, self.pen_color, 2
                )
                self._current_path_item.setZValue(self._new_item_z)
                self._current_path_item.setOpacity(0.6)
                self.scene.addItem(self._current_path_item)
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event)
            return
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            sel = [
                getattr(it, "layer_name", type(it).__name__)
                for it in self.scene.selectedItems()
            ]
            logger.debug(f"Selection after press: {sel}")
            if item and not sel:
                logger.debug(
                    "Clicked %s but nothing selected; layer enabled=%s",
                    getattr(item, "layer_name", type(item).__name__),
                    item.isEnabled(),
                )


    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        logger.debug(
            f"Mouse move to {scene_pos.x():.1f},{scene_pos.y():.1f} "
            f"buttons={int(event.buttons())} tool={self.current_tool}"
        )

        if self.current_tool == "pan":
            super().mouseMoveEvent(event)
            return
        if self._middle_pan:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            return
        scene_pos = self.mapToScene(event.pos())
        if self.snap_to_grid:
            scale = self.transform().m11() or 1
            grid = self.grid_size / scale
            scene_pos.setX(round(scene_pos.x() / grid) * grid)
            scene_pos.setY(round(scene_pos.y() / grid) * grid)
        if self.current_tool == "polygon" and self._polygon_points:
            last = self._polygon_points[-1]
            self._poly_preview_line.setLine(
                last.x(), last.y(), scene_pos.x(), scene_pos.y()
            )
        elif (
            self.current_tool == "freehand"
            and self._freehand_points is not None
        ):
            self._freehand_points.append(scene_pos)
            if self._current_path_item:
                path = self._current_path_item.path()
                if path.elementCount() == 0:
                    path.moveTo(self._freehand_points[0])
                path.lineTo(scene_pos)
                self._current_path_item.setPath(path)
        elif self._temp_item and self._start_pos:
            x0, y0 = self._start_pos.x(), self._start_pos.y()
            if self.current_tool in ("rect", "ellipse", "triangle"):
                rect = QRectF(x0, y0, scene_pos.x() - x0,
                              scene_pos.y() - y0).normalized()
                self._temp_item.setRect(
                    rect.x(), rect.y(), rect.width(), rect.height()
                )
            elif self.current_tool == "line":
                self._temp_item.setLine(x0, y0, scene_pos.x(), scene_pos.y())
            return
        super().mouseMoveEvent(event)
        for it in self.scene.selectedItems():
            pos = it.pos()
            logger.debug(
                f"Selected {getattr(it, 'layer_name', type(it).__name__)} "
                f"at {pos.x():.1f},{pos.y():.1f}"
            )

    def mouseReleaseEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        logger.debug(
            f"Mouse release {event.button()} at {scene_pos.x():.1f},{scene_pos.y():.1f} "
            f"tool={self.current_tool}"
        )
        if self.current_tool == "pan":
            super().mouseReleaseEvent(event)
            return
        if self._middle_pan and event.button() == Qt.MiddleButton:
            self._middle_pan = False
            self.setDragMode(self._prev_drag_mode or QGraphicsView.NoDrag)
            return
        if self.snap_to_grid:
            scale = self.transform().m11() or 1
            grid = self.grid_size / scale
            scene_pos.setX(round(scene_pos.x() / grid) * grid)
            scene_pos.setY(round(scene_pos.y() / grid) * grid)
        if self.current_tool == "polygon" and self._polygon_points:
            self._polygon_points.append(scene_pos)
            path = self._polygon_item.path()
            path.lineTo(scene_pos)
            self._polygon_item.setPath(path)
            self._poly_preview_line.setLine(
                scene_pos.x(), scene_pos.y(), scene_pos.x(), scene_pos.y()
            )
        elif self.current_tool == "freehand" and self._freehand_points:
            self._freehand_points.append(scene_pos)
            if self._current_path_item:
                path = self._current_path_item.path()
                if path.elementCount() == 0:
                    path.moveTo(self._freehand_points[0])
                path.lineTo(scene_pos)
                self._current_path_item.setPath(path)
                self._current_path_item.setOpacity(1.0)
                self._assign_layer_name(self._current_path_item)
                if self.current_layer:
                    self.current_layer.addToGroup(self._current_path_item)
                    self._current_path_item.layer = self.current_layer.layer_name
                self.scene.clearSelection()
                self._current_path_item.setSelected(True)
            self._current_path_item = None
            self._freehand_points = None
            self._mark_dirty()
            self._schedule_scene_changed()
        elif self._temp_item and self._start_pos:
            x0, y0 = self._start_pos.x(), self._start_pos.y()
            if self.current_tool in ("rect", "ellipse", "triangle"):
                rect = QRectF(x0, y0, scene_pos.x() - x0,
                              scene_pos.y() - y0).normalized()
                self._temp_item.setRect(
                    rect.x(), rect.y(), rect.width(), rect.height()
                )
            elif self.current_tool == "line":
                self._temp_item.setLine(x0, y0, scene_pos.x(), scene_pos.y())
            self._temp_item.setOpacity(1.0)
            self._assign_layer_name(self._temp_item)
            if self.current_layer:
                self.current_layer.addToGroup(self._temp_item)
                self._temp_item.layer = self.current_layer.layer_name
            self.scene.clearSelection()
            self._temp_item.setSelected(True)
            self._temp_item = None
            self._mark_dirty()
            self._schedule_scene_changed()
            self._start_pos = None
            return
        self._start_pos = None
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            sel = [
                getattr(it, "layer_name", type(it).__name__)
                for it in self.scene.selectedItems()
            ]
            logger.debug(f"Selection after release: {sel}")
            for it in self.scene.selectedItems():
                pos = it.pos()
                logger.debug(
                    f"Selected {getattr(it, 'layer_name', type(it).__name__)} "
                    f"at {pos.x():.1f},{pos.y():.1f}"
                )


    def mouseDoubleClickEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        if self.snap_to_grid:
            scale = self.transform().m11() or 1
            grid = self.grid_size / scale
            scene_pos.setX(round(scene_pos.x() / grid) * grid)
            scene_pos.setY(round(scene_pos.y() / grid) * grid)
        items = self.scene.items(scene_pos)
        if self.current_tool == "polygon" and self._polygon_points:
            self._polygon_points.append(scene_pos)
            path = self._polygon_item.path()
            path.lineTo(scene_pos)
            path.closeSubpath()
            self._polygon_item.setPath(path)
            self._polygon_item.setOpacity(1.0)
            self._assign_layer_name(self._polygon_item)
            if self.current_layer:
                self.current_layer.addToGroup(self._polygon_item)
                self._polygon_item.layer = self.current_layer.layer_name
            self.scene.clearSelection()
            self._polygon_item.setSelected(True)
            self.scene.removeItem(self._poly_preview_line)
            self._poly_preview_line = None
            self._polygon_item = None
            self._polygon_points = None
            self._mark_dirty()
            self._schedule_scene_changed()
        elif items and isinstance(items[0], TextItem):
            ti = items[0]
            ti.setTextInteractionFlags(Qt.TextEditorInteraction)
            ti.setFocus()
        else:
            super().mouseDoubleClickEvent(event)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        painter.fillRect(rect, QColor(60, 60, 60))
        painter.fillRect(self._doc_rect, Qt.white)
        if not self.show_grid:
            return
        pen = QPen(QColor(220, 220, 220), 0)
        painter.setPen(pen)
        # Taille de la grille en coordonnées scène pour conserver
        # un espacement constant à l'écran malgré le zoom
        scale = self.transform().m11()
        if scale == 0:
            scale = 1
        gs = self.grid_size / scale
        r = rect.intersected(self._doc_rect)
        left = int(math.floor(r.left()))
        right = int(math.ceil(r.right()))
        top = int(math.floor(r.top()))
        bottom = int(math.ceil(r.bottom()))
        # verticales
        x = left - int(left % gs)
        while x < right:
            painter.drawLine(int(x), top, int(x), bottom)
            x += gs
        # horizontales
        y = top - int(top % gs)
        while y < bottom:
            painter.drawLine(left, int(y), right, int(y))
            y += gs

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 100))
        outer = QPainterPath()
        outer.addRect(rect)
        inner = QPainterPath()
        inner.addRect(self._doc_rect)
        painter.drawPath(outer.subtracted(inner))

    def _show_context_menu(self, event):
        menu = AnimatedMenu(self)
        scene_pos = self.mapToScene(event.pos())
        items = self.scene.items(scene_pos)
        if items:
            item = items[0]
            if hasattr(item, "pen"):
                act_color = QAction("Couleur du contour...", self)
                act_color.triggered.connect(
                    lambda: self._change_pen_color(item))
                menu.addAction(act_color)
                act_width = QAction("Épaisseur du trait...", self)
                act_width.triggered.connect(
                    lambda: self._change_pen_width(item))
                menu.addAction(act_width)
            if hasattr(item, "brush"):
                act_fill = QAction("Couleur de remplissage...", self)
                act_fill.triggered.connect(
                    lambda: self._change_brush_color(item))
                menu.addAction(act_fill)
            act_flip_h = QAction("Miroir horizontal", self)
            act_flip_h.triggered.connect(
                lambda: (
                    item.setSelected(True),
                    self.flip_horizontal_selected(),
                )
            )
            menu.addAction(act_flip_h)
            act_flip_v = QAction("Miroir vertical", self)
            act_flip_v.triggered.connect(
                lambda: (
                    item.setSelected(True),
                    self.flip_vertical_selected(),
                )
            )
            menu.addAction(act_flip_v)
            act_delete = QAction("Supprimer", self)
            act_delete.triggered.connect(
                lambda: (
                    self.scene.removeItem(item),
                    self._mark_dirty(),
                    self._schedule_scene_changed(),
                )
            )
            menu.addAction(act_delete)
            act_props = QAction("Propriétés…", self)
            menu.addAction(act_props)
        else:
            act_grid = QAction("Afficher/Masquer grille", self)
            act_grid.triggered.connect(self._toggle_grid)
            menu.addAction(act_grid)
            act_snap = QAction("Activer/Désactiver magnétisme", self)
            act_snap.triggered.connect(self._toggle_snap)
            menu.addAction(act_snap)
        menu.exec_(self.mapToGlobal(event.pos()))

    def _toggle_grid(self):
        self.show_grid = not self.show_grid
        self.viewport().update()

    def _toggle_snap(self):
        self.snap_to_grid = not self.snap_to_grid

    def set_grid_size(self, size: int):
        self.grid_size = max(1, int(size))
        self.viewport().update()

    def _change_pen_color(self, item):
        from PyQt5.QtWidgets import QColorDialog

        color = QColorDialog.getColor(item.pen().color(), self)
        if color.isValid():
            pen = item.pen()
            pen.setColor(color)
            item.setPen(pen)

    def _change_brush_color(self, item):
        from PyQt5.QtWidgets import QColorDialog

        color = QColorDialog.getColor(item.brush().color(), self)
        if color.isValid():
            brush = item.brush()
            brush.setColor(color)
            brush.setStyle(Qt.SolidPattern)
            item.setBrush(brush)

    def insert_image(self, path: str, pos: QPointF | None = None):
        if not path:
            return None
        if pos is None:
            pos = QPointF(0, 0)
        item = ImageItem(pos.x(), pos.y(), path)
        self.scene.addItem(item)
        self._assign_layer_name(item)
        self._mark_dirty()
        self._schedule_scene_changed()
        return item

    def _change_pen_width(self, item):
        from PyQt5.QtWidgets import QInputDialog

        width, ok = QInputDialog.getInt(
            self, "Épaisseur", "Largeur :", item.pen().width(), 1, 20
        )
        if ok:
            pen = item.pen()
            pen.setWidth(width)
            item.setPen(pen)

    # ─── Couleur et sélection ─────────────────────────────────────────
    def set_pen_color(self, color: QColor):
        """Définit la couleur utilisée pour les prochains objets."""
        self.pen_color = color

    def _on_selection_changed(self):
        items = self.scene.selectedItems()
        names = [getattr(it, "layer_name", type(it).__name__) for it in items]
        logger.debug(f"Selection changed: {names}")
        window = self.window()
        if hasattr(window, "inspector"):
            # reuse computed items list above
            auto_show = getattr(window, "auto_show_inspector", True)
            if items:
                window.inspector.set_target(items[0])
                if auto_show and hasattr(window, "inspector_dock"):
                    window.inspector_dock.setVisible(True)
            else:
                window.inspector.set_target(None)
                if auto_show and hasattr(window, "inspector_dock"):
                    window.inspector_dock.setVisible(False)


    def _mark_dirty(self):
        window = self.window()
        if hasattr(window, "set_dirty"):
            window.set_dirty(True)

    def _schedule_scene_changed(self):
        """Debounce calls to _on_scene_changed to avoid UI freezes."""
        self._scene_changed_timer.start()

    def _on_scene_changed(self):
        self._mark_dirty()
        window = self.window()

        # Agrandit automatiquement la zone de la scène pour permettre
        # le déplacement libre des formes en dehors du document initial.
        bounds = self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        if not bounds.contains(self._doc_rect):
            bounds = bounds.united(self._doc_rect)
            self.setSceneRect(bounds)

        if not self._loading_snapshot:
            self._snapshot()
        if hasattr(window, "layout"):
            window.layout.populate()

    # --- Clipboard / editing helpers ---------------------------------
    def _serialize_item(self, item):
        cls = type(item).__name__
        if cls == "Rect":
            r = item.rect()
            return {
                "type": "rect",
                "name": getattr(item, "layer_name", ""),
                "layer": getattr(item, "layer", ""),
                "x": item.x(),
                "y": item.y(),
                "w": r.width(),
                "h": r.height(),
                "color": item.pen().color().name(),
                "pen_width": item.pen().width(),
                "fill": item.brush().color().name(),
                "rotation": item.rotation(),
                "z": item.zValue(),
            }
        if cls == "Ellipse":
            e = item.rect()
            return {
                "type": "ellipse",
                "name": getattr(item, "layer_name", ""),
                "layer": getattr(item, "layer", ""),
                "x": item.x(),
                "y": item.y(),
                "w": e.width(),
                "h": e.height(),
                "color": item.pen().color().name(),
                "pen_width": item.pen().width(),
                "fill": item.brush().color().name(),
                "rotation": item.rotation(),
                "z": item.zValue(),
            }
        if cls == "Line":
            line = item.line()
            return {
                "type": "line",
                "name": getattr(item, "layer_name", ""),
                "layer": getattr(item, "layer", ""),
                "x": item.x(),
                "y": item.y(),
                "x1": line.x1(),
                "y1": line.y1(),
                "x2": line.x2(),
                "y2": line.y2(),
                "color": item.pen().color().name(),
                "pen_width": item.pen().width(),
                "rotation": item.rotation(),
                "z": item.zValue(),
            }
        if cls == "FreehandPath":
            path = item.path()
            pts = [
                (path.elementAt(i).x, path.elementAt(i).y)
                for i in range(path.elementCount())
            ]
            return {
                "type": "path",
                "name": getattr(item, "layer_name", ""),
                "layer": getattr(item, "layer", ""),
                "x": item.x(),
                "y": item.y(),
                "points": pts,
                "color": item.pen().color().name(),
                "pen_width": item.pen().width(),
                "fill": item.brush().color().name(),
                "rotation": item.rotation(),
                "z": item.zValue(),
            }
        if cls == "TextItem":
            return {
                "type": "text",
                "name": getattr(item, "layer_name", ""),
                "layer": getattr(item, "layer", ""),
                "x": item.x(),
                "y": item.y(),
                "text": item.toPlainText(),
                "font_size": item.font().pointSize(),
                "color": item.defaultTextColor().name(),
                "rotation": item.rotation(),
                "z": item.zValue(),
            }
        if cls == "ImageItem":
            r = item.rect()
            return {
                "type": "image",
                "name": getattr(item, "layer_name", ""),
                "layer": getattr(item, "layer", ""),
                "x": item.x(),
                "y": item.y(),
                "w": r.width(),
                "h": r.height(),
                "path": item.path,
                "rotation": item.rotation(),
                "z": item.zValue(),
            }
        return None

    def _create_item(self, data):
        t = data.get("type")
        if t == "rect":
            item = Rect(
                data["x"], data["y"], data["w"], data["h"], QColor(
                    data["color"])
            )
            pen = item.pen()
            pen.setWidth(int(data.get("pen_width", pen.width())))
            item.setPen(pen)
            brush = item.brush()
            brush.setColor(QColor(data.get("fill", brush.color().name())))
            brush.setStyle(Qt.SolidPattern)
            item.setBrush(brush)
            item.setRotation(float(data.get("rotation", 0)))
            item.setZValue(float(data.get("z", 0)))
        elif t == "ellipse":
            item = Ellipse(
                data["x"], data["y"], data["w"], data["h"], QColor(
                    data["color"])
            )
            pen = item.pen()
            pen.setWidth(int(data.get("pen_width", pen.width())))
            item.setPen(pen)
            brush = item.brush()
            brush.setColor(QColor(data.get("fill", brush.color().name())))
            brush.setStyle(Qt.SolidPattern)
            item.setBrush(brush)
            item.setRotation(float(data.get("rotation", 0)))
            item.setZValue(float(data.get("z", 0)))
        elif t == "line":
            item = Line(
                data["x1"], data["y1"], data["x2"], data["y2"], QColor(
                    data["color"])
            )
            pen = item.pen()
            pen.setWidth(int(data.get("pen_width", pen.width())))
            item.setPen(pen)
            item.setPos(float(data.get("x", 0)), float(data.get("y", 0)))
            item.setRotation(float(data.get("rotation", 0)))
            item.setZValue(float(data.get("z", 0)))
        elif t == "path":
            pts = [QPointF(p[0], p[1]) for p in data.get("points", [])]
            item = FreehandPath.from_points(
                pts, QColor(data.get("color", "black")))
            pen = item.pen()
            pen.setWidth(int(data.get("pen_width", pen.width())))
            item.setPen(pen)
            brush = item.brush()
            brush.setColor(QColor(data.get("fill", brush.color().name())))
            item.setBrush(brush)
            item.setPos(float(data.get("x", 0)), float(data.get("y", 0)))
            item.setRotation(float(data.get("rotation", 0)))
            item.setZValue(float(data.get("z", 0)))
        elif t == "text":
            item = TextItem(
                data["x"],
                data["y"],
                data.get("text", ""),
                data.get("font_size", 12),
                QColor(data.get("color", "black")),
            )
            item.setRotation(float(data.get("rotation", 0)))
            item.setZValue(float(data.get("z", 0)))
        elif t == "image":
            item = ImageItem(
                data.get("x", 0),
                data.get("y", 0),
                data.get("path", ""),
            )
            item.setRotation(float(data.get("rotation", 0)))
            item.setZValue(float(data.get("z", 0)))
        else:
            return None
        self.scene.addItem(item)
        logger.debug(
            "Created %s flags=0x%x movable=%s selectable=%s",
            type(item).__name__,
            int(item.flags()),
            bool(item.flags() & QGraphicsItem.ItemIsMovable),
            bool(item.flags() & QGraphicsItem.ItemIsSelectable),
        )
        layer = data.get("layer")
        if layer and layer in self.layers:
            self.layers[layer].addToGroup(item)
            item.layer = layer
        elif self.current_layer:
            self.current_layer.addToGroup(item)
            item.layer = self.current_layer.layer_name
        name = data.get("name")
        if name:
            item.layer_name = name
            self._register_name(name)
        else:
            self._assign_layer_name(item)
        return item

    def copy_selected(self):
        items = self.scene.selectedItems()
        if not items:
            return None
        return self._serialize_item(items[0])

    def cut_selected(self):
        data = self.copy_selected()
        if data:
            for it in self.scene.selectedItems():
                self.scene.removeItem(it)
            self._mark_dirty()
            self._schedule_scene_changed()
        return data

    def paste_item(self, data):
        if not data:
            return
        data = dict(data)
        data.pop("name", None)
        item = self._create_item(data)
        if item:
            item.setSelected(True)
            self._mark_dirty()
            self._schedule_scene_changed()

    def duplicate_selected(self):
        data = self.copy_selected()
        if not data:
            return
        if "x" in data:
            data["x"] += 10
        if "y" in data:
            data["y"] += 10
        if "x1" in data:
            data["x1"] += 10
            data["x2"] += 10
        if "y1" in data:
            data["y1"] += 10
            data["y2"] += 10
        self.paste_item(data)

    def delete_selected(self):
        for it in self.scene.selectedItems():
            self.scene.removeItem(it)
        self._mark_dirty()
        self._schedule_scene_changed()

    def select_all(self):
        for it in self.scene.items():
            if it is not self._frame_item:
                it.setSelected(True)

    def deselect_all(self):
        """Clear selection on the scene."""
        self.scene.clearSelection()

    def zoom_in(self):
        self.scale(1.25, 1.25)

    def zoom_out(self):
        self.scale(0.8, 0.8)

    # --- Flip --------------------------------------------------------
    def flip_horizontal_selected(self):
        """Flip selected items horizontally around their center."""
        items = [it for it in self.scene.selectedItems() if it is not self._frame_item]
        if not items:
            return
        for it in items:
            center = it.boundingRect().center()
            orig = it.transformOriginPoint()
            it.setTransformOriginPoint(center)
            it.scale(-1, 1)
            it.setTransformOriginPoint(orig)
        self._mark_dirty()
        self._schedule_scene_changed()

    def flip_vertical_selected(self):
        """Flip selected items vertically around their center."""
        items = [it for it in self.scene.selectedItems() if it is not self._frame_item]
        if not items:
            return
        for it in items:
            center = it.boundingRect().center()
            orig = it.transformOriginPoint()
            it.setTransformOriginPoint(center)
            it.scale(1, -1)
            it.setTransformOriginPoint(orig)
        self._mark_dirty()
        self._schedule_scene_changed()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self._temp_item:
            self.scene.removeItem(self._temp_item)
            self._temp_item = None
            self._start_pos = None
            return
        super().keyPressEvent(event)

    # --- Historique --------------------------------------------------
    def _snapshot(self):
        data = self.export_project()
        self._history = self._history[: self._history_index + 1]
        self._history.append(data)
        self._history_index += 1

    def _load_snapshot(self, snap):
        self._loading_snapshot = True
        self.new_document(
            snap.get("width", 0),
            snap.get("height", 0),
            snap.get("unit", "px"),
            snap.get("orientation", "portrait"),
            snap.get("color_mode", "RGB"),
            snap.get("dpi", 72),
            name=snap.get("name", ""),
        )
        self.setup_layers(snap.get("layers", []))
        self.load_shapes(snap.get("shapes", []))
        self._loading_snapshot = False

    def undo(self):
        if self._history_index > 0:
            self._history_index -= 1
            self._load_snapshot(self._history[self._history_index])

    def redo(self):
        if self._history_index + 1 < len(self._history):
            self._history_index += 1
            self._load_snapshot(self._history[self._history_index])

    # --- Export supplémentaires --------------------------------------
    def export_pdf(self, path: str):
        writer = QPdfWriter(path)
        writer.setResolution(96)
        writer.setPageSizeMM(
            QSizeF(self._doc_rect.width(), self._doc_rect.height())
        )
        painter = QPainter(writer)
        self.scene.render(
            painter,
            QRectF(0, 0, self._doc_rect.width(), self._doc_rect.height()),
            self._doc_rect,
        )
        painter.end()

    # --- Group management -------------------------------------------
    def group_selected(self, items=None, *, sort_items=True):
        """Regroupe les éléments sélectionnés dans un QGraphicsItemGroup.

        Parameters
        ----------
        items : list[QGraphicsItem] | None
            Éléments à grouper. Si ``None`` (par défaut), les éléments
            actuellement sélectionnés dans la scène seront utilisés.
        sort_items : bool, optional
            Si ``True``, les items seront triés de bas en haut en fonction de
            leur ``zValue`` afin de préserver l'ordre d'empilement existant.
            Lorsque ``False``, l'ordre fourni est conservé tel quel.
        """
        if items is None:
            items = [
                it
                for it in self.scene.selectedItems()
                if it is not self._frame_item
            ]
        else:
            items = [it for it in items if it is not self._frame_item]
        if len(items) <= 1:
            return None
        if sort_items:
            # Preserve stacking order by sorting the items from bottom to top
            items.sort(key=lambda it: it.zValue())
        group = TransparentItemGroup()
        self.scene.addItem(group)
        for it in items:
            group.addToGroup(it)
        # Keep the group's z to match the highest child so layers don't bounce
        group.setZValue(max(it.zValue() for it in items))
        group.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
        )
        self._assign_layer_name(group, "group")
        if self.current_layer:
            self.current_layer.addToGroup(group)
            group.layer = self.current_layer.layer_name
        self.scene.clearSelection()
        group.setSelected(True)
        self._schedule_scene_changed()
        return group

    def ungroup_item(self, group):
        """Détruit un groupe et re-sélectionne ses enfants."""
        if not isinstance(group, (QGraphicsItemGroup, TransparentItemGroup)):
            return
        children = group.childItems()
        if isinstance(group, TransparentItemGroup):
            for ch in children:
                group.removeFromGroup(ch)
                ch.setSelected(True)
            self.scene.removeItem(group)
        else:
            self.scene.destroyItemGroup(group)
            for ch in children:
                ch.setSelected(True)
        self._schedule_scene_changed()

    def create_collection(self, name: str = "collection"):
        """Crée un groupe vide (collection) dans la scène."""
        group = TransparentItemGroup()
        self.scene.addItem(group)
        group.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
        )
        self._assign_layer_name(group, name)
        if self.current_layer:
            self.current_layer.addToGroup(group)
            group.layer = self.current_layer.layer_name
        self._schedule_scene_changed()
        return group

    # --- Layer management -------------------------------------------
    def create_layer(self, name: str | None = None, visible: bool = True):
        """Crée un calque et le retourne."""
        if name is None:
            name = f"Layer {len(self.layers) + 1}"
        group = TransparentItemGroup()
        self.scene.addItem(group)
        # Layers should not be selectable so items are easy to manipulate
        self._assign_layer_name(group, name)
        group.setVisible(visible)
        group.visible = visible
        group.locked = False
        group.setEnabled(True)
        self.layers[group.layer_name] = group
        if self.current_layer is None:
            self.current_layer = group
        logger.debug(
            f"Create layer {group.layer_name} visible={visible}"
        )
        self._schedule_scene_changed()
        return group

    def _apply_lock_setting(self):
        """Lock or unlock layers based on the current setting."""
        if not self.current_layer:
            return
        for layer in self.layers.values():
            effective_locked = layer.locked
            if self.lock_others and layer is not self.current_layer:
                effective_locked = True
            layer.setEnabled(not effective_locked)
            logger.debug(
                f"Layer {getattr(layer, 'layer_name', '')} locked={effective_locked} "
                f"enabled={layer.isEnabled()} current={layer is self.current_layer}"

            )

    def set_lock_others(self, enabled: bool):
        """Enable or disable locking of non-active layers."""
        self.lock_others = enabled
        logger.debug(f"Lock others set to {enabled}")
        self._apply_lock_setting()
        self._schedule_scene_changed()

    def set_current_layer(self, name: str):
        if name in self.layers:
            self.current_layer = self.layers[name]
            logger.debug(f"Current layer set to {name}")
            self._apply_lock_setting()
            self._schedule_scene_changed()

    def set_layer_visible(self, name: str, visible: bool):
        layer = self.layers.get(name)
        if layer:
            layer.setVisible(visible)
            layer.visible = visible
            self._schedule_scene_changed()

    def set_layer_locked(self, name: str, locked: bool):
        layer = self.layers.get(name)
        if layer:
            layer.locked = locked
            logger.debug(f"Layer {name} set locked={locked}")
            self._apply_lock_setting()
            self._schedule_scene_changed()

    def layer_names(self):
        return list(self.layers.keys())

    def remove_layer(self, name: str):
        if name not in self.layers or len(self.layers) <= 1:
            return
        layer = self.layers.pop(name)
        self.scene.removeItem(layer)
        if self.current_layer is layer:
            self.current_layer = next(iter(self.layers.values()))
        self.set_current_layer(self.current_layer.layer_name)
        self._schedule_scene_changed()

    def rename_layer(self, old: str, new: str):
        if old not in self.layers or not new:
            return
        if new in self.layers:
            base = new
            i = 1
            while f"{base} {i}" in self.layers:
                i += 1
            new = f"{base} {i}"
        keys = list(self.layers.keys())
        idx = keys.index(old)
        layer = self.layers.pop(old)
        layer.layer_name = new
        for child in layer.childItems():
            child.layer = new
        keys[idx] = new
        self.layers = OrderedDict((k, self.layers.get(k, layer) if k == new else self.layers[k]) for k in keys)
        if self.current_layer is layer:
            self.current_layer = layer
        self._schedule_scene_changed()

    def duplicate_layer(self, name: str):
        if name not in self.layers:
            return
        src = self.layers[name]
        base = f"{name} copy"
        i = 1
        new_name = base
        while new_name in self.layers:
            i += 1
            new_name = f"{base} {i}"

        self.create_layer(new_name, src.isVisible())

        idx = list(self.layers.keys()).index(name)
        order = list(self.layers.keys())
        order.remove(new_name)
        order.insert(idx + 1, new_name)
        self._reorder(order)
        for item in src.childItems():
            data = self._serialize_item(item)
            if not data:
                continue
            for key in ("x", "x1", "x2"):
                if key in data:
                    data[key] += 10
            for key in ("y", "y1", "y2"):
                if key in data:
                    data[key] += 10
            data["layer"] = new_name
            self._create_item(data)
        self._schedule_scene_changed()

    def move_layer(self, name: str, offset: int):
        keys = list(self.layers.keys())
        if name not in keys:
            return
        idx = keys.index(name)
        new_idx = max(0, min(len(keys) - 1, idx + offset))
        if new_idx == idx:
            return
        keys.insert(new_idx, keys.pop(idx))
        self._reorder(keys)

    def _reorder(self, names):
        self.layers = OrderedDict((n, self.layers[n]) for n in names)
        for z, n in enumerate(names):
            self.layers[n].setZValue(z)


    def setup_layers(self, layers_data):
        """Configure les calques depuis une liste de dicts."""
        for layer in self.layers.values():
            self.scene.removeItem(layer)
        self.layers.clear()
        self.current_layer = None
        if not layers_data:
            self.create_layer("Layer 1")
            return
        for layer in layers_data:
            name = layer.get("name") or f"Layer {len(self.layers)+1}"
            vis = layer.get("visible", True)
            grp = self.create_layer(name, vis)
            if layer.get("locked"):
                grp.locked = True
                grp.setEnabled(False)
        first = layers_data[0]
        self.set_current_layer(first.get("name", self.layer_names()[0]))


    # --- Item lookup -------------------------------------------------
    def select_item_by_name(self, name: str):
        """Select the item having the given stored name."""
        for it in self.scene.items():
            if getattr(it, "layer_name", None) == name:
                logger.debug("Selecting item %s", name)
                self.scene.clearSelection()
                it.setSelected(True)
                self.ensureVisible(it.sceneBoundingRect())
                break

        else:
            logger.debug("Item %s not found", name)


    def get_debug_report(self) -> str:
        """Return a textual report about the current project state."""
        lines: list[str] = []

        meta = getattr(self, "current_meta", {})
        lines.append("== Meta ==")
        for key, val in meta.items():
            lines.append(f"{key}: {val}")
        lines.append("")

        lines.append("== Layers ==")
        for name, layer in self.layers.items():
            locked = getattr(layer, "locked", False)
            count = len(layer.childItems())
            lines.append(
                f"{name}: visible={layer.isVisible()} locked={locked} "
                f"enabled={layer.isEnabled()} items={count}"
            )
        lines.append("")

        current = getattr(self.current_layer, "layer_name", "")
        lines.append(f"Current layer: {current}")
        lines.append(f"Lock others: {self.lock_others}")
        lines.append("")

        lines.append("== Selection ==")
        selected = [
            getattr(it, "layer_name", type(it).__name__)
            for it in self.scene.selectedItems()
        ]
        lines.append(", ".join(selected) if selected else "(none)")
        lines.append("")

        lines.append("== History ==")
        lines.append(f"index: {self._history_index} / {len(self._history)}")
        for i, snap in enumerate(self._history):
            count = len(snap.get("shapes", []))
            name = snap.get("name", "")
            lines.append(f"  {i}: {name} shapes={count}")
        lines.append("")

        lines.append(f"Tool: {self.current_tool}")
        lines.append(
            f"Snap to grid: {self.snap_to_grid} size={self.grid_size} show={self.show_grid}"
        )
        lines.append(f"Document rect: {self._doc_rect}")
        zoom = self.transform().m11() if self.transform().m11() else 1.0
        lines.append(f"Zoom: {zoom:.2f}")
        lines.append(f"Items in scene: {len(self.scene.items())}")

        lines.append("")
        lines.append("== Items by layer ==")
        for name, layer in self.layers.items():
            children = [
                getattr(it, "layer_name", type(it).__name__)
                for it in layer.childItems()
            ]
            lines.append(f"{name}: " + (", ".join(children) if children else "(empty)"))

        return "\n".join(lines)
