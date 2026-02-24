"""BrickEdit Interface - Main entry point."""

from sys import argv, exit as sys_exit
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
import resources_rc  # your compiled Qt resources
from systems.log import setup_logging

from mainwindow import BrickEditInterface

def main():
    setup_logging()

    app = QApplication(argv)

    # Title bar icon (cross-platform)
    bei_icon = QIcon(":/assets/icons/brickeditinterface.ico")
    app.setWindowIcon(bei_icon)

    window = BrickEditInterface()
    window.setWindowIcon(bei_icon)

    window.show()
    sys_exit(app.exec())


if __name__ == "__main__":
    main()
