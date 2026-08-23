from PySide6.QtGui import QIcon, QColor

from ui.components.gradient.editor import GradientEditor
from ui.widgets import Button, ComboBox, Label, Surface, NumberChannelEdit, ChannelMode, StyledLabel, LabelStyle
from ui.models import TooltipContents
from ui.dialogs import VehicleLoadingIssueDialog
from menus import base

import os

from brickedit import *
from utils import try_serialize, try_serialize_metadata


def col_as_tuple(col: QColor) -> tuple[int, int, int, int]:
    return col.red(), col.green(), col.blue(), col.alpha()



class GradientMaker(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)

        self.special_bricks = [bt.TEXT_BRICK.name(), bt.TEXT_CYLINDER.name(), bt.SPINNER_BRICK.name()]
        self.special_bricks_str = ', '.join(self.special_bricks)
        self.sorted_bt_registry = self.special_bricks + sorted([
            k for k, v in bt.bt_registry.items()
            if ((p.BRICK_SIZE in v.p.keys() or p.SPINNER_SIZE in v.p.keys())
                and k not in self.special_bricks)
        ])
        self.brick_count: int = 50

        self.gradient_editor = GradientEditor()
        self.master_layout.addWidget(self.gradient_editor)

        # BRICK SETTINGS
        self.brick_settings_widget = Surface()
        self.brick_settings_layout = self.brick_settings_widget.layout()
        self.setLayout(self.brick_settings_layout)
        self.master_layout.addWidget(self.brick_settings_widget)

        self.brick_settings_title = StyledLabel("Brick settings", LabelStyle.LARGE_5)
        self.brick_settings_layout.addWidget(self.brick_settings_title)

        self.brick_count_label = Label("Brick count")
        self.brick_settings_layout.addWidget(self.brick_count_label)

        self.brick_count_nce = NumberChannelEdit(ChannelMode.INT, minimum=2, maximum=5000, allow_inf=False, allow_nan=False)
        self.brick_count_nce.setValue(50)

        self.brick_settings_layout.addWidget(self.brick_count_nce)
        self.brick_count_nce.value_changed.connect(self.on_brick_count_updated)

        self.brick_type_label = Label("Brick type")
        self.brick_settings_layout.addWidget(self.brick_type_label)
        self.brick_type_label.set_tooltip(TooltipContents("Brick type", f"{self.special_bricks_str} have special interactions."))

        self.brick_type_setting = ComboBox()
        for bricktype in self.sorted_bt_registry:
            self.brick_type_setting.add_item(bricktype)
        self.brick_settings_layout.addWidget(self.brick_type_setting)

        self.create_gradient_button = Button("Create vehicle")
        self.create_gradient_button.clicked.connect(self.create_vehicle)
        self.master_layout.addWidget(self.create_gradient_button)

        self.master_layout.addStretch()


    def get_menu_name(self):
        return "Gradient Maker"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/GradientIconNew.png"), True)

    def on_brick_count_updated(self):
        self.brick_count = int(self.brick_count_nce.get_text())

    def create_vehicle(self):

        # Make sure we can create the vehicle
        if self.main_window.vehicle_selector_banner.is_vehicle_loaded():
            VehicleLoadingIssueDialog.create(False).exec()
            return

        # Get values
        num_bricks = self.brick_count
        # SET THE LIST OF COLORS MAKING THE GRADIENT
        brick_colors = [self.gradient_editor.get_color_at_pos(i / (num_bricks-1) * 100) for i in range(num_bricks)]

        # CREATE VEHICLE
        brv = BRVFile(FILE_MAIN_VERSION)
        vh = vhelper.ValueHelper(FILE_MAIN_VERSION)

        brick_type = bt.bt_registry.get(self.brick_type_setting.get_current_text())
        if brick_type is None:
            brick_type = bt.TEXT_BRICK

        brick_size = min(0.5, 6 / num_bricks)  # Minimum between 60cm and a total length under 500cm

        for i, qbc in enumerate(brick_colors):
            bc = col_as_tuple(qbc)
            nbc = vhelper.color.pack_float_to_int(*[c/255 for c in bc])
            color_str = f"{bc[0]:02x}{bc[1]:02x}{bc[2]:02x}"

            # Spinner brick
            if brick_type == bt.SPINNER_BRICK:
                angle_per_step = 360 / num_bricks
                brv.add(Brick(
                    ID(f"brick_{i}"),
                    brick_type,
                    pos=Vec3(0, 0, 0),
                    rot=Vec3(0, 0, angle_per_step*i),
                    ppatch={
                        p.BRICK_COLOR: nbc,
                        p.SPINNER_RADIUS: Vec2(200, 200),
                        p.SPINNER_SIZE: Vec2(100, 50),
                        p.SPINNER_ANGLE: angle_per_step
                    }
                ))
            else:
                brv.add(Brick(
                    ID(f"brick_{i}"),
                    brick_type,
                    pos=vh.pos(i*brick_size, 0, 0),
                    rot=Vec3(0, 0, 90),
                    ppatch={
                        p.BRICK_COLOR: nbc,
                        p.BRICK_SIZE: vh.pos(0.5, brick_size, 0.5),
                        p.TEXT: f"Brick {i+1}/{num_bricks}\n#{color_str}",
                        p.FONT: p.Font.ORBITRON,
                        p.FONT_SIZE: 10
                    }
                ))


        colorspace = self.gradient_editor.current_space().label
        description = f"Created using the {self.get_menu_name()}: {num_bricks}-bricks {colorspace} gradient"
        self.main_window.vehicle_selector_banner.save_brv(brv, description=description)
