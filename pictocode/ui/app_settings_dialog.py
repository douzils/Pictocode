from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QDialogButtonBox,
    QLineEdit,
    QColorDialog,
    QSpinBox,
    QCheckBox,
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from typing import Optional, Union


class AppSettingsDialog(QDialog):
    """Dialog to adjust global application settings like appearance."""

    def __init__(
        self,
        current_theme: str = "Light",
        accent: Union[QColor, str] = QColor(42, 130, 218),
        font_size: int = 10,
        menu_color: Optional[Union[QColor, str]] = None,
        toolbar_color: Optional[Union[QColor, str]] = None,
        dock_color: Optional[Union[QColor, str]] = None,
        menu_font_size: Optional[int] = None,
        toolbar_font_size: Optional[int] = None,
        dock_font_size: Optional[int] = None,
        show_splash: bool = True,
        parent=None,
    ):

        super().__init__(parent)
        self.setWindowTitle("Paramètres de l'application")
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        main_layout.addLayout(form)

        # Theme selector
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        idx = self.theme_combo.findText(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)

        form.addRow("Thème :", self.theme_combo)

        # Accent color
        self.accent_color = QColor(accent)
        self.color_edit = QLineEdit(self.accent_color.name())
        self.color_edit.setReadOnly(True)
        self.color_edit.mousePressEvent = lambda e: self._choose_color("accent")
        form.addRow("Couleur d'accent :", self.color_edit)

        # Global font size
        self.font_spin = QSpinBox()
        self.font_spin.setRange(6, 32)
        self.font_spin.setValue(int(font_size))
        form.addRow("Taille de police :", self.font_spin)

        # Per-element colors
        self.menu_color = QColor(menu_color or self.accent_color)
        self.menu_color_edit = QLineEdit(self.menu_color.name())
        self.menu_color_edit.setReadOnly(True)
        self.menu_color_edit.mousePressEvent = lambda e: self._choose_color("menu")
        form.addRow("Couleur menu :", self.menu_color_edit)

        self.toolbar_color = QColor(toolbar_color or self.accent_color)
        self.toolbar_color_edit = QLineEdit(self.toolbar_color.name())
        self.toolbar_color_edit.setReadOnly(True)
        self.toolbar_color_edit.mousePressEvent = lambda e: self._choose_color(
            "toolbar"
        )
        form.addRow("Couleur barre d'outils :", self.toolbar_color_edit)

        self.dock_color = QColor(dock_color or self.accent_color)
        self.dock_color_edit = QLineEdit(self.dock_color.name())
        self.dock_color_edit.setReadOnly(True)
        self.dock_color_edit.mousePressEvent = lambda e: self._choose_color("dock")
        form.addRow("Couleur inspecteur :", self.dock_color_edit)

        # Per-element font sizes
        self.menu_font_spin = QSpinBox()
        self.menu_font_spin.setRange(6, 32)
        self.menu_font_spin.setValue(int(menu_font_size or font_size))
        form.addRow("Police menu :", self.menu_font_spin)

        self.toolbar_font_spin = QSpinBox()
        self.toolbar_font_spin.setRange(6, 32)
        self.toolbar_font_spin.setValue(int(toolbar_font_size or font_size))
        form.addRow("Police barre d'outils :", self.toolbar_font_spin)

        self.dock_font_spin = QSpinBox()
        self.dock_font_spin.setRange(6, 32)
        self.dock_font_spin.setValue(int(dock_font_size or font_size))
        form.addRow("Police inspecteur :", self.dock_font_spin)

        self.show_splash_chk = QCheckBox()
        self.show_splash_chk.setChecked(bool(show_splash))
        form.addRow("Afficher l'écran de démarrage :", self.show_splash_chk)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    # --- accessors -------------------------------------------------------
    def _choose_color(self, target):
        current = getattr(self, f"{target}_color")
        col = QColorDialog.getColor(current, self)
        if col.isValid():
            setattr(self, f"{target}_color", col)
            getattr(self, f"{target}_color_edit").setText(col.name())

    def get_theme(self) -> str:
        return self.theme_combo.currentText()

    def get_accent_color(self) -> QColor:
        return self.accent_color

    def get_font_size(self) -> int:
        return self.font_spin.value()

    def get_menu_color(self) -> QColor:
        return self.menu_color

    def get_toolbar_color(self) -> QColor:
        return self.toolbar_color

    def get_dock_color(self) -> QColor:
        return self.dock_color

    def get_menu_font_size(self) -> int:
        return self.menu_font_spin.value()

    def get_toolbar_font_size(self) -> int:
        return self.toolbar_font_spin.value()

    def get_dock_font_size(self) -> int:
        return self.dock_font_spin.value()

    def get_show_splash(self) -> bool:
        return self.show_splash_chk.isChecked()
