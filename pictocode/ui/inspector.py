# pictocode/ui/inspector.py
from PyQt5.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QColorDialog,
    QSpinBox,
    QPushButton,
)


class Inspector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QFormLayout(self)

        self.x_field = QSpinBox(self)
        self.x_field.setRange(-10000, 10000)
        self.y_field = QSpinBox(self)
        self.y_field.setRange(-10000, 10000)
        self.w_field = QSpinBox(self)
        self.w_field.setRange(1, 10000)
        self.h_field = QSpinBox(self)
        self.h_field.setRange(1, 10000)
        self.layout.addRow("X :", self.x_field)
        self.layout.addRow("Y :", self.y_field)
        self.layout.addRow("W :", self.w_field)
        self.layout.addRow("H :", self.h_field)

        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(40)
        self.color_btn.clicked.connect(self._pick_color)
        self._update_color_button("#000000")
        self.layout.addRow("Couleur :", self.color_btn)

        self.text_field = QLineEdit(self)
        self.font_field = QLineEdit(self)
        self.layout.addRow("Texte :", self.text_field)
        self.layout.addRow("Taille :", self.font_field)
        self.text_field.hide()
        self.font_field.hide()

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
            (self.text_field, lambda val: self._item.setPlainText(val) if hasattr(self._item, 'setPlainText') else None),
            (self.font_field, lambda val: self._set_font_size(int(val))),

        ):
            fld.editingFinished.connect(
                lambda fld=fld, st=setter: self._update_field(fld, st)
            )

        # Choix de couleur handled by clicked signal

    def set_target(self, item):
        """Appelé par le Canvas quand un item est sélectionné."""
        self._item = item
        if item is None:
            for fld in (
                self.x_field,
                self.y_field,
                self.w_field,
                self.h_field,
            ):
                fld.setValue(0)
            self._update_color_button("#000000")
            self.text_field.hide()
            self.font_field.hide()
            return

        r = item.rect() if hasattr(item, "rect") else item.boundingRect()
        self.x_field.setValue(int(item.x()))
        self.y_field.setValue(int(item.y()))
        self.w_field.setValue(int(r.width()))
        self.h_field.setValue(int(r.height()))
        pen = item.pen().color().name() if hasattr(item, "pen") else "#000000"
        self._update_color_button(pen)
        if hasattr(item, "toPlainText"):
            self.text_field.show()
            self.font_field.show()
            self.text_field.setText(item.toPlainText())
            self.font_field.setText(str(item.font().pointSize()))
        else:
            self.text_field.hide()
            self.font_field.hide()

    def _update_field(self, fld, setter):
        try:
            value = fld.value() if hasattr(fld, "value") else fld.text()
            setter(value)
        except Exception:
            pass

    def _pick_color(self, event=None):
        if not self._item:
            return
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            if hasattr(self._item, "pen"):
                pen = self._item.pen()
                pen.setColor(col)
                self._item.setPen(pen)
            elif hasattr(self._item, "setDefaultTextColor"):
                self._item.setDefaultTextColor(col)
            self._update_color_button(col.name())

    def _set_font_size(self, size: int):
        if hasattr(self._item, 'font'):
            f = self._item.font()
            f.setPointSize(size)
            self._item.setFont(f)

    def _update_color_button(self, color: str):
        self.color_btn.setStyleSheet(f"background:{color};")

