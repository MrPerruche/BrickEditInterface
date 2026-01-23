from PySide6.QtWidgets import QLabel, QPushButton
from PySide6.QtGui import QIcon

from . import base


class VehicleUpscalerMenu(base.BaseMenu):
    """Menu for upscaling vehicle properties."""

    def __init__(self, mw):
        super().__init__(mw)

        label = QLabel("Upscale Vehicle")
        button = QPushButton("Test")

        self.master_layout.addWidget(label)
        self.master_layout.addWidget(button)
        self.master_layout.addStretch()

    def get_menu_name(self) -> str:
        return "Vehicle Upscaler"

    def get_icon(self) -> QIcon:
        return QIcon(":/assets/icons/placeholder.png")
