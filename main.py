"""BrickEdit Interface - Main entry point."""

import sys
from PySide6.QtWidgets import QApplication

import resources_rc

from mainwindow import BrickEditInterface


def main():
    app = QApplication(sys.argv)
    
    window = BrickEditInterface()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
