from PyQt5.QtWidgets import QMenu, QGraphicsOpacityEffect
from PyQt5.QtCore import QPropertyAnimation

class AnimatedMenu(QMenu):
    """QMenu with a simple fade-in effect when shown."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(150)

    def showEvent(self, event):
        self._effect.setOpacity(0)
        super().showEvent(event)
        self._anim.stop()
        self._anim.setStartValue(0)
        self._anim.setEndValue(1)
        self._anim.start()

