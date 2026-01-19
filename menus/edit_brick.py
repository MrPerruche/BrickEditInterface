from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QSizePolicy

from . import base
from .widgets import VehicleWidget, ColorWidget, LargeLabel, BrickListWidget

from brickedit.src.brickedit import *


class EditBrickMenu(base.BaseMenu):
    """Menu for editing brick properties."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # label = QLabel("Edit Brick")
        # button = QPushButton("Apply")
        self.header_label = LargeLabel(self.get_menu_name(), 2)
        layout.addWidget(self.header_label)
    
        self.vehicle_selector = VehicleWidget([self.on_brv_reload])
        layout.addWidget(self.vehicle_selector)

        self.color_selector = ColorWidget(lambda: self.vehicle_selector.brv)
        layout.addWidget(self.color_selector)

        self.bricks_widget = BrickListWidget([])
        layout.addWidget(self.bricks_widget)

        layout.addStretch()

    def get_menu_name(self) -> str:
        return "Brick Editor"

    def get_icon_path(self) -> str:
        return ":/assets/icons/placeholder.png"

    def on_brv_reload(self):
        brv = self.vehicle_selector.brv
        if brv is None:
            self.bricks_widget.update_brick_widgets([])
            return
        
        matching_bricks = [b for b in brv.bricks if b.get_property(p.BRICK_COLOR) == self.color_selector.color]
        self.bricks_widget.update_brick_widgets(matching_bricks)
