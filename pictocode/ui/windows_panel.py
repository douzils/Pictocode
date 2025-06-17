from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from PyQt5.QtCore import Qt

class WindowsPanel(QWidget):
    """Permet d'activer ou désactiver différentes fenêtres."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main = main_window
        layout = QVBoxLayout(self)
        self.chk_layers = QCheckBox('Calques')
        self.chk_props = QCheckBox('Propriétés')
        self.chk_toolbar = QCheckBox("Barre d'outils")
        self.chk_imports = QCheckBox('Imports')
        for chk in (self.chk_layers, self.chk_props, self.chk_toolbar, self.chk_imports):
            layout.addWidget(chk)
        self.chk_layers.stateChanged.connect(lambda s: self.main.layers_dock.setVisible(s == Qt.Checked))
        self.chk_props.stateChanged.connect(lambda s: self.main.inspector_dock.setVisible(s == Qt.Checked))
        self.chk_toolbar.stateChanged.connect(lambda s: self.main.toolbar.setVisible(s == Qt.Checked))
        self.chk_imports.stateChanged.connect(lambda s: self.main.imports_dock.setVisible(s == Qt.Checked))
        # états initiaux
        self.chk_props.setChecked(True)
        self.chk_toolbar.setChecked(True)
