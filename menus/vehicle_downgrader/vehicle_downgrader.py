from PySide6.QtWidgets import QComboBox
from PySide6.QtGui import QIcon

from menus import base

from ui.widgets import Button, StyledLabel, LabelStyle
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

        self.current_version = QComboBox()
        self.master_layout.addWidget(self.current_version)
        self.current_version.setDisabled(True)
        self.current_version.addItem('---')

        self.to_version_label = StyledLabel("DOWNGRADE TO VERSION", style=LabelStyle.SUBTEXT_1)
        self.master_layout.addWidget(self.to_version_label)

        self.to_version = QComboBox()
        self.master_layout.addWidget(self.to_version)
        self.to_version.addItems(self.supported_versions)
        self.to_version.currentIndexChanged.connect(self.update_can_downgrade)

        self.downgrade_button = Button("Downgrade vehicle")
        self.downgrade_button.clicked.connect(self.downgrade_vehicle)
        self.downgrade_button.setEnabled(False)
        self.master_layout.addWidget(self.downgrade_button)

        self.disabled_if_vehicle_not_loaded = [self.downgrade_button]

        self.main_window.vehicle_selector_banner.vehicle_loaded.connect(self.on_reload)

        self.master_layout.addStretch()



    @staticmethod
    def version_to_int(version: str):
        return 18 if version == "1.11" else 17 if version == "1.10" else 16 if version == "1.9" else None

    @staticmethod
    def int_to_version(v: int):
        return "1.11" if v == 18 else "1.10" if v == 17 else "1.9" if v == 16 else None

    def get_menu_name(self) -> str:
        return "Vehicle Downgrader"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/ArrowLeftSmallIcon.png"), True)

    def update_can_downgrade(self):
        self.downgrade_button.setDisabled(self.current_version.currentText() == '---' or self.current_version.currentText() == self.to_version.currentText())
        if self.main_window.vehicle_selector_banner.get_brvfile_ref() is None:
            self.downgrade_button.setDisabled(True)
            self.current_version.setItemText(0, '---')

    def unload_vehicle(self):
        self.current_version.setItemText(0, '---')
        self.update_can_downgrade()
        
    
    def on_reload(self):
        for widget in self.disabled_if_vehicle_not_loaded:
            widget.setDisabled(True if self.main_window.vehicle_selector_banner.get_brvfile_ref() is None else False)
        if self.main_window.vehicle_selector_banner.get_brvfile_ref() is not None:
            version = self.main_window.vehicle_selector_banner.get_brvfile_ref().version
            self.current_version.setItemText(0, self.int_to_version(version))
        self.update_can_downgrade()
    
    def downgrade_vehicle(self):
        brvfile = self.main_window.vehicle_selector_banner.get_brvfile_copy()  # Faster and respects user intentionally not reloading the vehicle
        if brvfile is None:
            VehicleLoadingIssueDialog.create(True).exec()  # nothing to do with exec(...) which is unsafe
            return
        brvfile.version = self.version_to_int(self.to_version.currentText())
        for brick in brvfile.bricks:
            print(brick)