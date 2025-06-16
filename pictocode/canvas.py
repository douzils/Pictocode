# pictocode/canvas.py

import math
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QAction
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen
from .shapes import Rect, Ellipse, Line, TextItem

class CanvasWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Scène
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Outil actif
        self.current_tool = None
        self._start_pos = None
        self.pen_color = QColor("black")

        # Grille et magnétisme
        self.grid_size = 50
        self.show_grid = True
        self.snap_to_grid = False

        # Anti-aliasing
        self.setRenderHint(QPainter.Antialiasing)

        # Pan & Zoom
        self.setDragMode(QGraphicsView.NoDrag)

        # Cadre de la zone de travail (sera redessiné par new_document)
        self._doc_rect = QRectF(0, 0, 800, 800)
        self._frame_item = None
        self._draw_doc_frame()

        # sélection -> inspecteur
        self.scene.selectionChanged.connect(self._on_selection_changed)

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

    def new_document(self, width, height, unit, orientation, color_mode, dpi, name=""):
        """
        Initialise un nouveau document selon les paramètres donnés.
        width/height en unité choisie, orientation et dpi sont pris en compte ici.
        """
        w = float(width)
        h = float(height)
        # TODO: convertir selon unit (px, mm, cm…)
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
        w = float(width)
        h = float(height)
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

    # ─── Pan & Zoom ────────────────────────────────────────────────────
    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        if event.button() == Qt.LeftButton and self.current_tool in ("rect", "ellipse", "line"):
            if self.snap_to_grid:
                grid = self.grid_size
                scene_pos.setX(round(scene_pos.x() / grid) * grid)
                scene_pos.setY(round(scene_pos.y() / grid) * grid)
            self._start_pos = scene_pos
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event)
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        if self._start_pos and self.current_tool:
            x0, y0 = self._start_pos.x(), self._start_pos.y()
            x1, y1 = scene_pos.x(), scene_pos.y()
            if self.snap_to_grid:
                grid = self.grid_size
                x1 = round(x1 / grid) * grid
                y1 = round(y1 / grid) * grid
            if self.current_tool == "rect":
                item = Rect(x0, y0, x1 - x0, y1 - y0, self.pen_color)
            elif self.current_tool == "ellipse":
                item = Ellipse(x0, y0, x1 - x0, y1 - y0, self.pen_color)
            elif self.current_tool == "line":
                item = Line(x0, y0, x1, y1, self.pen_color)
            else:
                item = None
            if item:
                self.scene.addItem(item)
        self._start_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        if self.snap_to_grid:
            grid = self.grid_size
            scene_pos.setX(round(scene_pos.x() / grid) * grid)
            scene_pos.setY(round(scene_pos.y() / grid) * grid)
        items = self.scene.items(scene_pos)
        if items and isinstance(items[0], TextItem):
            ti = items[0]
            ti.setTextInteractionFlags(Qt.TextEditorInteraction)
            ti.setFocus()
        elif items:
            x, y = scene_pos.x(), scene_pos.y()
            ti = TextItem(x, y, text="Texte", color=self.pen_color)
            ti.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.scene.addItem(ti)
            ti.setFocus()
        else:
            super().mouseDoubleClickEvent(event)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self.show_grid:
            return
        pen = QPen(QColor(220, 220, 220), 0)
        painter.setPen(pen)
        gs = self.grid_size
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))
        # verticales
        x = left - (left % gs)
        while x < right:
            painter.drawLine(x, top, x, bottom)
            x += gs
        # horizontales
        y = top - (top % gs)
        while y < bottom:
            painter.drawLine(left, y, right, y)
            y += gs

    def _show_context_menu(self, event):
        menu = QMenu(self)
        scene_pos = self.mapToScene(event.pos())
        items = self.scene.items(scene_pos)
        if items:
            item = items[0]
            act_delete = QAction("Supprimer", self)
            act_delete.triggered.connect(lambda: self.scene.removeItem(item))
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

