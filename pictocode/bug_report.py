import sys
import os
import traceback
from datetime import datetime

LOG_DIR = os.path.join(os.path.expanduser("~"), "pictocode_logs")
LOG_FILE = os.path.join(LOG_DIR, "pictocode.log")


def _excepthook(exc_type, exc_value, exc_tb):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n=== {datetime.now().isoformat()} ===\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    # Call the default hook to allow default handling (prints to stderr)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def install_excepthook():
    """Install global exception handler that logs uncaught exceptions."""
    sys.excepthook = _excepthook
