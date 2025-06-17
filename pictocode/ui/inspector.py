# pictocode/ui/inspector.py
from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit, QColorDialog


class Inspector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QFormLayout(self)

        self.x_field = QLineEdit(self)
        self.y_field = QLineEdit(self)
        self.w_field = QLineEdit(self)
        self.h_field = QLineEdit(self)
        self.layout.addRow("X :", self.x_field)
        self.layout.addRow("Y :", self.y_field)
        self.layout.addRow("W :", self.w_field)
        self.layout.addRow("H :", self.h_field)

        self.color_btn = QLineEdit(self)  # on affiche le code couleur
        self.color_btn.setReadOnly(True)
        self.layout.addRow("Couleur :", self.color_btn)

        # Item courant
        self._item = None

        # Connexions de saisie
        for fld, setter in (
            (self.x_field, lambda val: self._item.setX(int(val))),
            (self.y_field, lambda val: self._item.setY(int(val))),
            (
                self.w_field,
                lambda val: self._item.setRect(
                    0, 0, int(self.w_field.text()), self._item.rect().height()
                ),
            ),
            (
                self.h_field,
                lambda val: self._item.setRect(
                    0, 0, self._item.rect().width(), int(val)
                ),
            ),
        ):
            fld.editingFinished.connect(
                lambda fld=fld, st=setter: self._update_field(fld, st)
            )

        # Choix de couleur
        self.color_btn.mousePressEvent = self._pick_color

    def set_target(self, item):
        """Appelé par le Canvas quand un item est sélectionné."""
        self._item = item
        r = item.rect() if hasattr(item, "rect") else item.boundingRect()
        self.x_field.setText(str(int(item.x())))
        self.y_field.setText(str(int(item.y())))
        self.w_field.setText(str(int(r.width())))
        self.h_field.setText(str(int(r.height())))
        pen = item.pen().color().name() if hasattr(item, "pen") else "#000000"
        self.color_btn.setText(pen)

    def _update_field(self, fld, setter):
        try:
            setter(fld.text())
        except Exception:
            pass

    def _pick_color(self, event):
        if not self._item:
            return
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            pen = self._item.pen()
            pen.setColor(col)
            self._item.setPen(pen)
            self.color_btn.setText(col.name())
