from PySide6.QtGui import QIcon

from menus import base

from ui.widgets import Button, ComboBox, StyledLabel, LabelStyle
from ui.dialogs import VehicleLoadingIssueDialog

from brickedit import *

import logging
logger = logging.getLogger(__name__)



class DowngradeVehicleMenu(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)

        self.supported_versions = ("1.11", "1.10")

        self.current_version_label = StyledLabel("CURRENT VERSION", style=LabelStyle.SUBTEXT_1)
        self.master_layout.addWidget(self.current_version_label)

        self.current_version = ComboBox()
        self.master_layout.addWidget(self.current_version)
        self.current_version.setEnabled(False)
        self.current_version.add_item('---')

        self.to_version_label = StyledLabel("DOWNGRADE TO VERSION", style=LabelStyle.SUBTEXT_1)
        self.master_layout.addWidget(self.to_version_label)

        self.to_version = ComboBox()
        self.master_layout.addWidget(self.to_version)
        for version in self.supported_versions:
            self.to_version.add_item(version)
        self.to_version.item_changed.connect(self.update_can_downgrade)

        self.downgrade_button = Button("Downgrade vehicle")
        self.downgrade_button.clicked.connect(self.downgrade_vehicle)
        self.downgrade_button.set_enabled(False)
        self.master_layout.addWidget(self.downgrade_button)

        self.disabled_if_vehicle_not_loaded = [self.downgrade_button]

        self.main_window.vehicle_selector_banner.vehicle_loaded.connect(self.on_reload)

        self.master_layout.addStretch()



    @staticmethod
    def version_to_int(version: str):
        return 18 if version == "1.11" else 17 if version == "1.10" else None

    @staticmethod
    def int_to_version(v: int):
        return "1.11" if v == 18 else "1.10" if v == 17 else None

    def get_menu_name(self) -> str:
        return "Vehicle Downgrader"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/ArrowLeftSmallIcon.png"), True)

    def update_can_downgrade(self):
        self.downgrade_button.set_disabled(
            self.current_version.get_current_text() == '---' or
            self.version_to_int(self.current_version.get_current_text()) <= self.version_to_int(self.to_version.get_current_text())
            )
        if self.main_window.vehicle_selector_banner.get_brvfile_ref() is None:
            self.downgrade_button.set_enabled(False)
            self.current_version.set_current_text(0, '---')

    def unload_vehicle(self):
        self.current_version.set_current_text(0, '---')
        self.update_can_downgrade()
    
    def on_reload(self):
        for widget in self.disabled_if_vehicle_not_loaded:
            widget.set_enabled(self.main_window.vehicle_selector_banner.get_brvfile_ref() is not None)
        if self.main_window.vehicle_selector_banner.get_brvfile_ref() is not None:
            version = self.main_window.vehicle_selector_banner.get_brvfile_ref().version
            self.current_version.set_current_text(0, self.int_to_version(version))
        self.update_can_downgrade()

    def update_downgrade_preferences(self):
        pass
    
    def downgrade_vehicle(self):
        brvfile = self.main_window.vehicle_selector_banner.get_brvfile_copy()  # Faster and respects user intentionally not reloading the vehicle
        if brvfile is None:
            VehicleLoadingIssueDialog.create(True).exec()
            return
        brvfile.version = self.version_to_int(self.to_version.get_current_text())
        if self.to_version.get_current_text == self.supported_versions[1] and self.current_version.get_current_text == supported_versions[0]:
            for brick in brvfile.bricks:
                if bt.MATH_BRICK.name() == brick.meta().name():
                    if brick.get_property(p.OPERATION) == p.Operation.GREATER_EQUAL:
                        brick.set_property(p.OPERATION, p.Operation.GREATER)
        logger.info(f"Downgrading vehicle from {self.current_version.get_current_text()} to {self.to_version.get_current_text()}")
        self.main_window.vehicle_selector_banner.save_brv(brvfile, description=f"Downgraded using the {self.get_menu_name()} from {self.current_version.get_current_text} to {self.to_version.get_current_text()}.")
        logger.info(f"Vehicle downgraded from {self.current_version.get_current_text()} to {self.to_version.get_current_text()}")