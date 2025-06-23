# pictocode/ui/inspector.py
from PyQt5.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QColorDialog,
    QPushButton,
    QComboBox,
    QInputDialog,
    QDialog,
    QHBoxLayout,
)
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QLinearGradient, QBrush, QColor
from .gradient_editor import GradientEditorDialog
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
        self.axis_btn = QPushButton("Définir…", self)
        self.axis_btn.clicked.connect(self._set_rotation_axis)
        self.flip_h_btn = QPushButton("Horizontal", self)
        self.flip_h_btn.clicked.connect(self._flip_horizontal)
        self.flip_v_btn = QPushButton("Vertical", self)
        self.flip_v_btn.clicked.connect(self._flip_vertical)
        flip_box = QWidget(self)
        flip_layout = QHBoxLayout(flip_box)
        flip_layout.setContentsMargins(0, 0, 0, 0)
        flip_layout.setSpacing(2)
        flip_layout.addWidget(self.flip_h_btn)
        flip_layout.addWidget(self.flip_v_btn)
        self.z_field = StepSpinBox(self)
        self.z_field.setRange(-1000, 1000)
        self.border_field = StepSpinBox(self)
        self.border_field.setRange(0, 100)
        self.opacity_field = StepSpinBox(self)
        self.opacity_field.setRange(0, 100)
        self.opacity_field.setValue(100)
        self.var_field = QLineEdit(self)
        self.align_field = QComboBox(self)
        self.align_field.addItems(["left", "center", "right"])
        self.fill_btn = QPushButton()
        self.fill_btn.setFixedWidth(40)
        self.fill_btn.clicked.connect(self._pick_fill)
        self.gradient_btn = QPushButton("…", self)
        self.gradient_btn.clicked.connect(self._pick_gradient)
        self._update_gradient_button(QColor("white"), QColor("black"))
        self._update_fill_button("#ffffff")
        self.layout.addRow("X :", self.x_field)
        self.layout.addRow("Y :", self.y_field)
        self.layout.addRow("W :", self.w_field)
        self.layout.addRow("H :", self.h_field)
        self.layout.addRow("Rotation :", self.rotation_field)
        self.layout.addRow("Axe rotation :", self.axis_btn)
        self.layout.addRow("Miroir :", flip_box)
        self.layout.addRow("Calque :", self.z_field)
        self.layout.addRow("Largeur bordure :", self.border_field)
        self.layout.addRow("Opacité % :", self.opacity_field)

        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(40)
        self.color_btn.clicked.connect(self._pick_color)
        self._update_color_button("#000000")
        self.layout.addRow("Couleur bordure :", self.color_btn)
        self.layout.addRow("Couleur fond :", self.fill_btn)
        self.layout.addRow("Dégradé :", self.gradient_btn)
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
            (
                self.rotation_field,
                lambda val: self._item.setRotation(int(val)),
            ),
            (self.z_field, lambda val: self._item.setZValue(int(val))),
            (self.border_field, self._set_pen_width),
            (
                self.opacity_field,
                lambda val: self._item.setOpacity(int(val) / 100),
            ),
            (self.var_field, self._set_var_name),
            (self.align_field, self._set_alignment),
            (self.text_field, lambda val: self._item.setPlainText(
                val) if hasattr(self._item, 'setPlainText') else None),
            (self.font_field, lambda val: self._set_font_size(int(val))),
        ):
            if hasattr(fld, "valueChanged"):
                fld.valueChanged.connect(
                    lambda _val, fld=fld, st=setter: self._update_field(
                        fld, st)
                )
            elif hasattr(fld, "textEdited"):
                fld.textEdited.connect(
                    lambda _val, fld=fld, st=setter: self._update_field(
                        fld, st)
                )
            elif isinstance(fld, QComboBox):
                fld.currentIndexChanged.connect(
                    lambda _idx, fld=fld, st=setter: self._update_field(
                        fld, st)
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
            self.opacity_field.setValue(100)
            self.var_field.setText("")
            self._update_color_button("#000000")
            self._update_fill_button("#ffffff")
            self._update_gradient_button(QColor("white"), QColor("black"))
            self.text_field.hide()
            self.font_field.hide()
            return

        r = item.rect() if hasattr(item, "rect") else item.boundingRect()
        # avoid moving the item when populating the inspector fields
        for fld, val in (
            (self.x_field, int(item.x())),
            (self.y_field, int(item.y())),
            (self.w_field, int(r.width())),
            (self.h_field, int(r.height())),
            (self.rotation_field, int(item.rotation())),
            (self.opacity_field, int(item.opacity() * 100)),
            (self.z_field, int(item.zValue())),
        ):
            fld.blockSignals(True)
            fld.setValue(val)
            fld.blockSignals(False)
        if hasattr(item, "pen"):
            self.border_field.blockSignals(True)
            self.border_field.setValue(item.pen().width())
            self.border_field.blockSignals(False)
        pen = item.pen().color().name() if hasattr(item, "pen") else "#000000"
        self._update_color_button(pen)
        if hasattr(item, "brush"):
            brush = item.brush()
            grad = brush.gradient()
            if grad and isinstance(grad, QLinearGradient):
                stops = grad.stops()
                if stops:
                    self._update_gradient_button(stops[0][1], stops[-1][1])
                else:
                    self._update_gradient_button(
                        QColor("white"), QColor("black"))
            else:
                self._update_gradient_button(QColor("white"), QColor("black"))
            self._update_fill_button(brush.color().name())
        self.var_field.blockSignals(True)
        self.var_field.setText(getattr(item, "var_name", ""))
        self.var_field.blockSignals(False)
        if hasattr(item, "alignment"):
            idx = self.align_field.findText(getattr(item, "alignment", "left"))
            if idx >= 0:
                self.align_field.blockSignals(True)
                self.align_field.setCurrentIndex(idx)
                self.align_field.blockSignals(False)
        if hasattr(item, "toPlainText"):
            self.text_field.show()
            self.font_field.show()
            self.text_field.blockSignals(True)
            self.text_field.setText(item.toPlainText())
            self.text_field.blockSignals(False)
            self.font_field.blockSignals(True)
            self.font_field.setText(str(item.font().pointSize()))
            self.font_field.blockSignals(False)
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
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Failed to update %s", fld, exc_info=exc
            )

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

    def _pick_gradient(self, event=None):
        if not self._item or not hasattr(self._item, 'brush'):
            return
        brush = self._item.brush()
        start_col = QColor("white")
        end_col = QColor("black")
        p1, p2 = 0.0, 1.0
        grad = brush.gradient()
        if grad and isinstance(grad, QLinearGradient):
            stops = grad.stops()
            if stops:
                p1, start_col = stops[0]
                p2, end_col = stops[-1]
        dlg = GradientEditorDialog(start_col, end_col, p1, p2, self)
        if dlg.exec_() == QDialog.Accepted:
            start_col, end_col, p1, p2 = dlg.get_gradient()
            r = self._item.boundingRect()
            grad = QLinearGradient(0, 0, r.width(), 0)
            grad.setColorAt(p1, start_col)
            grad.setColorAt(p2, end_col)
            self._item.setBrush(QBrush(grad))
            self._update_gradient_button(start_col, end_col)
            self._notify_change()

    def _update_fill_button(self, color: str):
        self.fill_btn.setStyleSheet(f"background:{color};")

    def _update_gradient_button(self, start: QColor, end: QColor):
        self.gradient_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 %s,"
            " stop:1 %s);"
            % (start.name(), end.name())
        )

    def _flip_horizontal(self):
        if self._item and hasattr(self.parent(), "canvas"):
            self._item.setSelected(True)
            self.parent().canvas.flip_horizontal_selected()

    def _flip_vertical(self):
        if self._item and hasattr(self.parent(), "canvas"):
            self._item.setSelected(True)
            self.parent().canvas.flip_vertical_selected()

    def _set_rotation_axis(self):
        if not self._item:
            return
        r = self._item.boundingRect()
        x, ok = QInputDialog.getDouble(
            self,
            "Axe de rotation",
            "X :",
            r.width() / 2,
            -10000,
            10000,
            2,
        )
        if not ok:
            return
        y, ok = QInputDialog.getDouble(
            self,
            "Axe de rotation",
            "Y :",
            r.height() / 2,
            -10000,
            10000,
            2,
        )
        if not ok:
            return
        self._item.setTransformOriginPoint(x, y)
        self._notify_change()

    def _notify_change(self):
        if self._item and self._item.scene():
            views = self._item.scene().views()
            if views:
                view = views[0]
                if hasattr(view, "_mark_dirty"):
                    view._mark_dirty()
