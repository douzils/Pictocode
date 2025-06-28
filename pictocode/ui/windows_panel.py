from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from PyQt5.QtCore import Qt

class WindowsPanel(QWidget):
    """Permet d'activer ou désactiver différentes fenêtres."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main = main_window
        layout = QVBoxLayout(self)
        self.chk_props = QCheckBox('Propriétés')
        self.chk_toolbar = QCheckBox("Barre d'outils")
        self.chk_imports = QCheckBox('Imports')
        for chk in (
            self.chk_props,
            self.chk_toolbar,
            self.chk_imports,
        ):
            layout.addWidget(chk)
        idx_props = self.main.tabs.indexOf(self.main.inspector)
        self.chk_props.stateChanged.connect(
            lambda s: self.main.tabs.setTabVisible(idx_props, s == Qt.Checked)
        )
        self.chk_toolbar.stateChanged.connect(
            lambda s: self.main.toolbar.setVisible(s == Qt.Checked)
        )
        idx_imports = self.main.tabs.indexOf(self.main.imports)
        self.chk_imports.stateChanged.connect(
            lambda s: self.main.tabs.setTabVisible(idx_imports, s == Qt.Checked)
        )

        # synchronise les cases avec l'état courant sans déclencher de signal
        for chk, idx in (
            (self.chk_props, idx_props),
            (self.chk_toolbar, None),
            (self.chk_imports, idx_imports),
        ):
            chk.blockSignals(True)
            if idx is None:
                visible = self.main.toolbar.isVisible()
            else:
                visible = self.main.tabs.tabBar().isTabVisible(idx)
            chk.setChecked(visible)
            chk.blockSignals(False)
