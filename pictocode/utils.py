# pictocode/utils.py
"""
Fonctions d'export (génération de code), conversion de couleurs, etc.
"""

def color_to_hex(qcolor):
    """Convertit un QColor en chaîne hex."""
    r = qcolor.red()
    g = qcolor.green()
    b = qcolor.blue()
    return f'#{r:02X}{g:02X}{b:02X}'

def generate_pycode(shapes):
    """
    Exemple très simplifié : génère du code Python PyQt5 qui 
    re-crée les shapes passées en argument.
    """
    lines = ['from PyQt5.QtWidgets import QGraphicsRectItem', '']
    for i, shp in enumerate(shapes):
        if hasattr(shp, 'rect'):
            x, y, w, h = shp.rect().getRect()
            lines.append(f'# shape {i}')
            lines.append(f'rect{i} = QGraphicsRectItem({x}, {y}, {w}, {h})')
            lines.append(f'scene.addItem(rect{i})')
            lines.append('')
    return '\n'.join(lines)

# ---------------------------------------------------------------------------
def to_pixels(value: float, unit: str, dpi: float = 72) -> float:
    """Convertit une longueur dans l'unité donnée vers des pixels."""
    unit = unit.lower()
    if unit == 'px':
        return float(value)
    if unit == 'pt':
        return float(value) * dpi / 72.0
    if unit == 'mm':
        return float(value) * dpi / 25.4
    if unit == 'cm':
        return float(value) * dpi / 2.54
    if unit == 'in':
        return float(value) * dpi
    return float(value)

