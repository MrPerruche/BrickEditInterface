from PySide6.QtWidgets import QVBoxLayout

from . import base
from .widgets import *



class HomeMenu(base.BaseMenu):
    
    def __init__(self):
        super().__init__(header=False)

        self.welcome_label = LargeLabel("Welcome to\nBrickEdit-Interface", 1, center_text=True)
        self.master_layout.addWidget(self.welcome_label)

        self.brickeditinterface_logo = QPixmap(":/assets/icons/brickeditinterface.png")
        self.brickeditinterface_logo = self.brickeditinterface_logo.scaled(
            300, 300, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        self.brickeditinterface_label = QLabel()
        self.brickeditinterface_label.setPixmap(self.brickeditinterface_logo)
        self.master_layout.addWidget(self.brickeditinterface_label)

        self.master_layout.addStretch()

    def get_menu_name(self) -> str:
        return "Home"

    def get_icon_path(self) -> str:
        return ":/assets/icons/placeholder.png"
