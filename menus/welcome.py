from PySide6.QtWidgets import QVBoxLayout

from . import base
from .widgets import *



class HomeMenu(base.BaseMenu):
    
    def __init__(self):
        super().__init__()

        self.master_layout = QVBoxLayout(self)
        self.welcome_label = LargeLabel("Welcome to\nBrickEdit-Interface", 1, center_text=True)
        self.master_layout.addWidget(self.welcome_label)
        self.master_layout.addStretch()


    def get_menu_name(self) -> str:
        return "Home"

    def get_icon_path(self) -> str:
        return "assets/icons/placeholder.png"
