from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QSizePolicy, QMessageBox
from PySide6.QtGui import QIcon
import os

from . import base
from .widgets import VehicleWidget, ColorWidget, LargeLabel, BrickListWidget

from brickedit.src.brickedit import *


class EditBrickMenu(base.BaseMenu):
    """Menu for editing brick properties."""

    def __init__(self, mw):
        super().__init__(mw)
    
        self.vehicle_selector = VehicleWidget([self.on_brv_reload])
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
        return QIcon(":/assets/icons/placeholder.png")

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
        vehicle_dir = os.path.dirname(self.vehicle_selector.brv_file)
        self.main_window.backups.full_backup_procedure(vehicle_dir, f"Modified using the {self.get_menu_name()}.")

        # Save (and make sure the path exists)
        os.makedirs(os.path.dirname(self.vehicle_selector.brv_file), exist_ok=True)
        try:
            # Get the BRV with modified bricks
            brv = self.vehicle_selector.brv
            for brick_widget in self.bricks_widget.brick_widgets:
                brv.bricks[brick_widget.idx] = brick_widget.get_modified_brick()
            # Serialize and save
            serialized = brv.serialize()
            with open(self.vehicle_selector.brv_file, "wb") as f:
                f.write(serialized)

        # Message box in case of bugs
        except PermissionError as e:
            QMessageBox.critical(self, "Failed to save changes",
                f"BrickEdit-Interface was denied permission to save changes: {str(e)}"
            )
        except OSError as e:
            QMessageBox.critical(self, "Failed to save changes",
                f"BrickEdit-Interface could not save changes: {str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Failed to save changes",
                f"BrickEdit failed to save changes (most likely failed to serialize). Please report the following errors to the developers:\n\n{type(e).__name__}: {str(e)}"
            )
            raise e

        QMessageBox.information(self, "BrickEdit-Interface", "Successfully saved changes.")
