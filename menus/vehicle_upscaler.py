from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout

from . import base


class VehicleUpscalerMenu(base.BaseMenu):
    """Menu for upscaling vehicle properties."""

    def __init__(self):
        super().__init__()

        label = QLabel("Upscale Vehicle")
        button = QPushButton("Test")

        self.master_layout.addWidget(label)
        self.master_layout.addWidget(button)
        self.master_layout.addStretch()

    def get_menu_name(self) -> str:
        return "Vehicle Upscaler"

    def get_icon_path(self) -> str:
        return ":/assets/icons/placeholder.png"
