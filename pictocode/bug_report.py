import sys
import os
import traceback
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMessageBox

LOG_DIR = os.path.join(os.path.expanduser("~"), "pictocode_logs")
LOG_FILE = os.path.join(LOG_DIR, "pictocode.log")


def _excepthook(exc_type, exc_value, exc_tb):
    """Write the traceback to a log file and show a user-friendly dialog."""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n=== {datetime.now().isoformat()} ===\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)

    # Attempt to show a message box if a QApplication is running
    app = QApplication.instance()
    if app is not None:
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Pictocode - Erreur")
            msg.setText(
                "Une erreur inattendue est survenue. "
                f"Un rapport a été enregistré dans:\n{LOG_FILE}"
            )
            details = "".join(
                traceback.format_exception(exc_type, exc_value, exc_tb)
            )
            msg.setDetailedText(details)
            msg.exec_()
        except Exception:
            # Ignore any error while displaying the dialog
            pass

    # Call the default hook to allow default handling (prints to stderr)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def install_excepthook():
    """Install global exception handler that logs uncaught exceptions."""
    sys.excepthook = _excepthook
