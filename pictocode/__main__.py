#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QSettings
from pictocode.ui.main_window import MainWindow

def main():
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    app = QApplication(sys.argv)
    settings = QSettings("pictocode", "pictocode")
    show_splash = settings.value("show_splash", True, type=bool)
    splash = None
    if show_splash:
        pix = QPixmap(400, 300)
        pix.fill(Qt.white)
        painter = QPainter(pix)
        painter.setPen(QColor("#2a82da"))
        f = QFont()
        f.setPointSize(32)
        painter.setFont(f)
        painter.drawText(pix.rect(), Qt.AlignCenter, "Pictocode")
        painter.end()
        splash = QSplashScreen(pix)
        splash.show()
        app.processEvents()

    window = MainWindow()
    if splash:
        splash.finish(window)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
