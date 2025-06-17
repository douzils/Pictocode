# pictocode/__main__.py
import sys
import os
from PyQt5.QtWidgets import QApplication
from pictocode.ui.main_window import MainWindow


def main():
    if os.name == "nt":
        import ctypes

        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
