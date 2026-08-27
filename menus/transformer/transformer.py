from PySide6.QtGui import QIcon

from menus import base

from ui.widgets import Button, ComboBox, Label, StyledLabel, LabelStyle, Surface, NumberChannelEdit, ChannelMode, Switcher
from ui.dialogs import VehicleLoadingIssueDialog
from ui.components.brick.property_widgets import Vec3PropertyWidget
from ui.models import TooltipContents

from brickedit import *

from math import ceil, floor

import logging
logger = logging.getLogger(__name__)


class VehicleUpscalerMenu(base.BaseMenu):
    """Menu for upscaling vehicle properties."""

    def __init__(self, mw):
        super().__init__(mw)

        self.mw = mw

        mw.vehicle_selector_banner.vehicle_loaded.connect(self.vehicle_reloaded)

        self.pos_widget = Surface()
        self.pos_layout = self.pos_widget.layout()
        self.master_layout.addWidget(self.pos_widget)

        self.pos_title = StyledLabel("Position", LabelStyle.LARGE_5)
        self.pos_layout.addWidget(self.pos_title)

        self.pos_label = Label("Offset by")
        self.pos_layout.addWidget(self.pos_label)

        self.pos_vec_widget = Vec3PropertyWidget('', (Vec3(0.0, 0.0, 0.0),), False, Vec3(0.0, 0.0, 0.0), show_text=False)
        self.pos_layout.addWidget(self.pos_vec_widget)

        self.scale_widget = Surface()
        self.scale_layout = self.scale_widget.layout()
        self.master_layout.addWidget(self.scale_widget)

        self.scale_title = StyledLabel("Scale", LabelStyle.LARGE_5)
        self.scale_layout.addWidget(self.scale_title)

        self.scale_mul_label = Label("Multiply by")
        self.scale_layout.addWidget(self.scale_mul_label)

        self.scale_mul_nce = NumberChannelEdit(allow_inf=False, allow_nan=False)
        self.scale_layout.addWidget(self.scale_mul_nce)
        self.scale_mul_nce.setValue(1.0)
        self.scale_mul_nce.value_changed.connect(lambda: self.scale_input_updated(True))

        self.scale_div_label = Label("Divide by")
        self.scale_layout.addWidget(self.scale_div_label)

        self.scale_div_nce = NumberChannelEdit(allow_inf=False, allow_nan=False)
        self.scale_layout.addWidget(self.scale_div_nce)
        self.scale_div_nce.setValue(1.0)
        self.scale_div_nce.value_changed.connect(lambda: self.scale_input_updated(False))

        self.rounding_widget = Surface()
        self.rounding_layout = self.rounding_widget.layout()
        self.master_layout.addWidget(self.rounding_widget)

        self.rounding_title = StyledLabel("Rounding", LabelStyle.LARGE_5)
        self.rounding_layout.addWidget(self.rounding_title)

        self.rounding_mode_label = Label("Mode")
        self.rounding_layout.addWidget(self.rounding_mode_label)

        self.rounding_mode_switcher = Switcher(["Off", "Regular", "Up", "Down"])
        self.rounding_layout.addWidget(self.rounding_mode_switcher)
        self.rounding_mode_switcher.index_changed.connect(self.rounding_updated)

        self.rounding_label = Label("Decimals")
        self.rounding_label.set_tooltip(TooltipContents("Decimals", "Sets the decimals to round the bricks' positions to. Only affects the bricks' shifting from scaling"))
        self.rounding_layout.addWidget(self.rounding_label)

        self.rounding_decimals_nce = NumberChannelEdit(ChannelMode.INT, allow_inf=False, allow_nan=False, minimum=0, maximum=3)
        self.rounding_layout.addWidget(self.rounding_decimals_nce)
        self.rounding_decimals_nce.setDisabled(True)

        # TODO: add rounding to brick positions

        self.transform_vehicle_button = Button("Set vehicle transform")
        self.master_layout.addWidget(self.transform_vehicle_button)
        self.transform_vehicle_button.clicked.connect(self.save_changes)

        self.vehicle_reloaded()
        self.master_layout.addStretch()
    
    @staticmethod
    def ceil(x: float | Vec2 | Vec3, n: int) -> Vec3 | Vec2:
        if isinstance(x, Vec3):
            return Vec3(
            ceil(x.x * 10 ** n) / 10 ** n,
            ceil(x.y * 10 ** n) / 10 ** n,
            ceil(x.z * 10 ** n) / 10 ** n,
            )
        elif isinstance(x, float):
            return ceil(x * 10 ** n) / 10 ** n
        else:
            return Vec2(
            ceil(x.x * 10 ** n) / 10 ** n,
            ceil(x.y * 10 ** n) / 10 ** n,
            )

    @staticmethod
    def floor(x: float | Vec2 | Vec3, n: int) -> Vec3 | Vec2:
        if isinstance(x, Vec3):
            return Vec3(
            floor(x.x * 10 ** n) / 10 ** n,
            floor(x.y * 10 ** n) / 10 ** n,
            floor(x.z * 10 ** n) / 10 ** n,
            )
        elif isinstance(x, float):
            return floor(x * 10 ** n) / 10 ** n
        else:
            return Vec2(
            floor(x.x * 10 ** n) / 10 ** n,
            floor(x.y * 10 ** n) / 10 ** n,
            )

    @staticmethod
    def round(x: Vec3 | Vec2) -> Vec3 | Vec2:
        if isinstance(x, Vec3):
            return Vec3(
            round(x.x * 10 ** n) / 10 ** n,
            round(x.y * 10 ** n) / 10 ** n,
            round(x.z * 10 ** n) / 10 ** n,
            )
        elif isinstance(x, float):
            return round(x * 10 ** n) / 10 ** n
        else:
            return Vec2(
            round(x.x * 10 ** n) / 10 ** n,
            round(x.y * 10 ** n) / 10 ** n,
            )

    def scale_input_updated(self, from_mul: bool):
        if from_mul:
            self.scale_div_nce.blockSignals(True)
            self.scale_div_nce.setValue(1.0 / float(self.scale_mul_nce.get_text()))
            self.scale_div_nce.blockSignals(False)
        else:
            self.scale_mul_nce.blockSignals(True)
            self.scale_mul_nce.setValue(1.0 / float(self.scale_div_nce.get_text()))
            self.scale_mul_nce.blockSignals(False)

    def rounding_updated(self):
        enabled = self.rounding_mode_switcher.get_idx()
        self.rounding_decimals_nce.setEnabled(enabled)

    def get_rounding_mode(self) -> int:
        return self.rounding_mode_switcher.get_idx()

    def get_decimals(self) -> int:
        return int(self.rounding_decimals_nce.get_text())

    def vehicle_reloaded(self):
        brv = self.mw.vehicle_selector_banner.get_brvfile_ref()
        disabled_when_vehicle_unloaded = [self.pos_widget, self.scale_widget, self.transform_vehicle_button]
        for widget in disabled_when_vehicle_unloaded:
            widget.setDisabled(brv is None)

    def get_menu_name(self) -> str:
        return "Vehicle Transformer"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/GizmoIcon.png"), True)

    def save_changes(self):
        brvfile = self.mw.vehicle_selector_banner.get_brvfile_copy()
        if brvfile is None:
            VehicleLoadingIssueDialog.create(True).exec(); return

        # Apply transform
        off_x = float(self.pos_vec_widget.get_value(Vec3(0.0, 0.0, 0.0)).x)
        off_y = float(self.pos_vec_widget.get_value(Vec3(0.0, 0.0, 0.0)).y)
        off_z = float(self.pos_vec_widget.get_value(Vec3(0.0, 0.0, 0.0)).z)
        scale = float(self.scale_mul_nce.get_text())
        
        must_offset = (off_x != 0.0) or (off_y != 0.0) or (off_z != 0.0)
        must_scale = scale != 1.0

        if must_offset:
            for brick in brvfile.bricks:
                brick.pos += Vec3(off_x, off_y, off_z)

        if must_scale:
            for brick in brvfile.bricks:
                # Position
                brick.pos = brick.pos * scale
                # Modify properties
                for prop, val in brick.get_all_properties().items():
                    # Float & vec properties
                    if prop in (
                            p.BRICK_SIZE,
                            p.SPINNER_RADIUS, p.SPINNER_SIZE,
                            p.WHEEL_DIAMETER, p.WHEEL_WIDTH, p.TIRE_WIDTH,
                            p.PATTERN_SCALE,
                            p.FONT_SIZE
                    ):
                        mode = self.get_rounding_mode()
                        decimals = self.get_decimals()
                        brick.set_property(prop, 
                        val * scale if not mode else
                        self.round(val * scale, decimals) if mode == 1 else
                        self.ceil(val * scale, decimals) if mode == 2 else
                        self.floor(val * scale, decimals)
                        )

        logger.info(f"Transforming vehicle with scale {scale}" if must_scale else "Transforming vehicle")
        self.mw.vehicle_selector_banner.save_brv(brvfile, description=f"Transformed using scale {scale}.")
        logger.info(f"Vehicle transformed with scale {scale}" if must_scale else "Transforming vehicle")
