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

        # math brick handling
        self.operation_handling_options: tuple[str] = (
            "Keep operation",
            "Keep operation and recolor"
            )
        self.operation_handling_options_descriptions: tuple[str] = (
            "Closest equivalent to the 1.11 operation",
            "Lets you easily find the affected math brick(s)"
        )

        # greater operation handling
        self.greater_handling_label = StyledLabel("GREATER HANDLING", style=LabelStyle.SUBTEXT_1)
        self.downgrade_preferences_layout.addWidget(self.greater_handling_label)
        self.greater_handling_label.hide()

        self.greater_handling = ComboBox()
        self.downgrade_preferences_layout.addWidget(self.greater_handling)
        self.greater_handling.hide()
        for option in self.operation_handling_options:
            self.greater_handling.add_item(option)
        self.greater_handling.item_changed.connect(self.update_downgrade_preferences)

        self.greater_handling_color = ColorPropertyWidget(f"Recolor {p.Operation.GT} math bricks to", (0, 0, 0, 0,), False, 0xbcbcbcff)
        self.downgrade_preferences_layout.addWidget(self.greater_handling_color)
        self.greater_handling_color.hide()

        self.greater_handling.set_tooltip(TooltipContents(f'{p.Operation.GT} handling', f"""How '{p.Operation.GT}' math bricks get handled.
        The '{p.Operation.GT}' operation was tweaked in 1.11, which results in it not having a true equivalent operation in 1.10. You can use this option to set how the math brick(s) will get handled.
        <hr>
        {self.operation_handling_options[0]} - {self.operation_handling_options_descriptions[0]}
        {self.operation_handling_options[1]} - {self.operation_handling_options_descriptions[1]}
        """))

        # less operation handling
        self.less_handling_label = StyledLabel("LESS HANDLING", style=LabelStyle.SUBTEXT_1)
        self.downgrade_preferences_layout.addWidget(self.less_handling_label)
        self.less_handling_label.hide()

        self.less_handling = ComboBox()
        self.downgrade_preferences_layout.addWidget(self.less_handling)
        self.less_handling.hide()
        for option in self.operation_handling_options:
            self.less_handling.add_item(option)
        self.less_handling.item_changed.connect(self.update_downgrade_preferences)

        self.less_handling_color = ColorPropertyWidget(f"Recolor {p.Operation.LT} math bricks to", (0, 0, 0, 0,), False, 0xbcbcbcff)
        self.downgrade_preferences_layout.addWidget(self.less_handling_color)
        self.less_handling_color.hide()

        self.less_handling.set_tooltip(TooltipContents(f'{p.Operation.LT} handling', f"""How '{p.Operation.LT}' math bricks get handled.
        The '{p.Operation.LT}' operation was tweaked in 1.11, which results in it not having a true equivalent operation in 1.10. You can use this option to set how the math brick(s) will get handled.
        <hr>
        {self.operation_handling_options[0]} - {self.operation_handling_options_descriptions[0]}
        {self.operation_handling_options[1]} - {self.operation_handling_options_descriptions[1]}
        """))

        # scalable brick handling
        self.brick_handling_options: tuple[str] = ("Remove brick(s)", f"Replace with {bt.SCALABLE_BRICK.name()}", f"Replace with {bt.SCALABLE_BRICK.name()} and recolor")
        self.brick_handling_options_descriptions: tuple[str] = (
            "Removes the brick(s) with no additional handling",
            f"Replaces the brick(s) with a scalable cube ({bt.SCALABLE_BRICK.name()})",
            f"Replaces the brick(s) with a scalable cube ({bt.SCALABLE_BRICK.name()}) and recolors it to let you find the affected brick(s) easier"
            )

        # scalable square to circle handling
        self.sq_to_c_handling_label = StyledLabel("SCALABLE SQUARE TO CIRCLE HANDLING", style=LabelStyle.SUBTEXT_1)
        self.downgrade_preferences_layout.addWidget(self.sq_to_c_handling_label)
        self.sq_to_c_handling_label.hide()

        self.sq_to_c_handling = ComboBox()
        self.downgrade_preferences_layout.addWidget(self.sq_to_c_handling)
        self.sq_to_c_handling.hide()
        for option in self.brick_handling_options:
            self.sq_to_c_handling.add_item(option)
        self.sq_to_c_handling.item_changed.connect(self.update_downgrade_preferences)

        self.sq_to_c_handling_color = ColorPropertyWidget(f"Recolor {bt.SCALABLE_SQUARE_TO_CIRCLE.name()} bricks to", (0, 0, 0, 0,), False, 0xbcbcbcff)
        self.downgrade_preferences_layout.addWidget(self.sq_to_c_handling_color)
        self.sq_to_c_handling_color.hide()

        self.sq_to_c_handling.set_tooltip(TooltipContents(f'{bt.SCALABLE_SQUARE_TO_CIRCLE.name()} handling', f"""How '{bt.SCALABLE_SQUARE_TO_CIRCLE.name()}' bricks get handled.
        The '{bt.SCALABLE_SQUARE_TO_CIRCLE.name()} brick was added in 1.11, which results in it not having an equivalent brick in 1.10. You can use this option to set how the brick(s) will get handled.
        <hr>
        {self.brick_handling_options[0]} - {self.brick_handling_options_descriptions[0]}
        {self.brick_handling_options[1]} - {self.brick_handling_options_descriptions[1]}
        {self.brick_handling_options[2]} - {self.brick_handling_options_descriptions[2]}"""))

        # scalable square to quarter circle handling
        self.sq_to_qc_handling_label = StyledLabel("SCALABLE SQUARE TO QUARTER CIRCLE HANDLING", style=LabelStyle.SUBTEXT_1)
        self.downgrade_preferences_layout.addWidget(self.sq_to_qc_handling_label)
        self.sq_to_qc_handling_label.hide()

        self.sq_to_qc_handling = ComboBox()
        self.downgrade_preferences_layout.addWidget(self.sq_to_qc_handling)
        self.sq_to_qc_handling.hide()
        for option in self.brick_handling_options:
            self.sq_to_qc_handling.add_item(option)
        self.sq_to_qc_handling.item_changed.connect(self.update_downgrade_preferences)

        self.sq_to_qc_handling_color = ColorPropertyWidget(f"Recolor {bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()} bricks to", (0, 0, 0, 0,), False, 0xbcbcbcff)
        self.downgrade_preferences_layout.addWidget(self.sq_to_qc_handling_color)
        self.sq_to_qc_handling_color.hide()

        self.sq_to_qc_handling.set_tooltip(TooltipContents(f'{bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()} handling', f"""How '{bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()}' bricks get handled.
        The '{bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()} brick was added in 1.11, which results in it not having an equivalent brick in 1.10. You can use this option to set how the brick(s) will get handled.
        <hr>
        {self.brick_handling_options[0]} - {self.brick_handling_options_descriptions[0]}
        {self.brick_handling_options[1]} - {self.brick_handling_options_descriptions[1]}
        {self.brick_handling_options[2]} - {self.brick_handling_options_descriptions[2]}"""))

        self.master_layout.addStretch()



    @staticmethod
    def version_to_int(version: str) -> int | None:
        return 18 if version == "1.11" else 17 if version == "1.10" else None

    @staticmethod
    def int_to_version(v: int) -> str | None:
        return "1.11" if v == 18 else "1.10" if v == 17 else None

    def get_versions(self) -> tuple[int, int]:
        """Returns the current version and the version to downgrade to as a tuple of ints"""
        return (
            self.version_to_int(self.current_version.get_current_text()),
            self.version_to_int(self.to_version.get_current_text())
            )

    def get_versions_str(self) -> tuple[int, int]:
        """Returns the current version and the version to downgrade to as a tuple of strings"""
        return (
            self.current_version.get_current_text(),
            self.to_version.get_current_text()
            )

    def get_menu_name(self) -> str:
        return "Vehicle Downgrader"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/ArrowLeftSmallIcon.png"), True)

    def update_can_downgrade(self):
        self.downgrade_button.set_disabled(
            self.get_versions_str()[0] == '---' or
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
        self.greater_handling_label.hide()
        self.greater_handling.hide()
        self.greater_handling_color.hide()

        self.less_handling_label.hide()
        self.less_handling.hide()
        self.less_handling_color.hide()

        self.sq_to_c_handling_label.hide()
        self.sq_to_c_handling.hide()
        self.sq_to_c_handling_color.hide()

        self.sq_to_qc_handling_label.hide()
        self.sq_to_qc_handling.hide()
        self.sq_to_qc_handling_color.hide()

        has_greater: bool = False
        has_less: bool = False
        has_sq_to_c_brick: bool = False
        has_sq_to_qc_brick: bool = False

        if self.get_versions()[0] > self.get_versions()[1]:
            if self.get_versions()[1] < 18:
                brvf = self.main_window.vehicle_selector_banner.get_brvfile_copy()
                if brvf is None:
                    VehicleLoadingIssueDialog.create(True).exec()
                    return
                for brick in brvf.bricks:
                    if brick.meta().name() == bt.MATH_BRICK.name():
                        has_greater = True if brick.get_property(p.OPERATION) == p.Operation.GT else has_greater
                        has_less = True if brick.get_property(p.OPERATION) == p.Operation.LT else has_less 

                        self.greater_handling_label.setVisible(has_greater)
                        self.less_handling_label.setVisible(has_less)

                        self.greater_handling.setVisible(has_greater)
                        self.less_handling.setVisible(has_less)

                        self.greater_handling_color.setVisible(self.greater_handling.get_current_idx() == 1 and has_greater)
                        self.less_handling_color.setVisible(self.less_handling.get_current_idx() == 1 and has_less)

                    elif brick.meta().name() in (bt.SCALABLE_SQUARE_TO_CIRCLE.name(), bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()):
                        has_sq_to_c_brick = True if brick.meta().name() == bt.SCALABLE_SQUARE_TO_CIRCLE.name() else has_sq_to_c_brick
                        has_sq_to_qc_brick = True if brick.meta().name() == bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name() else has_sq_to_qc_brick

                        self.sq_to_c_handling_label.setVisible(has_sq_to_c_brick)
                        self.sq_to_qc_handling_label.setVisible(has_sq_to_qc_brick)
                        
                        self.sq_to_c_handling.setVisible(has_sq_to_c_brick)
                        self.sq_to_qc_handling.setVisible(has_sq_to_qc_brick)

                        self.sq_to_c_handling_color.setVisible(self.sq_to_c_handling.get_current_idx() == 2 and has_sq_to_c_brick)
                        self.sq_to_qc_handling_color.setVisible(self.sq_to_qc_handling.get_current_idx() == 2 and has_sq_to_qc_brick)
                        print(has_sq_to_c_brick)

        else: return


    
    def downgrade_vehicle(self):
        brvfile = self.main_window.vehicle_selector_banner.get_brvfile_copy()  # Faster and respects user intentionally not reloading the vehicle
        if brvfile is None:
            VehicleLoadingIssueDialog.create(True).exec()
            return
        brvfile.version = self.get_versions()[1]

        if self.get_versions_str()[1] == self.supported_versions[1] and self.get_versions_str()[0] == self.supported_versions[0]:
            for i, brick in enumerate(brvfile.bricks):
                if brick.meta().name() == bt.MATH_BRICK.name():
                    if brick.get_property(p.OPERATION) == p.Operation.GT or brick.get_property(p.OPERATION) == p.Operation.LT and self.greater_handling.get_current_idx() == 1:
                        brick.set_property(p.BRICK_COLOR, self.greater_handling_color.get_value(0xbcbcbcff) if brick.get_property(p.OPERATION) == p.Operation.GT else self.less_handling_color.get_value(0xbcbcbcff))
                    elif brick.get_property(p.OPERATION) == p.Operation.GE or brick.get_property(p.OPERATION) == p.Operation.LE:
                        brick.set_property(p.OPERATION, p.Operation.LT if brick.get_property(p.OPERATION) == p.Operation.LE else p.Operation.GT)
                elif brick.meta().name() in (bt.SCALABLE_SQUARE_TO_CIRCLE.name(), bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()):
                    if self.sq_to_c_handling.get_current_idx() in (1, 2):
                        new_meta = bt.SCALABLE_BRICK
                        new_brick = Brick(
                            ref=brick.ref,
                            meta=new_meta,
                            pos=brick.pos,
                            rot=brick.rot,
                            ppatch=brick.ppatch
                        )
                        brvfile.add(new_brick)
                        if self.sq_to_c_handling.get_current_idx() == 2:
                            new_brick.set_property(p.BRICK_COLOR, self.sq_to_c_handling_color.get_value(0xbcbcbcff))
                    brvfile.bricks.pop(i)
        
        logger.info(f"Downgrading vehicle from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")
        self.main_window.vehicle_selector_banner.save_brv(brvfile, description=f"Downgraded using the {self.get_menu_name()} from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}.")
        logger.info(f"Vehicle downgraded from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")