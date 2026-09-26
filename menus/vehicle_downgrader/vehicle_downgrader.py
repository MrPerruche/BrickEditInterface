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

_1_11_OPERATIONS: tuple[str] = (
    p.Operation.DISTANCE,
    p.Operation.HYPOTENUSE,
    p.Operation.COPY_SIGN,
    p.Operation.ROOT,
    p.Operation.EXP,
    p.Operation.LN,
    p.Operation.LOG10,
    p.Operation.LOG_BASE,
    p.Operation.FRACTION,
    p.Operation.TRUNCATE,
    p.Operation.GREATER,
    p.Operation.LESS,
    p.Operation.APPROXIMATELY_EQUAL,
    p.Operation.AND,
    p.Operation.OR,
    p.Operation.XOR,
    p.Operation.NOT,
    p.Operation.SATURATE,
    p.Operation.CLAMP,
    p.Operation.SYMMETRIC_CLAMP,
    p.Operation.LERP,
    p.Operation.REMAP,
    p.Operation.DERIVATIVE,
    p.Operation.INTEGRAL,
    p.Operation.LOW_PASS,
    p.Operation.RATE_LIMIT,
    p.Operation.MIN_HOLD,
    p.Operation.MAX_HOLD,
    p.Operation.SAMPLE_AND_HOLD,
    p.Operation.PULSE
)

_1_11_BRICKS: tuple[str] = (
    bt.SCALABLE_SQUARE_TO_CIRCLE.name(),
    bt.SCALABLE_SQUARE_TO_QUARTER_CIRCLE.name()
)

_SUPPORTED_VERSIONS: tuple[str] = ("1.10", "1.11")

_BRICK_HANDLING_OPTIONS: tuple[str] = (
    f"Replace with {bt.SCALABLE_BRICK.name()}",
    f"Replace with {bt.SCALABLE_BRICK.name()} and recolor"
    )

_BRICK_HANDLING_OPTIONS_TOOLTIP = TooltipContents(
    "Brick handling options",
    f"""{_BRICK_HANDLING_OPTIONS[0]} - Replaces the brick(s) with a scalable cube
    {_BRICK_HANDLING_OPTIONS[0]} - Replaces the brick(s) with a scalable cube and recolors it to help you find it easier"""
    )

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

        self.to_version_setting = Switcher(list(_SUPPORTED_VERSIONS))
        self.master_layout.addWidget(self.to_version_setting)
        self.to_version_setting.left_arrow.clicked.connect(self.update_can_downgrade)
        self.to_version_setting.right_arrow.clicked.connect(self.update_can_downgrade)

        # OPERATION HANDLING UI
        self.operation_handling_surface = Surface()
        self.operation_handling_layout = self.operation_handling_surface.layout()
        self.master_layout.addWidget(self.operation_handling_surface)
        self.operation_handling_surface.hide()

        self.operation_handling_title = StyledLabel("Operations", LabelStyle.LARGE_5)
        self.operation_handling_layout.addWidget(self.operation_handling_title)
        #self.operation_handling_title.hide()

        self.operation_handling_recolor_label = Label("Recolor to")
        self.operation_handling_layout.addWidget(self.operation_handling_recolor_label)

        self.operation_handling_recolor = ColorPropertyWidget('',
        (0,), False, 0xbcbcbcff, True, False)
        self.operation_handling_layout.addWidget(self.operation_handling_recolor)

        self.operation_handling_recolor_label.set_tooltip(TooltipContents("Recolor to", "Recolors the math brick to a color to help you with replacing it"))
        self.operation_handling_recolor.set_tooltip(TooltipContents("Recolor to", "Recolors the math brick to a color to help you with replacing it"))

        # BRICK HANDLING UI
        self.brick_handling_surface = Surface()
        self.brick_handling_layout = self.brick_handling_surface.layout()
        self.master_layout.addWidget(self.brick_handling_surface)
        self.brick_handling_surface.hide()

        self.brick_handling_title = StyledLabel("Bricks", LabelStyle.LARGE_5)
        self.brick_handling_layout.addWidget(self.brick_handling_title)

        self.brick_handling_option_label = Label("Brick downgrade option")
        self.brick_handling_layout.addWidget(self.brick_handling_option_label)
        self.brick_handling_option_label.set_tooltip(_BRICK_HANDLING_OPTIONS_TOOLTIP)

        self.brick_handling_option = ComboBox()
        for option in _BRICK_HANDLING_OPTIONS:
            self.brick_handling_option.add_item(option)
        self.brick_handling_layout.addWidget(self.brick_handling_option)
        self.brick_handling_option.set_tooltip(_BRICK_HANDLING_OPTIONS_TOOLTIP)
        self.brick_handling_option.item_changed.connect(self.update_downgrade_preferences)

        self.brick_handling_recolor_label = Label("Recolor to")
        self.brick_handling_layout.addWidget(self.brick_handling_recolor_label)

        self.brick_handling_recolor = ColorPropertyWidget('',
        (0,), False, 0xbcbcbcff, True, False)
        self.brick_handling_layout.addWidget(self.brick_handling_recolor)

        self.downgrade_vehicle_button = Button("Downgrade vehicle")
        self.master_layout.addWidget(self.downgrade_vehicle_button)
        self.downgrade_vehicle_button.set_disabled(True)
        self.downgrade_vehicle_button.clicked.connect(self.downgrade_vehicle)

        mw.vehicle_selector_banner.vehicle_loaded.connect(self.on_reloaded)
        self.master_layout.addStretch()



    @staticmethod
    def version_to_int(v: str) -> int:
        return 17 + _SUPPORTED_VERSIONS.index(v) if v in _SUPPORTED_VERSIONS else 0

    @staticmethod
    def int_to_version(v: int) -> str:
        return _SUPPORTED_VERSIONS[v - 17] if v in (17, 18) else '---'

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

    def _make_menu_info(self) -> base.MenuInfo:
        return base.MenuInfo(QIcon(":/assets/icons/DowngradeIcon.png"), True)

    def update_can_downgrade(self):
        self.downgrade_vehicle_button.set_enabled(self.version_to_int(self.current_version_setting.get_text()) >
        self.version_to_int(self.to_version_setting.get_text()) if self.current_version_setting.get_text() != "---" else False)

    def on_reloaded(self):
        version = None
        if self.mw.vehicle_selector_banner.get_brvfile_ref() is not None:
            version = self.mw.vehicle_selector_banner.get_brvfile_ref().version
        self.current_version_setting.set_items([self.int_to_version(version)])
        self.update_downgrade_preferences()
        self.update_can_downgrade()

    def update_downgrade_preferences(self):
        has_1_11_operations: bool = False
        has_1_11_bricks: bool = False

        if self.get_versions()[0] > self.get_versions()[1]:
            if self.get_versions()[1] < 18:
                brvf = self.mw.vehicle_selector_banner.get_brvfile_copy()
                if brvf is None:
                    return
                for brick in brvf.bricks:
                    if brick.meta().name() == bt.MATH_BRICK.name():
                        op = brick.get_property(p.OPERATION)
                        has_1_11_operations = True if op in _1_11_OPERATIONS else has_1_11_operations

                    has_1_11_bricks = True if brick.meta().name() in _1_11_BRICKS else has_1_11_bricks

                    self.operation_handling_surface.setVisible(has_1_11_operations)

                    self.brick_handling_surface.setVisible(has_1_11_bricks)
                    self.brick_handling_recolor.setVisible(self.brick_handling_option.get_current_idx())
                    self.brick_handling_recolor_label.setVisible(self.brick_handling_option.get_current_idx())

        else:
            return



    def downgrade_vehicle(self):
        brvfile = self.mw.vehicle_selector_banner.get_brvfile_copy()  # Faster and respects user intentionally not reloading the vehicle
        if brvfile is None:
            VehicleLoadingIssueDialog.create(self.mw, True).exec()
            return
        brvfile.version = self.get_versions()[1]

        if self.get_versions_str()[0] == _SUPPORTED_VERSIONS[1] and self.get_versions_str()[1] == _SUPPORTED_VERSIONS[0]:
            for brick in brvfile.bricks[:]:
                if brick.meta().name() == bt.MATH_BRICK.name():
                    op = brick.get_property(p.OPERATION)
                    if op == p.Operation.GT:
                        brick.set_property(
                            p.BRICK_COLOR,
                            self.operation_handling_recolor.get_value(0)
                            )

                    elif op == p.Operation.LT:
                        brick.set_property(
                            p.BRICK_COLOR,
                            self.less_handling_color.get_value(0)
                            )

                    elif op in (p.Operation.GE, p.Operation.LE):
                        brick.set_property(p.OPERATION, p.Operation.LT if op == p.Operation.LE else p.Operation.GT)

                    elif op == p.Operation.RECIPROCAL:
                        brick.set_property(p.OPERATION, p.Operation.DIV)

                        old_a = (
                        brick.get_property(p.INPUT_CNL_A_VALUE),
                        brick.get_property(p.INPUT_CNL_A_INPUT_AXIS),
                        brick.get_property(p.INPUT_CNL_A_SOURCE_BRICKS)
                        )
                        new_a = (
                            1.0, # InputCnl_A_Value
                            p.InputCnl_A_InputAxis.CONST,
                            p.InputCnl_A_SourceBricks.EMPTY
                        )

                        brick.set_property(p.INPUT_CNL_A_VALUE, new_a[0])
                        brick.set_property(p.INPUT_CNL_A_INPUT_AXIS, new_a[1])
                        brick.set_property(p.INPUT_CNL_A_SOURCE_BRICKS, new_a[2])

                        brick.set_property(p.INPUT_CNL_B_VALUE, old_a[0])
                        brick.set_property(p.INPUT_CNL_B_INPUT_AXIS, old_a[1])
                        brick.set_property(p.INPUT_CNL_B_SOURCE_BRICKS, old_a[2])

                    elif op == p.Operation.NEGATE:
                        brick.set_property(p.OPERATION, p.Operation.MUL)

                        brick.set_property(p.INPUT_CNL_B_INPUT_AXIS, p.InputCnl_B_InputAxis.CONST)
                        brick.set_property(p.INPUT_CNL_B_VALUE, -1.0)
                        brick.set_property(p.INPUT_CNL_B_SOURCE_BRICKS, p.InputCnl_B_SourceBricks.EMPTY)

                    elif op == p.Operation.SQUARE:
                        brick.set_property(p.OPERATION, p.Operation.POW)

                        brick.set_property(p.INPUT_CNL_B_VALUE, 2.0)
                        brick.set_property(p.INPUT_CNL_B_INPUT_AXIS, p.InputCnl_B_InputAxis.CONST)
                        brick.set_property(p.INPUT_CNL_B_SOURCE_BRICKS, p.InputCnl_B_SourceBricks.EMPTY)

                    brick.reset_property(p.INPUT_CNL_C_INPUT_AXIS)
                    brick.reset_property(p.INPUT_CNL_D_INPUT_AXIS)
                    brick.reset_property(p.INPUT_CNL_E_INPUT_AXIS)

                    brick.reset_property(p.INPUT_CNL_C_SOURCE_BRICKS)
                    brick.reset_property(p.INPUT_CNL_D_SOURCE_BRICKS)
                    brick.reset_property(p.INPUT_CNL_E_SOURCE_BRICKS)

                    brick.reset_property(p.INPUT_CNL_C_VALUE)
                    brick.reset_property(p.INPUT_CNL_D_VALUE)
                    brick.reset_property(p.INPUT_CNL_E_VALUE)

                elif brick.meta().name() in _1_11_BRICKS:
                    new_meta = bt.SCALABLE_BRICK
                    new_brick = Brick(
                        ref=brick.ref,
                        meta=new_meta,
                        pos=brick.pos,
                        rot=brick.rot,
                         ppatch=brick.ppatch
                    )
                    brvfile.add(new_brick)
                    if self.brick_handling_option.get_current_idx():
                        new_brick.set_property(p.BRICK_COLOR, self.brick_handling_recolor.get_value(0))

                    brvfile.bricks.remove(brick)

        logger.info(f"Downgrading vehicle from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")
        self.mw.vehicle_selector_banner.save_brv(brvfile, description=f"Downgraded using the {self.get_menu_name()} from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}.")
        logger.info(f"Vehicle downgraded from {self.get_versions_str()[0]} to {self.get_versions_str()[1]}")
