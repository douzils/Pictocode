# pictocode/canvas.py
# -*- coding: utf-8 -*-

import math
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QAction
from .ui.animated_menu import AnimatedMenu
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QPainterPath
from .shapes import Rect, Ellipse, Line, FreehandPath, TextItem
from .utils import to_pixels

class CanvasWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Scène
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Outil actif
        self.current_tool = None
        self._start_pos = None
        self._freehand_points = None
        self._temp_item = None
        self._current_path_item = None
        self._polygon_points = None
        self._polygon_item = None
        self._poly_preview_line = None
        self.pen_color = QColor("white")

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

        # Cadre de la zone de travail (sera redessiné par new_document)
        self._doc_rect = QRectF(0, 0, 800, 800)
        self._frame_item = None
        self._draw_doc_frame()

        # sélection -> inspecteur
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.scene.changed.connect(lambda _: self._mark_dirty())

    def _draw_doc_frame(self):
        """Dessine le contour en pointillés de la zone de travail."""
        if self._frame_item:
            self.scene.removeItem(self._frame_item)
        pen = QPen(QColor(200, 200, 200), 2, Qt.DashLine)
        self._frame_item = self.scene.addRect(self._doc_rect, pen)
        self._frame_item.setZValue(-1)

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
        if orientation == 'landscape' and h > w:
            w, h = h, w
        elif orientation == 'portrait' and w > h:
            w, h = h, w
        self.scene.clear()
        self._frame_item = None
        self._doc_rect = QRectF(0, 0, w, h)
        self._draw_doc_frame()
        self.setSceneRect(self._doc_rect)
        self.current_meta = {
            'name': name,
            'width': width,
            'height': height,
            'unit': unit,
            'orientation': orientation,
            'color_mode': color_mode,
            'dpi': dpi,
        }

    def update_document_properties(self, width, height, unit, orientation, color_mode, dpi, name=""):
        """Met à jour les paramètres du document sans toucher aux formes."""
        w = to_pixels(width, unit, dpi)
        h = to_pixels(height, unit, dpi)
        if orientation == 'landscape' and h > w:
            w, h = h, w
        elif orientation == 'portrait' and w > h:
            w, h = h, w
        self._doc_rect = QRectF(0, 0, w, h)
        self._draw_doc_frame()
        self.setSceneRect(self._doc_rect)
        if not hasattr(self, 'current_meta'):
            self.current_meta = {}
        self.current_meta.update({
            'name': name or self.current_meta.get('name', ''),
            'width': width,
            'height': height,
            'unit': unit,
            'orientation': orientation,
            'color_mode': color_mode,
            'dpi': dpi,
        })

    def load_shapes(self, shapes):
        """Charge depuis une liste de dicts (issue de export_project)."""
        self.scene.blockSignals(True)
        for s in shapes:
            t = s["type"]
            if t == "rect":
                item = Rect(s["x"], s["y"], s["w"], s["h"], QColor(s["color"]))
            elif t == "ellipse":
                item = Ellipse(s["x"], s["y"], s["w"], s["h"], QColor(s["color"]))
            elif t == "line":
                item = Line(s["x1"], s["y1"], s["x2"], s["y2"], QColor(s["color"]))
            elif t == "path":
                pts = [QPointF(p[0], p[1]) for p in s.get("points", [])]
                item = FreehandPath.from_points(pts, QColor(s.get("color", "black")))
            elif t == "text":
                item = TextItem(s["x"], s["y"], s["text"], s["font_size"], QColor(s["color"]))
            else:
                continue
            self.scene.addItem(item)
        self.scene.blockSignals(False)

    def export_project(self):
        """
        Exporte la meta (self.current_meta) + toutes les formes en dict.
        Prêt à sérialiser en JSON.
        """
        shapes = []
        for item in self.scene.items():
            cls = type(item).__name__
            if cls == "Rect":
                r = item.rect()
                shapes.append({
                    "type": "rect", "x": r.x(), "y": r.y(),
                    "w": r.width(), "h": r.height(),
                    "color": item.pen().color().name()
                })
            elif cls == "Ellipse":
                e = item.rect()
                shapes.append({
                    "type": "ellipse", "x": e.x(), "y": e.y(),
                    "w": e.width(), "h": e.height(),
                    "color": item.pen().color().name()
                })
            elif cls == "Line":
                line = item.line()
                shapes.append({
                    "type": "line",
                    "x1": line.x1(), "y1": line.y1(),
                    "x2": line.x2(), "y2": line.y2(),
                    "color": item.pen().color().name()
                })
            elif cls == "FreehandPath":
                path = item.path()
                pts = [
                    (path.elementAt(i).x, path.elementAt(i).y)
                    for i in range(path.elementCount())
                ]
                shapes.append({
                    "type": "path",
                    "points": pts,
                    "color": item.pen().color().name()
                })
            elif cls == "TextItem":
                shapes.append({
                    "type": "text",
                    "x": item.x(), "y": item.y(),
                    "text": item.toPlainText(),
                    "font_size": item.font().pointSize(),
                    "color": item.defaultTextColor().name()
                })
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
        root = Element('svg', xmlns="http://www.w3.org/2000/svg",
                       width=str(w), height=str(h))

        for item in reversed(self.scene.items()):
            if item is self._frame_item:
                continue
            cls = type(item).__name__
            stroke = item.pen().color().name() if hasattr(item, 'pen') else '#000000'

            if cls == 'Rect':
                r = item.rect()
                SubElement(root, 'rect', x=str(r.x()), y=str(r.y()),
                           width=str(r.width()), height=str(r.height()),
                           fill='none', stroke=stroke)
            elif cls == 'Ellipse':
                e = item.rect()
                cx = e.x() + e.width()/2
                cy = e.y() + e.height()/2
                SubElement(root, 'ellipse', cx=str(cx), cy=str(cy),
                           rx=str(e.width()/2), ry=str(e.height()/2),
                           fill='none', stroke=stroke)
            elif cls == 'Line':
                line = item.line()
                SubElement(root, 'line', x1=str(line.x1()), y1=str(line.y1()),
                           x2=str(line.x2()), y2=str(line.y2()),
                           stroke=stroke)
            elif cls == 'FreehandPath':
                path = item.path()
                pts = [path.elementAt(i) for i in range(path.elementCount())]
                if len(pts) > 2 and pts[0].x == pts[-1].x and pts[0].y == pts[-1].y:
                    points = ' '.join(f"{p.x},{p.y}" for p in pts[:-1])
                    SubElement(root, 'polygon', points=points, fill='none', stroke=stroke)
                else:
                    cmds = []
                    for i, ept in enumerate(pts):
                        cmd = 'M' if i == 0 else 'L'
                        cmds.append(f"{cmd}{ept.x} {ept.y}")
                    SubElement(root, 'path', d=' '.join(cmds), fill='none', stroke=stroke)
            elif cls == 'TextItem':
                SubElement(
                    root,
                    'text',
                    x=str(item.x()),
                    y=str(item.y() + item.font().pointSize()),
                    fill=item.defaultTextColor().name(),
                    **{'font-size': str(item.font().pointSize())}
                ).text = item.toPlainText()

        ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)

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
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._middle_pan = True
        elif event.button() == Qt.LeftButton:
            if self.snap_to_grid:
                scale = self.transform().m11() or 1
                grid = self.grid_size / scale
                scene_pos.setX(round(scene_pos.x() / grid) * grid)
                scene_pos.setY(round(scene_pos.y() / grid) * grid)
            if self.current_tool == "erase":
                items = self.scene.items(scene_pos)
                if items and items[0] is not self._frame_item:
                    self.scene.removeItem(items[0])
                    self._mark_dirty()
            elif self.current_tool in ("rect", "ellipse", "line"):
                items = [it for it in self.scene.items(scene_pos) if it is not self._frame_item]
                if items:
                    super().mousePressEvent(event)
                    return
                self._start_pos = scene_pos
                if self.current_tool == "rect":
                    self._temp_item = Rect(scene_pos.x(), scene_pos.y(), 0, 0, self.pen_color)
                elif self.current_tool == "ellipse":
                    self._temp_item = Ellipse(scene_pos.x(), scene_pos.y(), 0, 0, self.pen_color)
                elif self.current_tool == "line":
                    self._temp_item = Line(scene_pos.x(), scene_pos.y(), scene_pos.x(), scene_pos.y(), self.pen_color)
                if self._temp_item:
                    self._temp_item.setOpacity(0.6)
                    self.scene.addItem(self._temp_item)
            elif self.current_tool == "polygon":
                if self._polygon_points is None:
                    self._polygon_points = [scene_pos]
                    path = QPainterPath(scene_pos)
                    self._polygon_item = FreehandPath(path, self.pen_color, 2)
                    self._polygon_item.setOpacity(0.6)
                    self.scene.addItem(self._polygon_item)
                    self._poly_preview_line = Line(scene_pos.x(), scene_pos.y(), scene_pos.x(), scene_pos.y(), self.pen_color)
                    self._poly_preview_line.setOpacity(0.6)
                    self.scene.addItem(self._poly_preview_line)
                else:
                    self._polygon_points.append(scene_pos)
                    path = self._polygon_item.path()
                    path.lineTo(scene_pos)
                    self._polygon_item.setPath(path)
                    self._poly_preview_line.setLine(scene_pos.x(), scene_pos.y(), scene_pos.x(), scene_pos.y())
            elif self.current_tool == "freehand":
                self._freehand_points = [scene_pos]
                self._current_path_item = FreehandPath.from_points(self._freehand_points, self.pen_color, 2)
                self._current_path_item.setOpacity(0.6)
                self.scene.addItem(self._current_path_item)
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):

        if self.current_tool == "pan" or self._middle_pan:
            super().mouseMoveEvent(event)
            return
        if self._middle_pan:
            super().mouseMoveEvent(event)
            return
        scene_pos = self.mapToScene(event.pos())
        if self.snap_to_grid:
            scale = self.transform().m11() or 1
            grid = self.grid_size / scale
            scene_pos.setX(round(scene_pos.x() / grid) * grid)
            scene_pos.setY(round(scene_pos.y() / grid) * grid)
        if self.current_tool == "polygon" and self._polygon_points:
            last = self._polygon_points[-1]
            self._poly_preview_line.setLine(last.x(), last.y(), scene_pos.x(), scene_pos.y())
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
                self._temp_item.setRect(x0, y0, scene_pos.x() - x0, scene_pos.y() - y0)
            elif self.current_tool == "line":
                self._temp_item.setLine(x0, y0, scene_pos.x(), scene_pos.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.current_tool == "pan":
            super().mouseReleaseEvent(event)
            return
        if self._middle_pan and event.button() == Qt.MiddleButton:
            self.setDragMode(self._prev_drag_mode or QGraphicsView.NoDrag)
            self._middle_pan = False
            super().mouseReleaseEvent(event)
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
            self._poly_preview_line.setLine(scene_pos.x(), scene_pos.y(), scene_pos.x(), scene_pos.y())
        elif self.current_tool == "freehand" and self._freehand_points:
            self._freehand_points.append(scene_pos)
            if self._current_path_item:
                path = self._current_path_item.path()
                if path.elementCount() == 0:
                    path.moveTo(self._freehand_points[0])
                path.lineTo(scene_pos)
                self._current_path_item.setPath(path)
                self._current_path_item.setOpacity(1.0)
            self._current_path_item = None
            self._freehand_points = None
            self._mark_dirty()
        elif self._temp_item and self._start_pos:
            x0, y0 = self._start_pos.x(), self._start_pos.y()
            if self.current_tool in ("rect", "ellipse"):
                self._temp_item.setRect(x0, y0, scene_pos.x() - x0, scene_pos.y() - y0)
            elif self.current_tool == "line":
                self._temp_item.setLine(x0, y0, scene_pos.x(), scene_pos.y())
            self._temp_item.setOpacity(1.0)
            self._temp_item = None
            self._mark_dirty()
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
            self.scene.removeItem(self._poly_preview_line)
            self._poly_preview_line = None
            self._polygon_item = None
            self._polygon_points = None
            self._mark_dirty()
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
                act_width.triggered.connect(lambda: self._change_pen_width(item))
                menu.addAction(act_width)
            if hasattr(item, "brush"):
                act_fill = QAction("Couleur de remplissage...", self)
                act_fill.triggered.connect(lambda: self._change_brush_color(item))
                menu.addAction(act_fill)
            act_delete = QAction("Supprimer", self)
            act_delete.triggered.connect(lambda: (self.scene.removeItem(item), self._mark_dirty()))
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

    def _change_pen_width(self, item):
        from PyQt5.QtWidgets import QInputDialog
        width, ok = QInputDialog.getInt(self, "Épaisseur", "Largeur :", item.pen().width(), 1, 20)
        if ok:
            pen = item.pen()
            pen.setWidth(width)
            item.setPen(pen)

    # ─── Couleur et sélection ─────────────────────────────────────────
    def set_pen_color(self, color: QColor):
        """Définit la couleur utilisée pour les prochains objets."""
        self.pen_color = color

    def _on_selection_changed(self):
        parent = self.parent()
        if hasattr(parent, "inspector"):
            items = self.scene.selectedItems()
            if items:
                parent.inspector.set_target(items[0])

    def _mark_dirty(self):
        parent = self.parent()
        if hasattr(parent, "set_dirty"):
            parent.set_dirty(True)


