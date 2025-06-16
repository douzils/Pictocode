# pictocode/canvas.py

import math, io
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QAction
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QImage
from .shapes import Rect, Ellipse, Line, FreehandPath, TextItem

class CanvasWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.current_tool = None
        self._start_pos = None
        self.grid_size = 50
        self.show_grid = True
        self.snap_to_grid = False
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        # zone de travail par défaut
        self._doc_rect = QRectF(0,0,800,800)
        self._draw_doc_frame()

    def _draw_doc_frame(self):
        self.scene.clear()
        pen = QPen(QColor(200,200,200), 2, Qt.DashLine)
        self.scene.addRect(self._doc_rect, pen)

    def new_document(self, name, width, height, unit, orientation, color_mode, dpi):
        """
        Initialise un nouveau document (taille, unité, orientation, couleur).
        name est ignoré ici (géré par MainWindow).
        """
        w = float(width)
        h = float(height)
        # conversion unité si nécessaire… ici on garde pixels
        self._doc_rect = QRectF(0,0,w,h)
        self._draw_doc_frame()

    def load_shapes(self, shapes):
        """Recrée chaque forme depuis la liste de dicts."""
        for s in shapes:
            t = s["type"]
            if t == "rect":
                item = Rect(s["x"],s["y"],s["w"],s["h"], QColor(s["color"]))
            elif t == "ellipse":
                item = Ellipse(s["x"],s["y"],s["w"],s["h"], QColor(s["color"]))
            elif t == "line":
                item = Line(s["x1"],s["y1"],s["x2"],s["y2"], QColor(s["color"]))
            elif t == "text":
                item = TextItem(s["x"],s["y"], s["text"], s["font_size"], QColor(s["color"]))
            else:
                continue
            self.scene.addItem(item)

    def export_project(self):
        """
        Exporte métadonnées + formes en dict prêt à json.dump.
        MainWindow y ajoute 'name' et 'dpi'.
        """
        # récupère formes
        shapes = []
        for item in self.scene.items():
            cls = type(item).__name__
            if cls == "Rect":
                r = item.rect()
                shapes.append({
                    "type":"rect",
                    "x":r.x(),"y":r.y(),"w":r.width(),"h":r.height(),
                    "color": item.pen().color().name()
                })
            elif cls == "Ellipse":
                e = item.rect()
                shapes.append({
                    "type":"ellipse",
                    "x":e.x(),"y":e.y(),"w":e.width(),"h":e.height(),
                    "color": item.pen().color().name()
                })
            elif cls == "Line":
                line = item.line()
                shapes.append({
                    "type":"line",
                    "x1":line.x1(),"y1":line.y1(),
                    "x2":line.x2(),"y2":line.y2(),
                    "color": item.pen().color().name()
                })
            elif cls == "TextItem":
                shapes.append({
                    "type":"text",
                    "x":item.x(),"y":item.y(),
                    "text":item.toPlainText(),
                    "font_size": item.font().pointSize(),
                    "color": item.defaultTextColor().name()
                })
            # ignorer FreehandPath pour l'instant…
        # on pourra y ajouter les métas
        meta = getattr(self, "current_meta", {})
        return {**meta, "shapes": shapes}

    # --- le reste (pan/zoom, dessin, grille, menu contextuel) reste inchangé ---
