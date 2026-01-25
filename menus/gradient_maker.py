from PySide6.QtGui import QIcon

from . import base
from .widgets import *


class GradientMaker(base.BaseMenu):
    def __init__(self, mw):
        super().__init__(mw)

        self.color_selector = ColorSelectorWidget(0, True, True, True)
        self.master_layout.addWidget(self.color_selector)
        

        self.master_layout.addStretch()

    def get_menu_name(self):
        return "Gradient Maker"

    def get_icon(self):
        return QIcon(":/assets/icons/GradientIcon.png")
