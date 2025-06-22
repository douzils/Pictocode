import logging
from PyQt5.QtCore import QObject, pyqtSignal

class LogEmitter(QObject):
    log_record = pyqtSignal(str)

log_emitter = LogEmitter()

class QtHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_emitter.log_record.emit(msg)

def setup_logging():
    logger = logging.getLogger()
    if logger.handlers:
        return
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    qt_handler = QtHandler()
    qt_handler.setFormatter(fmt)
    logger.addHandler(qt_handler)
