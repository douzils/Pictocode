from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QListWidgetItem,
    QGraphicsOpacityEffect,
)
from PyQt5.QtGui import QIcon, QPainterPath
from PyQt5.QtCore import (
    Qt,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
    QRegion,
    QRectF,
)

class ProjectTile(QWidget):
    """Widget affichant une miniature de projet avec overlay et titre au survol."""

    def __init__(
        self,
        icon: QIcon,
        title: str,
        width=128,
        height=None,
        parent=None,
    ):
        super().__init__(parent)
        self._width = int(width)
        self._height = int(height or width)
        self._item: QListWidgetItem | None = None

        self.setObjectName("project_tile")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("tile_title")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.hide()
        layout.addWidget(self.title_label)

        self.preview = QLabel(self)
        self.preview.setObjectName("tile_preview")
        self.preview.setFixedSize(self._width, self._height)
        self.preview.setPixmap(icon.pixmap(self._width, self._height))
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setScaledContents(True)
        layout.addWidget(self.preview)
        self._update_clip()

        self.overlay = QLabel(self.preview)
        self.overlay.setObjectName("tile_overlay")
        self.overlay.setGeometry(self.preview.rect())
        self.overlay.raise_()
        self.overlay.show()

        self.setStyleSheet(
            """
            #project_tile {
                background: #b04848;
                border-radius: 18px;
            }
            QLabel#tile_preview {
                border-radius: 18px;
            }
            QLabel#tile_overlay {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 18px;
            }
            QLabel#tile_title {
                color: white;
                font-weight: bold;
            }
            """
        )

        # Effets d'opacite pour l'overlay et le titre
        self.overlay_effect = QGraphicsOpacityEffect(self.overlay)
        self.overlay.setGraphicsEffect(self.overlay_effect)
        self.overlay_effect.setOpacity(1.0)

        self.title_effect = QGraphicsOpacityEffect(self.title_label)
        self.title_label.setGraphicsEffect(self.title_effect)
        self.title_effect.setOpacity(0.0)

        self.fade_overlay = QPropertyAnimation(self.overlay_effect, b"opacity", self)
        self.fade_overlay.setDuration(150)
        self.fade_overlay.setEasingCurve(QEasingCurve.OutCubic)

        self.fade_title = QPropertyAnimation(self.title_effect, b"opacity", self)
        self.fade_title.setDuration(150)
        self.fade_title.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_title.finished.connect(self._on_title_anim_finished)
    def set_item(self, item: QListWidgetItem):
        """Assure que la taille de l'item suit celle du widget."""
        self._item = item
        item.setSizeHint(self.sizeHint())

    # ------------------------------------------------------------------
    # Events
    def enterEvent(self, event):
        self.title_label.show()
        self.fade_title.stop()
        self.fade_title.setStartValue(self.title_effect.opacity())
        self.fade_title.setEndValue(1.0)
        self.fade_title.start()

        self.fade_overlay.stop()
        self.fade_overlay.setStartValue(self.overlay_effect.opacity())
        self.fade_overlay.setEndValue(0.0)
        self.fade_overlay.start()
        self._update_item_size()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.fade_title.stop()
        self.fade_title.setStartValue(self.title_effect.opacity())
        self.fade_title.setEndValue(0.0)
        self.fade_title.start()

        self.fade_overlay.stop()
        self.fade_overlay.setStartValue(self.overlay_effect.opacity())
        self.fade_overlay.setEndValue(1.0)
        self.fade_overlay.start()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        self.overlay.setGeometry(self.preview.rect())
        self._update_clip()
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    def sizeHint(self) -> QSize:
        h = self._height
        if self.title_label.isVisible():
            h += self.title_label.sizeHint().height()
        return QSize(self._width, h)

    def _update_item_size(self):
        if self._item is not None:
            self._item.setSizeHint(self.sizeHint())

    def _on_title_anim_finished(self):
        if self.title_effect.opacity() == 0:
            self.title_label.hide()
        self._update_item_size()

    def _update_clip(self):
        path = QPainterPath()
        rect = QRectF(self.preview.rect())
        path.addRoundedRect(rect, 18, 18)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.preview.setMask(region)
        self.overlay.setMask(region)
