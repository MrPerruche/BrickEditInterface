import sys
import os
import traceback
import logging
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import qInstallMessageHandler, QtMsgType


LOG_DIR_NAME = 'logs'
LOG_FILE_NAME = 'BrickEditInterface.log'


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

def _get_log_dir():
    if getattr(sys, 'frozen', False):  # Compiled
        base_dir = os.path.dirname(sys.executable)
    else:  # Interpreted
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    log_dir = os.path.join(base_dir, LOG_DIR_NAME)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


# ------------------------------------------------------------
# Setup
# ------------------------------------------------------------

def setup_logging():
    log_dir = _get_log_dir()
    log_path = os.path.join(log_dir, LOG_FILE_NAME)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | [%(name)s]: %(message)s'
    )

    # ---- File handler (always on)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # ---- Console handler (DEV ONLY, VS Code safe)
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

    _redirect_stdout_stderr(root_logger)
    _install_exception_hook(root_logger)
    _install_qt_message_handler(root_logger)

    root_logger.info("Logging initialized")
    root_logger.info(f"Log file: {log_path}")


# ------------------------------------------------------------
# stdout / stderr redirection (print → logging)
# ------------------------------------------------------------

class _StreamRedirector:
    def __init__(self, logger, level):
        self._logger = logger
        self._level = level

    def write(self, message):
        message = message.rstrip()
        if message:
            self._logger.log(self._level, message)

    def flush(self):
        pass


def _redirect_stdout_stderr(logger):
    sys.stdout = _StreamRedirector(logger, logging.INFO)
    sys.stderr = _StreamRedirector(logger, logging.ERROR)


# ------------------------------------------------------------
# Uncaught exceptions
# ------------------------------------------------------------

def _install_exception_hook(logger):
    def excepthook(exc_type, exc_value, exc_tb):
        tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical("Uncaught exception:\n" + tb)

    sys.excepthook = excepthook


# ------------------------------------------------------------
# Qt message handler
# ------------------------------------------------------------

_QT_LOG_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def _install_qt_message_handler(logger):
    def qt_handler(msg_type, context, message):
        level = _QT_LOG_LEVELS.get(msg_type, logging.INFO)
        logger.log(level, f"Qt: {message}")

    qInstallMessageHandler(qt_handler)
