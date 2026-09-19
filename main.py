"""BrickEdit Interface - Main entry point."""

from sys import argv, exit as sys_exit
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase, QFont
import resources_rc  # your compiled Qt resources
from systems.log import setup_logging

from mainwindow import BrickEditInterface

import traceback
from PySide6.QtCore import QObject, QEvent
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QWidget

# If random widgets start appearing and dissapearing for a split second again before startup, this stuff can be used to find them
#  (uncomment below app too)
# class ShowSpy(QObject):
#     def eventFilter(self, obj, event):
#         if event.type() == QEvent.Type.Show:
#             if (isinstance(obj, QWidget) and obj.isWindow()) or isinstance(obj, QWindow):
#                 print(f"[show] {type(obj).__name__} name={obj.objectName()!r} size={obj.size()}")
#                 traceback.print_stack(limit=10)
#         return False

def main():
    setup_logging()

    app = QApplication(argv)
    # spy = ShowSpy()
    # app.installEventFilter(spy)

    font_id = QFontDatabase.addApplicationFont(":/assets/fonts/SofiaSansCondensed-VariableFont_wght.ttf")
    QFontDatabase.addApplicationFont(":/assets/fonts/SofiaSansCondensed-Italic-VariableFont_wght.ttf")
    family = QFontDatabase.applicationFontFamilies(font_id)[0]
    app.setFont(QFont(family))

    # Title bar icon (cross-platform)
    bei_icon = QIcon(":/assets/icons/brickeditinterface.ico")
    app.setWindowIcon(bei_icon)

    window = BrickEditInterface()
    window.setWindowIcon(bei_icon)

    window.show()
    sys_exit(app.exec())


if __name__ == "__main__":
    main()
