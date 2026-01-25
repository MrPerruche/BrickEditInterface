from PySide6.QtWidgets import QPushButton, QMessageBox
from PySide6.QtGui import QIcon
from os import path, makedirs

from . import base
from .widgets import VehicleWidget, VehicleWidgetMode, ColorWidget, BrickListWidget

from brickedit import *
from utils import try_serialize


class EditBrickMenu(base.BaseMenu):
    """Menu for editing brick properties."""

    def __init__(self, mw):
        super().__init__(mw)
    
        self.vehicle_selector = VehicleWidget(VehicleWidgetMode.SELECT_AND_RELOAD, [self.on_brv_reload])
        self.master_layout.addWidget(self.vehicle_selector)

        self.color_selector = ColorWidget(lambda: self.vehicle_selector.brv)
        self.master_layout.addWidget(self.color_selector)

        self.bricks_widget = BrickListWidget([])
        self.master_layout.addWidget(self.bricks_widget)

        self.save_button = QPushButton("Save changes")
        self.save_button.clicked.connect(self.save_changes)
        self.master_layout.addWidget(self.save_button)

        self.master_layout.addStretch()

    def get_menu_name(self) -> str:
        return "Brick Editor"

    def get_icon(self) -> QIcon:
        return QIcon(":/assets/icons/BrickEditorIcon.png")

    def on_brv_reload(self):
        brv = self.vehicle_selector.brv
        if brv is None:
            self.bricks_widget.update_brick_widgets([])
            return
        
        matching_bricks = [(i, b) for i, b in enumerate(brv.bricks) if b.get_property(p.BRICK_COLOR) == self.color_selector.color]
        self.bricks_widget.update_brick_widgets(matching_bricks)

    def save_changes(self):
        # Create backup
        if self.vehicle_selector.brv_file is None:
            QMessageBox.warning(self, "No vehicle selected", "No vehicle selected. Please select a vehicle before saving changes.")
            return
        vehicle_dir = path.dirname(self.vehicle_selector.brv_file)
        self.main_window.backups.full_backup_procedure(vehicle_dir, f"Modified using the {self.get_menu_name()}.")

        # Save (and make sure the path exists)
        makedirs(path.dirname(self.vehicle_selector.brv_file), exist_ok=True)

        # Get the BRV with modified bricks
        brv = self.vehicle_selector.brv
        for brick_widget in self.bricks_widget.brick_widgets:
            brv.bricks[brick_widget.idx] = brick_widget.get_modified_brick()

        # Serialize and save
        serialized = try_serialize(brv.serialize())
        if serialized is None:
            return
        with open(self.vehicle_selector.brv_file, "wb") as f:
            f.write(serialized)

        QMessageBox.information(self, "BrickEdit-Interface", "Successfully saved changes.")
