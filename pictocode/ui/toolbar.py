from PyQt5.QtWidgets import QToolBar, QAction, QColorDialog
from PyQt5.QtGui import QColor


class Toolbar(QToolBar):
    def __init__(self, parent):
        super().__init__("Outils", parent)
        self.canvas = parent.canvas

        # Rectangle
        rect_act = QAction("Rectangle", self)
        rect_act.triggered.connect(lambda: self.canvas.set_tool("rect"))
        self.addAction(rect_act)

        # Ellipse
        ell_act = QAction("Ellipse", self)
        ell_act.triggered.connect(lambda: self.canvas.set_tool("ellipse"))
        self.addAction(ell_act)

        # Ligne (à ajouter dans shapes.py / canvas.py si besoin)
        line_act = QAction("Ligne", self)
        line_act.triggered.connect(lambda: self.canvas.set_tool("line"))
        self.addAction(line_act)

        # Tracé libre
        free_act = QAction("Tracer libre", self)
        free_act.triggered.connect(lambda: self.canvas.set_tool("freehand"))
        self.addAction(free_act)

        poly_act = QAction("Polygone", self)
        poly_act.triggered.connect(lambda: self.canvas.set_tool("polygon"))
        self.addAction(poly_act)

        # Texte
        text_act = QAction("Texte", self)
        text_act.triggered.connect(lambda: self.canvas.set_tool("text"))
        self.addAction(text_act)

        img_act = QAction("Image...", self)
        img_act.triggered.connect(self.import_image)
        self.addAction(img_act)

        # Pan / déplacement du plan de travail
        pan_act = QAction("Pan", self)
        pan_act.triggered.connect(lambda: self.canvas.set_tool("pan"))
        self.addAction(pan_act)

        # Sélection
        sel_act = QAction("Sélection", self)
        sel_act.triggered.connect(lambda: self.canvas.set_tool("select"))
        self.addAction(sel_act)

        # Gomme
        erase_act = QAction("Gomme", self)
        erase_act.triggered.connect(lambda: self.canvas.set_tool("erase"))
        self.addAction(erase_act)

        self.addSeparator()

        # Palette de couleurs
        self.currentColor = QColor("white")
        color_act = QAction("Couleur...", self)
        color_act.triggered.connect(self.choose_color)
        self.addAction(color_act)

    def import_image(self):
        from PyQt5.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self.parent(),
            "Importer une image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if path:
            item = self.canvas.insert_image(path)
            if item:
                self.parent().add_imported_image(path)

    def choose_color(self):
        """Ouvre une palette, récupère la couleur et la passe au canvas."""
        color = QColorDialog.getColor(
            self.currentColor, self.parent(), "Choisir une couleur"
        )
        if color.isValid():
            self.currentColor = color
            self.canvas.set_pen_color(color)
