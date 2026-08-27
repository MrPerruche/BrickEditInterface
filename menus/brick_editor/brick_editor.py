from PySide6.QtGui import QIcon

from menus import base

from ui.dialogs import VehicleLoadingIssueDialog
from ui.widgets import Button
from ui.components import BrickSelector, VehicleBricksEditor

from brickedit import *

import logging
logger = logging.getLogger(__name__)



class EditBrickMenu(base.BaseMenu):
    """Menu for editing brick properties."""

    def __init__(self, mw):
        super().__init__(mw)

        # self.color_selector = ColorWidget(lambda: self.vehicle_selector.brv)
        # self.master_layout.addWidget(self.color_selector)

        # self.bricks_widget = BrickListWidget([])
        # self.master_layout.addWidget(self.bricks_widget)

        self.brick_selector = BrickSelector(mw)
        self.master_layout.addWidget(self.brick_selector)

        self.vbe = VehicleBricksEditor(mw, self.brick_selector)
        self.master_layout.addWidget(self.vbe)

        self.save_button = Button("Save changes")
        self.save_button.clicked.connect(self.save_changes)
        self.master_layout.addWidget(self.save_button)

        self.master_layout.addStretch()

    def get_menu_name(self) -> str:
        return "Brick Editor"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/BrickEditorIcon.png"), True)

    def save_changes(self):
        if not self.main_window.vehicle_selector_banner.is_vehicle_loaded():
            VehicleLoadingIssueDialog.create(self.mw, True).exec()
            return
        logger.info("Saving changes in Brick Editor...")
        self.vbe.build_modified_brvfile(True, {'description': f"Modified using the {self.get_menu_name()}."})
        logger.info("Saving changes in Brick Editor complete")

    # def on_brv_reload(self):
    #     brv = self.vehicle_selector.brv
    #     if brv is None:
    #         self.bricks_widget.update_bricks_widgets([])
    #         return

    #     matching_bricks = [(i, b) for i, b in enumerate(brv.bricks) if b.get_property(p.BRICK_COLOR) == self.color_selector.color]
    #     self.bricks_widget.update_bricks_widgets(matching_bricks)

    # def save_changes(self):
    #     # Create backup
    #     if self.vehicle_selector.brv_file is None:
    #         QMessageBox.warning(self, "No vehicle selected", "No vehicle selected. Please select a vehicle before saving changes.")
    #         return
    #     vehicle_dir = path.dirname(self.vehicle_selector.brv_file)
    #     self.main_window.backups.full_backup_procedure(vehicle_dir, f"Modified using the {self.get_menu_name()}.")

    #     # Save (and make sure the path exists)
    #     makedirs(path.dirname(self.vehicle_selector.brv_file), exist_ok=True)

    #     # Get the BRV with modified bricks
    #     brv = self.vehicle_selector.brv
    #     changes = self.bricks_widget.get_modified_bricks()
    #     for i, changed in changes:
    #         brv.bricks[i] = changed

    #     # Serialize and save
    #     serialized = try_serialize(brv)
    #     if serialized is None:
    #         return
    #     with open(self.vehicle_selector.brv_file, "wb") as f:
    #         f.write(serialized)

    #     QMessageBox.information(self, "BrickEdit-Interface", "Successfully saved changes.")
