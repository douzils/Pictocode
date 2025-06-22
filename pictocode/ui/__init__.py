"""Expose core UI widgets for convenient imports."""

from .main_window import MainWindow
from .animated_menu import AnimatedMenu
from .title_bar import TitleBar
from .project_tile import ProjectTile
from .gradient_editor import GradientEditorDialog
from .layers_dock import LayersWidget
from .layout_dock import LayoutWidget

__all__ = [
    "MainWindow",
    "AnimatedMenu",
    "TitleBar",
    "ProjectTile",
    "GradientEditorDialog",
    "LayersWidget",
    "LayoutWidget",
]
