# pictocode/core.py

from PyQt5.QtGui import QColor
from .shapes import Rect, Ellipse, Line, FreehandPath, TextItem


class CanvasModel:
    """
    Logique métier du canevas :
    - conserve une liste d'objets graphiques
    - fournit des méthodes pour en créer rapidement
    - prépare à une éventuelle export en “code”
    """

    def __init__(self):
        self.shapes: list = []

    def add_rect(self, x, y, w, h, color: QColor = QColor("black")):
        rect = Rect(x, y, w, h, color=color)
        self.shapes.append(rect)
        return rect

    def add_ellipse(self, x, y, w, h, color: QColor = QColor("black")):
        ellipse = Ellipse(x, y, w, h, color=color)
        self.shapes.append(ellipse)
        return ellipse

    def add_line(self, x1, y1, x2, y2, pen_color="black", pen_width=2):
        clr = QColor(pen_color)
        line = Line(x1, y1, x2, y2, clr, pen_width)
        self.shapes.append(line)
        return line

    def add_freehand_path(self, points, pen_color="black", pen_width=2):
        clr = QColor(pen_color)
        path = FreehandPath.from_points(points, clr, pen_width)
        self.shapes.append(path)
        return path

    def add_text(self, x, y, text, font_size=12, color="black"):
        clr = QColor(color)
        txt = TextItem(x, y, text, font_size, clr)
        self.shapes.append(txt)
        return txt

    def remove_shape(self, shape):
        if shape in self.shapes:
            self.shapes.remove(shape)
            return True
        return False

    def clear(self):
        """Supprime tous les objets du modèle."""
        self.shapes.clear()
