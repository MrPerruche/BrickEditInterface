from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtGui import QIcon

from menus import base

from ui.widgets import Button, ComboBox, StyledLabel, LabelStyle
from ui.components.brick.property_widgets import ColorPropertyWidget
from ui.dialogs import VehicleLoadingIssueDialog
from ui.models import TooltipContents


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
        self.to_version.item_changed.connect(self.update_downgrade_preferences)

        self.downgrade_preferences_layout = QVBoxLayout()
        self.master_layout.addLayout(self.downgrade_preferences_layout)

        self.downgrade_button = Button("Downgrade vehicle")
        self.downgrade_button.clicked.connect(self.downgrade_vehicle)
        self.downgrade_button.set_enabled(False)
        self.master_layout.addWidget(self.downgrade_button)

        self.disabled_if_vehicle_not_loaded = [self.downgrade_button]

        self.main_window.vehicle_selector_banner.vehicle_loaded.connect(self.on_reloaded)


        # greater operation handling
        self.greater_handling_label = StyledLabel("GREATER HANDLING", style=LabelStyle.SUBTEXT_1)
        self.downgrade_preferences_layout.addWidget(self.greater_handling_label)
        self.greater_handling_label.setVisible(False)

        self.greater_handling = ComboBox()
        self.downgrade_preferences_layout.addWidget(self.greater_handling)
        self.greater_handling.setVisible(False)
        self.greater_handling.item_changed.connect(self.update_downgrade_preferences)

        self.greater_handling_color = ColorPropertyWidget("Set to color", (0, 0, 0, 0,), False, 0xbcbcbcff)
        self.downgrade_preferences_layout.addWidget(self.greater_handling_color)
        self.greater_handling_color.hide()

        self.greater_options = ("Keep operation (Recommended)", "Keep operation and change color")
        for option in self.greater_options:
            self.greater_handling.add_item(option)
        self.greater_handling.set_tooltip(TooltipContents(text='Greater handling', description="""How 'Greater' math bricks get handled.
        The 'Greater' operation was tweaked in 1.11, which results in it not having a true equal operation in 1.10. You can use this option to set how the math brick will get handled
        <hr>
        Keep operation - Closest equivalent to the 1.11 operation
        Keep operation and change color - Lets you easily find the affected math bricks
        """))

        self.master_layout.addStretch()



    @staticmethod
    def version_to_int(version: str):
        return 18 if version == "1.11" else 17 if version == "1.10" else None

    @staticmethod
    def int_to_version(v: int):
        return "1.11" if v == 18 else "1.10" if v == 17 else None

    def get_versions(self) -> tuple[int, int]:
        """Returns the current version and the version to downgrade to as a tuple of ints"""
        return (self.version_to_int(self.current_version.get_current_text()) if self.current_version.get_current_text() != "---" else 0,
        self.version_to_int(self.to_version.get_current_text()))

    def get_versions_str(self) -> tuple[int, int]:
        """Returns the current version and the version to downgrade to as a tuple of strings"""
        return (self.current_version.get_current_text(), self.to_version.get_current_text())

    def get_menu_name(self) -> str:
        return "Vehicle Downgrader"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/ArrowLeftSmallIcon.png"), True)

    def update_can_downgrade(self):
        self.downgrade_button.set_disabled(
            self.get_versions()[0] == '---' or
            self.get_versions()[0] <= self.get_versions()[1]
            )
        if self.main_window.vehicle_selector_banner.get_brvfile_ref() is None:
            self.downgrade_button.set_enabled(False)
            self.current_version.set_current_text(0, '---')
    
    def on_reloaded(self):
        for widget in self.disabled_if_vehicle_not_loaded:
            widget.set_enabled(self.main_window.vehicle_selector_banner.get_brvfile_ref() is not None)
        if self.main_window.vehicle_selector_banner.get_brvfile_ref() is not None:
            version = self.main_window.vehicle_selector_banner.get_brvfile_ref().version
            self.current_version.set_current_text(0, self.int_to_version(version))
        self.update_can_downgrade()
        self.update_downgrade_preferences()

    def update_downgrade_preferences(self):
        if self.get_versions()[0] > self.get_versions()[1]:
            if self.get_versions()[1] < 18:
                brvf = self.main_window.vehicle_selector_banner.get_brvfile_copy()
                if brvf is None:
                    VehicleLoadingIssueDialog.create(True).exec()
                    return
                for brick in brvf.bricks:
                    if brick.meta().name() == bt.MATH_BRICK.name():
                            self.greater_handling_label.setVisible(brick.get_property(p.OPERATION) == p.Operation.GT)
                            self.greater_handling.setVisible(brick.get_property(p.OPERATION) == p.Operation.GT)
                            self.greater_handling_color.setVisible(self.greater_handling.get_current_idx() == 1 and
                            brick.get_property(p.OPERATION) == p.Operation.GT)
                            if self.greater_handling.get_current_idx() == 1:
                                self.greater_handling_color.setVisible(brick.get_property(p.OPERATION) == p.Operation.GT)
                            else:
                                self.greater_handling_color.hide()
        else:
            self.greater_handling_label.hide()
            self.greater_handling.hide()
            self.greater_handling_color.hide()


    
    def downgrade_vehicle(self):
        self.update_downgrade_preferences()
        brvfile = self.main_window.vehicle_selector_banner.get_brvfile_copy()  # Faster and respects user intentionally not reloading the vehicle
        if brvfile is None:
            VehicleLoadingIssueDialog.create(True).exec()
            return
        brvfile.version = self.get_versions()[1]

        if self.get_versions_str()[1] == self.supported_versions[1] and self.get_versions_str()[0] == self.supported_versions[0]:
            for brick in brvfile.bricks:
                if brick.meta().name() == bt.MATH_BRICK.name():
                    if brick.get_property(p.OPERATION) == p.Operation.GT and self.greater_handling.get_current_idx() == 1:
                        brick.set_property(p.BRICK_COLOR, self.greater_handling_color.get_value(0xbcbcbcff))
                    if brick.get_property(p.OPERATION) == p.Operation.GE:
                        brick.set_property(p.OPERATION, p.Operation.GT)
        
        logger.info(f"Downgrading vehicle from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")
        self.main_window.vehicle_selector_banner.save_brv(brvfile, description=f"Downgraded using the {self.get_menu_name()} from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}.")
        logger.info(f"Vehicle downgraded from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")