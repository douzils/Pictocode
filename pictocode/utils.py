# pictocode/utils.py
"""
Fonctions d'export (génération de code), conversion de couleurs, etc.
"""


def color_to_hex(qcolor):
    """Convertit un QColor en chaîne hex."""
    r = qcolor.red()
    g = qcolor.green()
    b = qcolor.blue()
    return f"#{r:02X}{g:02X}{b:02X}"


def get_contrast_color(qcolor):
    """Return '#000000' or '#ffffff' depending on brightness for
    readability."""
    from PyQt5.QtGui import QColor

    color = QColor(qcolor)
    lum = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return "#000000" if lum > 186 else "#ffffff"


def generate_pycode(shapes):
    """Génère du code Python (PyQt5) reproduisant la scène fournie."""

    lines = [
        "from PyQt5.QtWidgets import (",
        "    QGraphicsScene, QGraphicsRectItem, QGraphicsEllipseItem,",
        "    QGraphicsLineItem, QGraphicsPathItem, QGraphicsPolygonItem,",
        "    QGraphicsTextItem",
        ")",
        (
            "from PyQt5.QtGui import QPen, QBrush, QColor, QPainterPath, "
            "QPolygonF"
        ),
        "from PyQt5.QtCore import QPointF",
        "",
        "scene = QGraphicsScene()",
        "",
    ]

    for i, shp in enumerate(shapes):
        cls = type(shp).__name__
        lines.append(f"# shape {i} - {cls}")

        if cls == "Rect":
            r = shp.rect()
            lines.append(
                f"rect{i} = QGraphicsRectItem("
                f"{r.x()}, {r.y()}, {r.width()}, {r.height()})"
            )
            color = shp.pen().color().name()
            width = shp.pen().width()
            lines.append(f"rect{i}.setPen(QPen(QColor('{color}'), {width}))")
            if shp.brush().style() != 0:
                fill = shp.brush().color().name()
                lines.append(f"rect{i}.setBrush(QBrush(QColor('{fill}')))")
            lines.append(f"rect{i}.setPos({shp.x()}, {shp.y()})")
            if shp.rotation() != 0:
                lines.append(f"rect{i}.setRotation({shp.rotation()})")
            if shp.zValue() != 0:
                lines.append(f"rect{i}.setZValue({shp.zValue()})")
            lines.append(f"scene.addItem(rect{i})")

        elif cls == "Ellipse":
            e = shp.rect()
            lines.append(
                f"ellipse{i} = QGraphicsEllipseItem("
                f"{e.x()}, {e.y()}, {e.width()}, {e.height()})"
            )
            color = shp.pen().color().name()
            width = shp.pen().width()
            lines.append(
                f"ellipse{i}.setPen(QPen(QColor('{color}'), {width}))")
            if shp.brush().style() != 0:
                fill = shp.brush().color().name()
                lines.append(f"ellipse{i}.setBrush(QBrush(QColor('{fill}')))")
            lines.append(f"ellipse{i}.setPos({shp.x()}, {shp.y()})")
            if shp.rotation() != 0:
                lines.append(f"ellipse{i}.setRotation({shp.rotation()})")
            if shp.zValue() != 0:
                lines.append(f"ellipse{i}.setZValue({shp.zValue()})")
            lines.append(f"scene.addItem(ellipse{i})")

        elif cls == "Line":
            line = shp.line()
            lines.append(
                f"line{i} = QGraphicsLineItem("
                f"{line.x1()}, {line.y1()}, {line.x2()}, {line.y2()})"
            )
            color = shp.pen().color().name()
            width = shp.pen().width()
            lines.append(f"line{i}.setPen(QPen(QColor('{color}'), {width}))")
            lines.append(f"line{i}.setPos({shp.x()}, {shp.y()})")
            if shp.rotation() != 0:
                lines.append(f"line{i}.setRotation({shp.rotation()})")
            if shp.zValue() != 0:
                lines.append(f"line{i}.setZValue({shp.zValue()})")
            lines.append(f"scene.addItem(line{i})")

        elif cls == "FreehandPath":
            path = shp.path()
            pts = [path.elementAt(j) for j in range(path.elementCount())]
            is_poly = len(
                pts) > 2 and pts[0].x == pts[-1].x and pts[0].y == pts[-1].y
            if is_poly:
                lines.append(f"poly{i} = QPolygonF([")
                for p in pts[:-1]:
                    lines.append(f"    QPointF({p.x}, {p.y}),")
                lines.append("])")
                lines.append(f"poly_item{i} = QGraphicsPolygonItem(poly{i})")
                color = shp.pen().color().name()
                width = shp.pen().width()
                lines.append(
                    f"poly_item{i}.setPen(QPen(QColor('{color}'), {width}))")
                if shp.brush().style() != 0:
                    fill = shp.brush().color().name()
                    lines.append(
                        f"poly_item{i}.setBrush(QBrush(QColor('{fill}')))")
                lines.append(f"poly_item{i}.setPos({shp.x()}, {shp.y()})")
                if shp.rotation() != 0:
                    lines.append(f"poly_item{i}.setRotation({shp.rotation()})")
                if shp.zValue() != 0:
                    lines.append(f"poly_item{i}.setZValue({shp.zValue()})")
                lines.append(f"scene.addItem(poly_item{i})")
            else:
                lines.append(f"path{i} = QPainterPath()")
                for idx, p in enumerate(pts):
                    cmd = "moveTo" if idx == 0 else "lineTo"
                    lines.append(f"path{i}.{cmd}({p.x}, {p.y})")
                lines.append(f"path_item{i} = QGraphicsPathItem(path{i})")
                color = shp.pen().color().name()
                width = shp.pen().width()
                lines.append(
                    f"path_item{i}.setPen(QPen(QColor('{color}'), {width}))")
                if shp.brush().style() != 0:
                    fill = shp.brush().color().name()
                    lines.append(
                        f"path_item{i}.setBrush(QBrush(QColor('{fill}')))")
                lines.append(f"path_item{i}.setPos({shp.x()}, {shp.y()})")
                if shp.rotation() != 0:
                    lines.append(f"path_item{i}.setRotation({shp.rotation()})")
                if shp.zValue() != 0:
                    lines.append(f"path_item{i}.setZValue({shp.zValue()})")
                lines.append(f"scene.addItem(path_item{i})")

        elif cls == "TextItem":
            text = shp.toPlainText().replace("'", "\\'")
            lines.append(f"text{i} = QGraphicsTextItem('{text}')")
            lines.append(f"text{i}.setPos({shp.x()}, {shp.y()})")
            color = shp.defaultTextColor().name()
            size = shp.font().pointSize()
            lines.append(f"font{i} = text{i}.font()")
            lines.append(f"font{i}.setPointSize({size})")
            lines.append(f"text{i}.setFont(font{i})")
            lines.append(f"text{i}.setDefaultTextColor(QColor('{color}'))")
            if shp.rotation() != 0:
                lines.append(f"text{i}.setRotation({shp.rotation()})")
            if shp.zValue() != 0:
                lines.append(f"text{i}.setZValue({shp.zValue()})")
            lines.append(f"scene.addItem(text{i})")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
def to_pixels(value: float, unit: str, dpi: float = 72) -> float:
    """Convertit une longueur dans l'unité donnée vers des pixels."""
    unit = unit.lower()
    if unit == "px":
        return float(value)
    if unit == "pt":
        return float(value) * dpi / 72.0
    if unit == "mm":
        return float(value) * dpi / 25.4
    if unit == "cm":
        return float(value) * dpi / 2.54
    if unit == "in":
        return float(value) * dpi
    return float(value)
