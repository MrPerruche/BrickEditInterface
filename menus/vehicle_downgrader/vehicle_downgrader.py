from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtGui import QIcon

from menus import base

from ui.widgets import Button, ComboBox, Label, StyledLabel, LabelStyle, Surface, Switcher
from ui.components.brick.property_widgets import ColorPropertyWidget
from ui.dialogs import VehicleLoadingIssueDialog
from ui.models import TooltipContents


from brickedit import *

import logging
logger = logging.getLogger(__name__)



_SUPPORTED_VERSIONS = ["1.10", "1.11"]

_ABOUT_OPERATION_HANDLING = """Keep operation - Closest equivalent to the 1.11 operation
        Keep operation and recolor - Lets you easily find the affected math brick(s)"""

_ABOUT_BRICK_HANDLING = f"""Remove brick(s) - Removes the brick(s)
        Replace with {bt.SCALABLE_BRICK.name()} - Replaces the brick(s) with a scalable cube ({bt.SCALABLE_BRICK.name()})
        Replace with {bt.SCALABLE_BRICK.name()} and recolor - Replaces the brick(s) with a scalable cube ({bt.SCALABLE_BRICK.name()}) and recolors it to let you find the affected brick(s) easier"""

_OPERATION_HANDLING_OPTIONS = ("Keep operation", "Keep operation and recolor")

_BRICK_HANDLING_OPTIONS = ("Remove brick(s)", f"Replace with {bt.SCALABLE_BRICK.name()}", f"Replace with {bt.SCALABLE_BRICK.name()} and recolor")


class DowngradeVehicleMenu(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw

        # downgrade from
        self.current_version_label = Label("Current version")
        self.master_layout.addWidget(self.current_version_label)

        self.current_version_setting = Switcher(["---"])
        self.master_layout.addWidget(self.current_version_setting)

        # downgrade to
        self.to_version_label = Label("Downgrade to version")
        self.master_layout.addWidget(self.to_version_label)

        self.to_version_setting = Switcher(_SUPPORTED_VERSIONS)
        self.master_layout.addWidget(self.to_version_setting)
        self.to_version_setting.left_arrow.clicked.connect(self.update_can_downgrade)
        self.to_version_setting.right_arrow.clicked.connect(self.update_can_downgrade)

        # OPERATION HANDLING UI
        self.operation_handling_layout = QVBoxLayout()
        self.master_layout.addLayout(self.operation_handling_layout)

        self.operation_handling_title = StyledLabel("Operation handling", LabelStyle.LARGE_5)
        self.operation_handling_layout.addWidget(self.operation_handling_title)
        self.operation_handling_title.hide()

        # greater operation handling
        self.greater_handling_widget = Surface()
        self.greater_handling_layout = self.greater_handling_widget.layout()
        self.greater_handling_title = StyledLabel(f"{p.Operation.GT} handling", LabelStyle.LARGE_5)
        self.greater_handling_layout.addWidget(self.greater_handling_title)
        self.operation_handling_layout.addWidget(self.greater_handling_widget)
        self.greater_handling_widget.hide()

        self.greater_handling_label = Label("Handling mode")
        self.greater_handling_label.set_tooltip(TooltipContents("Handling mode", _ABOUT_OPERATION_HANDLING))
        self.greater_handling_setting = ComboBox()
        for option in _OPERATION_HANDLING_OPTIONS:
            self.greater_handling_setting.add_item(option)
        self.greater_handling_color_label = Label("Recolor to")
        self.greater_handling_color = ColorPropertyWidget('', (0,), False, 0xbcbcbcff, show_text=False)
        self.greater_handling_layout.addWidget(self.greater_handling_label)
        self.greater_handling_label.hide()
        self.greater_handling_layout.addWidget(self.greater_handling_setting)
        self.greater_handling_setting.hide()
        self.greater_handling_layout.addWidget(self.greater_handling_color_label)
        self.greater_handling_color_label.hide()
        self.greater_handling_layout.addWidget(self.greater_handling_color)
        self.greater_handling_color.hide()
        self.greater_handling_setting.item_changed.connect(self.update_downgrade_preferences)

        # less operation handling
        self.less_handling_widget = Surface()
        self.less_handling_layout = self.less_handling_widget.layout()
        self.less_handling_title = StyledLabel(f"{p.Operation.LT} handling", LabelStyle.LARGE_5)
        self.less_handling_layout.addWidget(self.less_handling_title)
        self.operation_handling_layout.addWidget(self.less_handling_widget)
        self.less_handling_widget.hide()

        self.less_handling_label = Label("Handling mode")
        self.less_handling_label.set_tooltip(TooltipContents("Handling mode", _ABOUT_OPERATION_HANDLING))
        self.less_handling_setting = ComboBox()
        for option in _OPERATION_HANDLING_OPTIONS:
            self.less_handling_setting.add_item(option)
        self.less_handling_color_label = Label("Recolor to")
        self.less_handling_color = ColorPropertyWidget('', (0,), False, 0xbcbcbcff, show_text=False)
        self.less_handling_layout.addWidget(self.less_handling_label)
        self.less_handling_label.hide()
        self.less_handling_layout.addWidget(self.less_handling_setting)
        self.less_handling_setting.hide()
        self.less_handling_layout.addWidget(self.less_handling_color_label)
        self.less_handling_color_label.hide()
        self.less_handling_layout.addWidget(self.less_handling_color)
        self.less_handling_color.hide()
        self.less_handling_setting.item_changed.connect(self.update_downgrade_preferences)

        # BRICK HANDLING UI
        self.brick_handling_layout = QVBoxLayout()
        self.master_layout.addLayout(self.brick_handling_layout)

        self.brick_handling_title = StyledLabel("Brick handling", LabelStyle.LARGE_5)
        self.brick_handling_layout.addWidget(self.brick_handling_title)
        self.brick_handling_title.hide()

        # scalable square to circle handling
        self.sq_to_c_handling_widget = Surface()
        self.sq_to_c_handling_layout = self.sq_to_c_handling_widget.layout()
        self.sq_to_c_handling_title = StyledLabel(f"{bt.SCALABLE_SQUARE_TO_CIRCLE.name()} handling", LabelStyle.LARGE_5)
        self.sq_to_c_handling_layout.addWidget(self.sq_to_c_handling_title)
        self.brick_handling_layout.addWidget(self.sq_to_c_handling_widget)
        self.sq_to_c_handling_widget.hide()

        self.sq_to_c_handling_label = Label("Handling mode")
        self.sq_to_c_handling_label.set_tooltip(TooltipContents("Handling mode", _ABOUT_OPERATION_HANDLING))
        self.sq_to_c_handling_setting = ComboBox()
        for option in _BRICK_HANDLING_OPTIONS:
            self.sq_to_c_handling_setting.add_item(option)
        self.sq_to_c_handling_color_label = Label("Recolor to")
        self.sq_to_c_handling_color = ColorPropertyWidget('', (0,), False, 0xbcbcbcff, show_text=False)
        self.sq_to_c_handling_layout.addWidget(self.sq_to_c_handling_label)
        self.sq_to_c_handling_label.hide()
        self.sq_to_c_handling_layout.addWidget(self.sq_to_c_handling_setting)
        self.sq_to_c_handling_setting.hide()
        self.sq_to_c_handling_layout.addWidget(self.sq_to_c_handling_color_label)
        self.sq_to_c_handling_color_label.hide()
        self.sq_to_c_handling_layout.addWidget(self.sq_to_c_handling_color)
        self.sq_to_c_handling_color.hide()
        self.sq_to_c_handling_setting.item_changed.connect(self.update_downgrade_preferences)

        # scalable square to quarter circle handling
        self.sq_to_qc_handling_widget = Surface()
        self.sq_to_qc_handling_layout = self.sq_to_qc_handling_widget.layout()
        self.sq_to_qc_handling_title = StyledLabel(f"{bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()} handling", LabelStyle.LARGE_5)
        self.sq_to_qc_handling_layout.addWidget(self.sq_to_qc_handling_title)
        self.brick_handling_layout.addWidget(self.sq_to_qc_handling_widget)
        self.sq_to_qc_handling_widget.hide()

        self.sq_to_qc_handling_label = Label("Handling mode")
        self.sq_to_qc_handling_label.set_tooltip(TooltipContents("Handling mode", _ABOUT_OPERATION_HANDLING))
        self.sq_to_qc_handling_setting = ComboBox()
        for option in _BRICK_HANDLING_OPTIONS:
            self.sq_to_qc_handling_setting.add_item(option)
        self.sq_to_qc_handling_color_label = Label("Recolor to")
        self.sq_to_qc_handling_color = ColorPropertyWidget('', (0,), False, 0xbcbcbcff, show_text=False)
        self.sq_to_qc_handling_layout.addWidget(self.sq_to_qc_handling_label)
        self.sq_to_qc_handling_label.hide()
        self.sq_to_qc_handling_layout.addWidget(self.sq_to_qc_handling_setting)
        self.sq_to_qc_handling_setting.hide()
        self.sq_to_qc_handling_layout.addWidget(self.sq_to_qc_handling_color_label)
        self.sq_to_qc_handling_color_label.hide()
        self.sq_to_qc_handling_layout.addWidget(self.sq_to_qc_handling_color)
        self.sq_to_qc_handling_color.hide()
        self.sq_to_qc_handling_setting.item_changed.connect(self.update_downgrade_preferences)

        self.downgrade_vehicle_button = Button("Downgrade vehicle")
        self.master_layout.addWidget(self.downgrade_vehicle_button)
        self.downgrade_vehicle_button.set_disabled(True)
        self.downgrade_vehicle_button.clicked.connect(self.downgrade_vehicle)

        mw.vehicle_selector_banner.vehicle_loaded.connect(self.on_reloaded)
        self.master_layout.addStretch()



    @staticmethod
    def version_to_int(version: str) -> int | None:
        return 18 if version == "1.11" else 17 if version == "1.10" else 0

    @staticmethod
    def int_to_version(v: int) -> str | None:
        return "1.11" if v == 18 else "1.10" if v == 17 else "---"

    def get_versions(self) -> tuple[int, int]:
        """Returns the current version and the version to downgrade to as a tuple of ints"""
        return (
            self.version_to_int(self.current_version_setting.get_text()),
            self.version_to_int(self.to_version_setting.get_text())
            )

    def get_versions_str(self) -> tuple[int, int]:
        """Returns the current version and the version to downgrade to as a tuple of strings"""
        return (
            self.current_version_setting.get_text(),
            self.to_version_setting.get_text()
            )

    def get_menu_name(self) -> str:
        return "Vehicle Downgrader"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/DowngradeIcon.png"), True)

    def update_can_downgrade(self):
        self.downgrade_vehicle_button.set_enabled(self.version_to_int(self.current_version_setting.get_text()) >
        self.version_to_int(self.to_version_setting.get_text()) if self.current_version_setting.get_text() != '---' else False)
    
    def on_reloaded(self):
        version = None
        if self.mw.vehicle_selector_banner.get_brvfile_ref() is not None:
            version = self.mw.vehicle_selector_banner.get_brvfile_ref().version
        self.current_version_setting.set_items([self.int_to_version(version)])
        self.update_downgrade_preferences()
        self.update_can_downgrade()

    def update_downgrade_preferences(self):
        widgets_to_hide = [
            self.greater_handling_setting, self.greater_handling_label, self.greater_handling_widget, self.greater_handling_color, self.greater_handling_color_label,
            self.less_handling_setting, self.less_handling_label, self.less_handling_widget, self.less_handling_color, self.less_handling_color_label,
            self.sq_to_c_handling_setting, self.sq_to_c_handling_label, self.sq_to_c_handling_widget, self.sq_to_c_handling_color, self.sq_to_c_handling_color_label,
            self.sq_to_qc_handling_setting, self.sq_to_qc_handling_label, self.sq_to_qc_handling_widget, self.sq_to_qc_handling_color, self.sq_to_qc_handling_color_label,
            self.operation_handling_title, self.brick_handling_title
        ]

        for widget in widgets_to_hide:
            widget.hide()

        has_greater_operation: bool = False
        has_less_operation: bool = False
        has_sq_to_c_brick: bool = False
        has_sq_to_qc_brick: bool = False

        if self.get_versions()[0] > self.get_versions()[1]:
            if self.get_versions()[1] < 18:
                brvf = self.mw.vehicle_selector_banner.get_brvfile_copy()
                if brvf is None: return
                for brick in brvf.bricks:
                    if brick.meta().name() == bt.MATH_BRICK.name():
                        has_greater_operation = True if brick.get_property(p.OPERATION) == p.Operation.GT else has_greater_operation
                        has_less_operation = True if brick.get_property(p.OPERATION) == p.Operation.LT else has_less_operation

                    has_sq_to_c_brick = True if brick.meta().name() == bt.SCALABLE_SQUARE_TO_CIRCLE.name() else has_sq_to_c_brick
                    has_sq_to_qc_brick = True if brick.meta().name() == bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name() else has_sq_to_qc_brick

                self.operation_handling_title.setVisible(has_greater_operation or has_less_operation)

                self.greater_handling_widget.setVisible(has_greater_operation)
                self.greater_handling_label.setVisible(has_greater_operation)
                self.greater_handling_setting.setVisible(has_greater_operation)
                self.greater_handling_color_label.setVisible(has_greater_operation and self.greater_handling_setting.get_current_idx() == 1)
                self.greater_handling_color.setVisible(has_greater_operation and self.greater_handling_setting.get_current_idx() == 1)

                self.less_handling_widget.setVisible(has_less_operation)
                self.less_handling_label.setVisible(has_less_operation)
                self.less_handling_setting.setVisible(has_less_operation)
                self.less_handling_color_label.setVisible(has_less_operation and self.less_handling_setting.get_current_idx() == 1)
                self.less_handling_color.setVisible(has_less_operation and self.less_handling_setting.get_current_idx() == 1)

                self.brick_handling_title.setVisible(has_sq_to_c_brick or has_sq_to_qc_brick)

                self.sq_to_c_handling_widget.setVisible(has_sq_to_c_brick)
                self.sq_to_c_handling_label.setVisible(has_sq_to_c_brick)
                self.sq_to_c_handling_setting.setVisible(has_sq_to_c_brick)
                self.sq_to_c_handling_color_label.setVisible(has_sq_to_c_brick and self.sq_to_c_handling_setting.get_current_idx() == 2)
                self.sq_to_c_handling_color.setVisible(has_sq_to_c_brick  and self.sq_to_c_handling_setting.get_current_idx() == 2)

                self.sq_to_qc_handling_widget.setVisible(has_sq_to_qc_brick)
                self.sq_to_qc_handling_label.setVisible(has_sq_to_qc_brick)
                self.sq_to_qc_handling_setting.setVisible(has_sq_to_qc_brick)
                self.sq_to_qc_handling_color_label.setVisible(has_sq_to_qc_brick and self.sq_to_qc_handling_setting.get_current_idx() == 2)
                self.sq_to_qc_handling_color.setVisible(has_sq_to_qc_brick and self.sq_to_qc_handling_setting.get_current_idx() == 2)
                        

        else: return


    
    def downgrade_vehicle(self):
        brvfile = self.mw.vehicle_selector_banner.get_brvfile_copy()  # Faster and respects user intentionally not reloading the vehicle
        if brvfile is None:
            VehicleLoadingIssueDialog.create(True).exec(); return
        brvfile.version = self.get_versions()[1]

        if self.get_versions_str()[0] == _SUPPORTED_VERSIONS[1] and self.get_versions_str()[1] == _SUPPORTED_VERSIONS[0]:
            for i, brick in enumerate(brvfile.bricks[:]):
                if brick.meta().name() == bt.MATH_BRICK.name():
                    if brick.get_property(p.OPERATION) == p.Operation.GT and self.greater_handling_setting.get_current_idx() == 1:
                        brick.set_property(
                            p.BRICK_COLOR,
                            self.greater_handling_color.get_value(0xbcbcbcff)
                            )
                    elif brick.get_property(p.OPERATION) == p.Operation.LT and self.less_handling_setting.get_current_idx() == 1:
                        brick.set_property(
                            p.BRICK_COLOR,
                            self.less_handling_color.get_value(0xbcbcbcff)
                            )
                    elif brick.get_property(p.OPERATION) in (p.Operation.GE, p.Operation.LE):
                        brick.set_property(p.OPERATION, p.Operation.LT if brick.get_property(p.OPERATION) == p.Operation.LE else p.Operation.GT)
                elif brick.meta().name() in (bt.SCALABLE_SQUARE_TO_CIRCLE.name(), bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()):
                    if self.sq_to_c_handling_setting.get_current_idx() in (1, 2):
                        new_meta = bt.SCALABLE_BRICK
                        new_brick = Brick(
                            ref=brick.ref,
                            meta=new_meta,
                            pos=brick.pos,
                            rot=brick.rot,
                            ppatch=brick.ppatch
                        )
                        brvfile.add(new_brick)
                        if self.sq_to_c_handling_setting.get_current_idx() == 2 and brick.meta().name() == bt.SCALABLE_SQUARE_TO_CIRCLE.name():
                            new_brick.set_property(p.BRICK_COLOR,
                            self.sq_to_c_handling_color.get_value(0xbcbcbcff))
                        elif self.sq_to_qc_handling_setting.get_current_idx() == 2 and brick.meta().name() == bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name():
                            new_brick.set_property(p.BRICK_COLOR,
                            self.sq_to_qc_handling_color.get_value(0xbcbcbcff))

                        brvfile.bricks.remove(brick)
        
        logger.info(f"Downgrading vehicle from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")
        self.mw.vehicle_selector_banner.save_brv(brvfile, description=f"Downgraded using the {self.get_menu_name()} from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}.")
        logger.info(f"Vehicle downgraded from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")
