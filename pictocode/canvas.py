# pictocode/canvas.py
# -*- coding: utf-8 -*-

import math
from PyQt5.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QAction,
    QGraphicsItem,
    QGraphicsItemGroup,
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
from .shapes import Rect, Ellipse, Line, FreehandPath, TextItem, ImageItem
from .utils import to_pixels


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

        # Scène
        self.scene = CanvasScene(self)
        self.setScene(self.scene)
        self.scene.itemAdded.connect(self._schedule_scene_changed)
        self.scene.itemRemoved.connect(self._schedule_scene_changed)

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

    def new_document(self, width, height, unit, orientation, color_mode, dpi, name=""):
        """
        Initialise un nouveau document selon les paramètres donnés.
        width/height en unité choisie, orientation et dpi sont pris en compte ici.
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
        if hasattr(window, "layers"):
            window.layers.update_layers(self)

        if not self._loading_snapshot:
            self._snapshot()

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
        for s in shapes:
            self._create_item(s)
        self.scene.blockSignals(False)
        window = self.window()
        if hasattr(window, "layers"):
            window.layers.update_layers(self)

    def export_project(self):
        """
        Exporte la meta (self.current_meta) + toutes les formes en dict.
        Prêt à sérialiser en JSON.
        """
        shapes = []
        for item in reversed(self.scene.items()):
            if item is self._frame_item:
                continue
            data = self._serialize_item(item)
            if data:
                shapes.append(data)
        meta = getattr(self, "current_meta", {})
        return {**meta, "shapes": shapes}

    def export_image(self, path: str, img_format: str = "PNG"):
        """Enregistre la scène actuelle dans un fichier image."""
        w = int(self._doc_rect.width())
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

        w = int(self._doc_rect.width())
        h = int(self._doc_rect.height())
        root = Element(
            "svg", xmlns="http://www.w3.org/2000/svg", width=str(w), height=str(h)
        )

        for item in reversed(self.scene.items()):
            if item is self._frame_item:
                continue
            cls = type(item).__name__
            stroke = item.pen().color().name() if hasattr(item, "pen") else "#000000"

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
                pts = [path.elementAt(i) for i in range(path.elementCount())]
                if len(pts) > 2 and pts[0].x == pts[-1].x and pts[0].y == pts[-1].y:
                    points = " ".join(f"{p.x},{p.y}" for p in pts[:-1])
                    SubElement(
                        root, "polygon", points=points, fill="none", stroke=stroke
                    )
                else:
                    cmds = []
                    for i, ept in enumerate(pts):
                        cmd = "M" if i == 0 else "L"
                        cmds.append(f"{cmd}{ept.x} {ept.y}")
                    SubElement(
                        root, "path", d=" ".join(cmds), fill="none", stroke=stroke
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
            while base_item and base_item.parentItem():
                base_item = base_item.parentItem()
            if base_item is self._frame_item:
                base_item = None
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
            elif self.current_tool in ("rect", "ellipse", "line"):
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
                if self._temp_item:
                    self._temp_item.setZValue(self._new_item_z)
                    self._temp_item.setOpacity(0.6)
                    self.scene.addItem(self._temp_item)
            elif self.current_tool == "text":
                item = TextItem(scene_pos.x(), scene_pos.y(), "Texte", 12, self.pen_color)
                item.setZValue(self._new_item_z)
                self.scene.addItem(item)
                self._assign_layer_name(item)
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
                        scene_pos.x(), scene_pos.y(), scene_pos.x(), scene_pos.y()
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

    def mouseMoveEvent(self, event):

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
        elif self.current_tool == "freehand" and self._freehand_points is not None:
            self._freehand_points.append(scene_pos)
            if self._current_path_item:
                path = self._current_path_item.path()
                if path.elementCount() == 0:
                    path.moveTo(self._freehand_points[0])
                path.lineTo(scene_pos)
                self._current_path_item.setPath(path)
        elif self._temp_item and self._start_pos:
            x0, y0 = self._start_pos.x(), self._start_pos.y()
            if self.current_tool in ("rect", "ellipse"):
                rect = QRectF(x0, y0, scene_pos.x() - x0, scene_pos.y() - y0).normalized()
                self._temp_item.setRect(
                    rect.x(), rect.y(), rect.width(), rect.height()
                )
            elif self.current_tool == "line":
                self._temp_item.setLine(x0, y0, scene_pos.x(), scene_pos.y())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.current_tool == "pan":
            super().mouseReleaseEvent(event)
            return
        if self._middle_pan and event.button() == Qt.MiddleButton:
            self._middle_pan = False
            self.setDragMode(self._prev_drag_mode or QGraphicsView.NoDrag)
            return
        scene_pos = self.mapToScene(event.pos())
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
            self._current_path_item = None
            self._freehand_points = None
            self._mark_dirty()
            self._schedule_scene_changed()
        elif self._temp_item and self._start_pos:
            x0, y0 = self._start_pos.x(), self._start_pos.y()
            if self.current_tool in ("rect", "ellipse"):
                rect = QRectF(x0, y0, scene_pos.x() - x0, scene_pos.y() - y0).normalized()
                self._temp_item.setRect(
                    rect.x(), rect.y(), rect.width(), rect.height()
                )
            elif self.current_tool == "line":
                self._temp_item.setLine(x0, y0, scene_pos.x(), scene_pos.y())
            self._temp_item.setOpacity(1.0)
            self._assign_layer_name(self._temp_item)
            self._temp_item = None
            self._mark_dirty()
            self._schedule_scene_changed()
            self._start_pos = None
            return
        self._start_pos = None
        super().mouseReleaseEvent(event)

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
                act_color.triggered.connect(lambda: self._change_pen_color(item))
                menu.addAction(act_color)
                act_width = QAction("Épaisseur du trait...", self)
                act_width.triggered.connect(lambda: self._change_pen_width(item))
                menu.addAction(act_width)
            if hasattr(item, "brush"):
                act_fill = QAction("Couleur de remplissage...", self)
                act_fill.triggered.connect(lambda: self._change_brush_color(item))
                menu.addAction(act_fill)
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
        window = self.window()
        if hasattr(window, "inspector"):
            items = self.scene.selectedItems()
            if items:
                window.inspector.set_target(items[0])
                if hasattr(window, "layers"):
                    window.layers.highlight_item(items[0])
            else:
                window.inspector.set_target(None)

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
        if hasattr(window, "layers"):
            window.layers.update_layers(self)

        # Agrandit automatiquement la zone de la scène pour permettre
        # le déplacement libre des formes en dehors du document initial.
        bounds = self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        if not bounds.contains(self._doc_rect):
            bounds = bounds.united(self._doc_rect)
            self.setSceneRect(bounds)

        if not self._loading_snapshot:
            self._snapshot()

    # --- Clipboard / editing helpers ---------------------------------
    def _serialize_item(self, item):
        cls = type(item).__name__
        if cls == "Rect":
            r = item.rect()
            return {
                "type": "rect",
                "name": getattr(item, "layer_name", ""),
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
                data["x"], data["y"], data["w"], data["h"], QColor(data["color"])
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
                data["x"], data["y"], data["w"], data["h"], QColor(data["color"])
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
                data["x1"], data["y1"], data["x2"], data["y2"], QColor(data["color"])
            )
            pen = item.pen()
            pen.setWidth(int(data.get("pen_width", pen.width())))
            item.setPen(pen)
            item.setPos(float(data.get("x", 0)), float(data.get("y", 0)))
            item.setRotation(float(data.get("rotation", 0)))
            item.setZValue(float(data.get("z", 0)))
        elif t == "path":
            pts = [QPointF(p[0], p[1]) for p in data.get("points", [])]
            item = FreehandPath.from_points(pts, QColor(data.get("color", "black")))
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

    def zoom_in(self):
        self.scale(1.25, 1.25)

    def zoom_out(self):
        self.scale(0.8, 0.8)

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
    def group_selected(self):
        """Regroupe les éléments sélectionnés dans un QGraphicsItemGroup."""
        items = [it for it in self.scene.selectedItems() if it is not self._frame_item]
        if len(items) <= 1:
            return None
        # Preserve stacking order by sorting the items from bottom to top
        items.sort(key=lambda it: it.zValue())
        group = self.scene.createItemGroup(items)
        # Keep the group's z to match the highest child so layers don't bounce
        group.setZValue(max(it.zValue() for it in items))
        group.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
        )
        self._assign_layer_name(group, "group")
        self.scene.clearSelection()
        group.setSelected(True)
        self._schedule_scene_changed()
        return group

    def ungroup_item(self, group):
        """Détruit un groupe et re-sélectionne ses enfants."""
        if not isinstance(group, QGraphicsItemGroup):
            return
        children = group.childItems()
        self.scene.destroyItemGroup(group)
        for ch in children:
            ch.setSelected(True)
        self._schedule_scene_changed()

    def create_collection(self, name: str = "collection"):
        """Crée un groupe vide (collection) dans la scène."""
        group = QGraphicsItemGroup()
        self.scene.addItem(group)
        group.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
        )
        self._assign_layer_name(group, name)
        self._schedule_scene_changed()
        return group

