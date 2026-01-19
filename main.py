"""BrickEdit Interface - Main entry point."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
import resources_rc  # your compiled Qt resources

from mainwindow import BrickEditInterface


def main():
    app = QApplication(sys.argv)

    # Title bar icon (cross-platform)
    bei_icon = QIcon(":/assets/icons/brickeditinterface.png")
    app.setWindowIcon(bei_icon)

    window = BrickEditInterface()
    window.setWindowIcon(bei_icon)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
