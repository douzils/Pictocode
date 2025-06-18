from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtCore import Qt

class StepSpinBox(QSpinBox):
    """SpinBox with adjustable wheel step and precision."""

    def __init__(self, parent=None, base_step=1):
        super().__init__(parent)
        self._base_step = base_step
        self._level = 1
        self.setSingleStep(base_step)

    def wheelEvent(self, event):
        step = self._base_step * self._level
        if event.modifiers() & Qt.ShiftModifier:
            step = step / 10 if step > 0 else step
        delta = event.angleDelta().y()
        if delta > 0:
            self.setValue(self.value() + step)
        else:
            self.setValue(self.value() - step)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self._level += 1
        elif event.key() == Qt.Key_Minus:
            self._level = max(1, self._level - 1)
        else:
            super().keyPressEvent(event)
        self.setSingleStep(self._base_step * self._level)
