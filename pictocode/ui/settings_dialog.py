from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QDialogButtonBox,
    QListWidget,
    QStackedWidget,
    QWidget,
    QLineEdit,
    QColorDialog,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QLabel,
    QKeySequenceEdit,
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class SettingsDialog(QDialog):
    """Combined preferences dialog with tabs."""

    DOCK_NAMES = ["Propriétés", "Imports", "Objets", "Logs"]

    def __init__(
        self,
        shortcuts: dict[str, str],
        current_theme: str = "Light",
        accent: QColor | str = QColor(0, 120, 215),
        font_size: int = 10,
        menu_color: QColor | str | None = None,
        toolbar_color: QColor | str | None = None,
        dock_color: QColor | str | None = None,
        menu_font_size: int | None = None,
        toolbar_font_size: int | None = None,
        dock_font_size: int | None = None,
        show_splash: bool = True,
        autosave_enabled: bool = False,
        autosave_interval: int = 5,
        auto_show_inspector: bool = True,
        float_docks: bool = False,
        dock_title_colors: dict[str, QColor] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Préférences")
        self.setModal(True)

        dock_title_colors = dock_title_colors or {}
        self.dock_title_colors = {
            name: QColor(dock_title_colors.get(name, toolbar_color or accent))
            for name in self.DOCK_NAMES
        }

        layout = QVBoxLayout(self)

        content_layout = QHBoxLayout()
        layout.addLayout(content_layout)

        self.category_list = QListWidget()
        self.category_list.setFixedWidth(150)
        self.category_list.setFrameShape(QListWidget.NoFrame)
        self.category_list.setSpacing(2)
        content_layout.addWidget(self.category_list)

        self.pages = QStackedWidget(self)
        content_layout.addWidget(self.pages, 1)

        # --- General tab -------------------------------------------------
        gen = QWidget()
        gen_form = QFormLayout(gen)
        self.show_splash_chk = QCheckBox()
        self.show_splash_chk.setChecked(bool(show_splash))
        gen_form.addRow("Afficher l'écran de démarrage :", self.show_splash_chk)

        self.autosave_chk = QCheckBox()
        self.autosave_chk.setChecked(bool(autosave_enabled))
        gen_form.addRow("Sauvegarde auto :", self.autosave_chk)

        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(1, 60)
        self.autosave_spin.setValue(int(autosave_interval))
        gen_form.addRow("Intervalle (min) :", self.autosave_spin)

        self.auto_show_chk = QCheckBox()
        self.auto_show_chk.setChecked(bool(auto_show_inspector))
        gen_form.addRow("Ouvrir inspecteur sur sélection :", self.auto_show_chk)

        self.float_docks_chk = QCheckBox()
        self.float_docks_chk.setChecked(bool(float_docks))
        gen_form.addRow("Fenêtres flottantes :", self.float_docks_chk)

        self.pages.addWidget(gen)
        self.category_list.addItem("Général")

        # --- Appearance tab ---------------------------------------------
        app = QWidget()
        app_form = QFormLayout(app)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        idx = self.theme_combo.findText(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        app_form.addRow("Thème :", self.theme_combo)

        self.accent_color = QColor(accent)
        self.color_edit = QLineEdit(self.accent_color.name())
        self.color_edit.setReadOnly(True)
        self.color_edit.mousePressEvent = lambda e: self._choose_color("accent")
        app_form.addRow("Couleur d'accent :", self.color_edit)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(6, 32)
        self.font_spin.setValue(int(font_size))
        app_form.addRow("Taille de police :", self.font_spin)

        self.menu_color = QColor(menu_color or self.accent_color)
        self.menu_color_edit = QLineEdit(self.menu_color.name())
        self.menu_color_edit.setReadOnly(True)
        self.menu_color_edit.mousePressEvent = lambda e: self._choose_color("menu")
        app_form.addRow("Couleur menu :", self.menu_color_edit)

        self.toolbar_color = QColor(toolbar_color or self.accent_color)
        self.toolbar_color_edit = QLineEdit(self.toolbar_color.name())
        self.toolbar_color_edit.setReadOnly(True)
        self.toolbar_color_edit.mousePressEvent = lambda e: self._choose_color("toolbar")
        app_form.addRow("Couleur barre d'outils :", self.toolbar_color_edit)

        self.dock_color = QColor(dock_color or self.accent_color)
        self.dock_color_edit = QLineEdit(self.dock_color.name())
        self.dock_color_edit.setReadOnly(True)
        self.dock_color_edit.mousePressEvent = lambda e: self._choose_color("dock")
        app_form.addRow("Couleur inspecteur :", self.dock_color_edit)

        self.menu_font_spin = QSpinBox()
        self.menu_font_spin.setRange(6, 32)
        self.menu_font_spin.setValue(int(menu_font_size or font_size))
        app_form.addRow("Police menu :", self.menu_font_spin)

        self.toolbar_font_spin = QSpinBox()
        self.toolbar_font_spin.setRange(6, 32)
        self.toolbar_font_spin.setValue(int(toolbar_font_size or font_size))
        app_form.addRow("Police barre d'outils :", self.toolbar_font_spin)

        self.dock_font_spin = QSpinBox()
        self.dock_font_spin.setRange(6, 32)
        self.dock_font_spin.setValue(int(dock_font_size or font_size))
        app_form.addRow("Police inspecteur :", self.dock_font_spin)

        # per dock title colors
        self._dock_color_edits = {}
        for name in self.DOCK_NAMES:
            col = self.dock_title_colors[name]
            edit = QLineEdit(col.name())
            edit.setReadOnly(True)
            edit.mousePressEvent = lambda e, n=name: self._choose_dock_color(n)
            app_form.addRow(f"Couleur {name} :", edit)
            self._dock_color_edits[name] = edit

        self.pages.addWidget(app)
        self.category_list.addItem("Apparence")

        # --- Shortcuts tab ----------------------------------------------
        sh = QWidget()
        sh_form = QFormLayout(sh)
        self._short_edits = {}
        for name, seq in shortcuts.items():
            edit = QKeySequenceEdit(seq, self)
            sh_form.addRow(name + " :", edit)
            self._short_edits[name] = edit
        self.pages.addWidget(sh)
        self.category_list.addItem("Raccourcis")

        # --- Credits tab -------------------------------------------------
        cr = QWidget()
        cr_layout = QVBoxLayout(cr)
        cr_label = QLabel("Pictocode\n(c) 2023")
        cr_label.setAlignment(Qt.AlignCenter)
        cr_layout.addWidget(cr_label)
        cr_layout.addStretch()
        self.pages.addWidget(cr)
        self.category_list.addItem("Crédits")

        self.category_list.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.category_list.setCurrentRow(0)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # --- internals ------------------------------------------------------
    def _choose_color(self, target):
        current = getattr(self, f"{target}_color")
        col = QColorDialog.getColor(current, self)
        if col.isValid():
            setattr(self, f"{target}_color", col)
            getattr(self, f"{target}_color_edit").setText(col.name())

    def _choose_dock_color(self, name):
        col = QColorDialog.getColor(self.dock_title_colors[name], self)
        if col.isValid():
            self.dock_title_colors[name] = col
            self._dock_color_edits[name].setText(col.name())

    # --- accessors ------------------------------------------------------
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

    def get_autosave_enabled(self) -> bool:
        return self.autosave_chk.isChecked()

    def get_autosave_interval(self) -> int:
        return self.autosave_spin.value()

    def get_auto_show_inspector(self) -> bool:
        return self.auto_show_chk.isChecked()

    def get_float_docks(self) -> bool:
        return self.float_docks_chk.isChecked()

    def get_dock_title_colors(self) -> dict[str, QColor]:
        return self.dock_title_colors

    def get_shortcuts(self) -> dict[str, str]:
        return {
            name: edit.keySequence().toString()
            for name, edit in self._short_edits.items()
        }
