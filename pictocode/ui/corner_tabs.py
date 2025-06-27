from PyQt5.QtWidgets import QWidget, QHBoxLayout, QComboBox, QMenu, QDockWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from ..utils import get_contrast_color

class CornerTabs(QWidget):
    """Dropdown widget used as dock header or floating overlay."""

    tab_selected = pyqtSignal(str)

    def __init__(self, parent=None, overlay=False, color: QColor | None = None):
        super().__init__(parent)
        self._color = QColor(color) if color else None
        self.setObjectName("corner_tabs")
        if overlay:
            self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignLeft)
        self.selector = QComboBox(self)
        self.selector.setObjectName("corner_selector")
        self.selector.addItems([
            "Plan de travail",
            "Propriétés",
            "Imports",
            "Objets",
            "Logs",
        ])
        layout.addWidget(self.selector)
        layout.addStretch()
        self.selector.currentTextChanged.connect(self._emit_change)
        self._handle = None
        if self._color:
            self.set_color(self._color)
        else:
            base_style = (
                "QComboBox#corner_selector { border: none; padding: 0 6px; }"
                "QComboBox#corner_selector::drop-down { border: none; }"
            )
            self.setStyleSheet(base_style)
        self.setFixedHeight(self.selector.sizeHint().height())
        if overlay:
            self.hide()

    def mouseDoubleClickEvent(self, event):
        dock = self.parent()
        if isinstance(dock, QDockWidget) and hasattr(dock.parent(), "_toggle_dock"):
            dock.parent()._toggle_dock(dock)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        """Show a menu allowing the dock to be closed."""
        menu = QMenu(self)
        remove = menu.addAction("Supprimer")
        chosen = menu.exec_(event.globalPos())
        if chosen == remove:
            dock = self.parent()
            if isinstance(dock, QDockWidget):
                dock.close()
        else:
            super().contextMenuEvent(event)

    def add_tab(self, widget, label: str):
        """Compatibility shim for the previous API.

        Only the label is used by the current dropdown based implementation.
        The ``widget`` argument is ignored but kept to avoid runtime errors if
        older code still calls :meth:`add_tab`.
        """
        self.selector.addItem(label)

    def _emit_change(self, text):
        self.tab_selected.emit(text)

    def set_color(self, color: QColor):
        """Apply a background color to the tab bar."""
        self._color = QColor(color)
        text = get_contrast_color(self._color)
        style = (
            f"#corner_tabs {{ background: {self._color.name()}; }}"
            f"QComboBox#corner_selector {{ border: none; padding: 0 6px;"
            f" background: transparent; color: {text}; }}"
            "QComboBox#corner_selector::drop-down { border: none; }"
        )
        self.setStyleSheet(style)
        self.setFixedHeight(self.selector.sizeHint().height())

    # ------------------------------------------------------------------
    # Resize handle support
    def set_handle(self, handle: QWidget):
        """Attach ``handle`` and keep it aligned to the top-right."""
        self._handle = handle
        handle.setParent(self)
        handle.raise_()
        self._position_handle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_handle()

    def _position_handle(self):
        if self._handle:
            self._handle.move(
                self.width() - self._handle.width(),
                0,
            )


