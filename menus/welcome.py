from PySide6.QtWidgets import QSizePolicy
from PySide6.QtGui import QIcon

from . import base
from .widgets import *


class HomeMenu(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw, header=False)

        self._logo_pixmap = QPixmap(':/assets/icons/brickeditinterface.png')

        self.brickeditinterface_label = QLabel()
        self.brickeditinterface_label.setAlignment(Qt.AlignCenter)
        self.brickeditinterface_label.setScaledContents(False)
        self.brickeditinterface_label.setMinimumSize(0, 0)
        self.brickeditinterface_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.master_layout.addWidget(self.brickeditinterface_label)

        self.welcome_label = QLabel(
            "blah blah blah blah blah blah blah blahblah blah blah blahblah blah blah blah"
        )
        self.welcome_label.setWordWrap(True)
        self.master_layout.addWidget(self.welcome_label)


        self.master_layout.addStretch()

        self._update_logo()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_logo()

    def _update_logo(self):
        if self._logo_pixmap.isNull():
            return

        size = self.brickeditinterface_label.contentsRect().size()
        size.setWidth(size.width() // 1.01)
        size.setHeight(size.height() // 1.01)

        if size.width() <= 0 or size.height() <= 0:
            return

        scaled = self._logo_pixmap.scaled(
            size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.brickeditinterface_label.setPixmap(scaled)


    def get_menu_name(self):
        return "Welcome"

    def get_icon(self):
        return QIcon(':/assets/icons/brickeditinterface.ico')
