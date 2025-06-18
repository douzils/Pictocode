# pictocode/ui/inspector.py
from PyQt5.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QColorDialog,
    QPushButton,
    QComboBox,
)
from PyQt5.QtCore import Qt
from .step_spinbox import StepSpinBox


class Inspector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QFormLayout(self)

        self.x_field = StepSpinBox(self)
        self.x_field.setRange(-10000, 10000)
        self.y_field = StepSpinBox(self)
        self.y_field.setRange(-10000, 10000)
        self.w_field = StepSpinBox(self)
        self.w_field.setRange(1, 10000)
        self.h_field = StepSpinBox(self)
        self.h_field.setRange(1, 10000)
        self.rotation_field = StepSpinBox(self)
        self.rotation_field.setRange(-360, 360)
        self.z_field = StepSpinBox(self)
        self.z_field.setRange(-1000, 1000)
        self.border_field = StepSpinBox(self)
        self.border_field.setRange(0, 100)
        self.var_field = QLineEdit(self)
        self.align_field = QComboBox(self)
        self.align_field.addItems(["left", "center", "right"])
        self.fill_btn = QPushButton()
        self.fill_btn.setFixedWidth(40)
        self.fill_btn.clicked.connect(self._pick_fill)
        self._update_fill_button("#ffffff")
        self.layout.addRow("X :", self.x_field)
        self.layout.addRow("Y :", self.y_field)
        self.layout.addRow("W :", self.w_field)
        self.layout.addRow("H :", self.h_field)
        self.layout.addRow("Rotation :", self.rotation_field)
        self.layout.addRow("Calque :", self.z_field)
        self.layout.addRow("Largeur bordure :", self.border_field)

        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(40)
        self.color_btn.clicked.connect(self._pick_color)
        self._update_color_button("#000000")
        self.layout.addRow("Couleur bordure :", self.color_btn)
        self.layout.addRow("Couleur fond :", self.fill_btn)
        self.layout.addRow("Variable :", self.var_field)
        self.layout.addRow("Alignement :", self.align_field)

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
            (self.rotation_field, lambda val: self._item.setRotation(int(val))),
            (self.z_field, lambda val: self._item.setZValue(int(val))),
            (self.border_field, self._set_pen_width),
            (self.var_field, self._set_var_name),
            (self.align_field, self._set_alignment),
            (self.text_field, lambda val: self._item.setPlainText(val) if hasattr(self._item, 'setPlainText') else None),
            (self.font_field, lambda val: self._set_font_size(int(val))),
        ):
            if hasattr(fld, "editingFinished"):
                fld.editingFinished.connect(
                    lambda fld=fld, st=setter: self._update_field(fld, st)
                )
            elif isinstance(fld, QComboBox):
                fld.currentIndexChanged.connect(
                    lambda _idx, fld=fld, st=setter: self._update_field(fld, st)
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
                self.rotation_field,
                self.z_field,
                self.border_field,
            ):
                fld.setValue(0)
            self.var_field.setText("")
            self._update_color_button("#000000")
            self._update_fill_button("#ffffff")
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
        if hasattr(item, "brush"):
            self._update_fill_button(item.brush().color().name())
        self.rotation_field.setValue(int(item.rotation()))
        self.z_field.setValue(int(item.zValue()))
        if hasattr(item, "pen"):
            self.border_field.setValue(item.pen().width())
        self.var_field.setText(getattr(item, "var_name", ""))
        if hasattr(item, "alignment"):
            idx = self.align_field.findText(getattr(item, "alignment", "left"))
            if idx >= 0:
                self.align_field.setCurrentIndex(idx)
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
            if hasattr(fld, "value"):
                value = fld.value()
            elif hasattr(fld, "currentText"):
                value = fld.currentText()
            else:
                value = fld.text()
            setter(value)
            self._notify_change()
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
            self._notify_change()

    def _set_font_size(self, size: int):
        if hasattr(self._item, 'font'):
            f = self._item.font()
            f.setPointSize(size)
            self._item.setFont(f)
            self._notify_change()

    def _set_pen_width(self, width: int):
        if hasattr(self._item, 'pen'):
            pen = self._item.pen()
            pen.setWidth(int(width))
            self._item.setPen(pen)
            self._notify_change()

    def _set_var_name(self, name: str):
        if self._item is not None:
            setattr(self._item, 'var_name', name)
            self._notify_change()

    def _set_alignment(self, _val):
        if hasattr(self._item, 'alignment'):
            self._item.alignment = self.align_field.currentText()
            self._notify_change()

    def _update_color_button(self, color: str):
        self.color_btn.setStyleSheet(f"background:{color};")

    def _pick_fill(self, event=None):
        if not self._item or not hasattr(self._item, 'brush'):
            return
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            brush = self._item.brush()
            brush.setColor(col)
            brush.setStyle(Qt.SolidPattern)
            self._item.setBrush(brush)
            self._update_fill_button(col.name())
            self._notify_change()

    def _update_fill_button(self, color: str):
        self.fill_btn.setStyleSheet(f"background:{color};")

    def _notify_change(self):
        if self._item and self._item.scene():
            views = self._item.scene().views()
            if views:
                view = views[0]
                if hasattr(view, "_mark_dirty"):
                    view._mark_dirty()

