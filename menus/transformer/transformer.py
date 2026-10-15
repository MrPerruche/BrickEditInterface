from PySide6.QtGui import QIcon

from menus import base

from ui.widgets import Button, LabelStyle, Separator
from ui.dialogs import VehicleLoadingIssueDialog, CannotSaveDialog, NoBricksMatchDialog
from ui.components import BrickSelector
from ui.components.vehicle.brick_transform import transform_bricks
from ui.components.vehicle.transform_settings import TransformSettings, CENTER
from ui.components import Tutorial
from ui.rich_text import pmd

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface

import logging
logger = logging.getLogger(__name__)


class VehicleUpscalerMenu(base.BaseMenu):
    """Menu rotating, scaling and moving the bricks of a vehicle (all of them, or those matching filters)."""

    def __init__(self, mw: 'BrickEditInterface'):
        super().__init__(mw)

        self.mw = mw

        mw.vehicle_selector_banner.vehicle_loaded.connect(self.vehicle_reloaded)

        self.brick_selector = BrickSelector(self.mw, [], allow_all_if_empty=True, updates_requires_reloading=False)
        self.master_layout.addWidget(self.brick_selector)

        self.settings = TransformSettings(CENTER, section_style=LabelStyle.HEADER_3)
        self.master_layout.addWidget(self.settings)

        self.master_layout.addWidget(Separator())

        self.transform_vehicle_button = Button("Set vehicle transform")
        self.master_layout.addWidget(self.transform_vehicle_button)
        self.transform_vehicle_button.clicked.connect(self.save_changes)

        self.vehicle_reloaded()
        self.master_layout.addStretch()

    def vehicle_reloaded(self):
        self.transform_vehicle_button.setDisabled(self.mw.vehicle_selector_banner.get_brvfile_ref() is None)

    def get_menu_name(self) -> str:
        return "Vehicle Transformer"

    def _make_menu_info(self) -> base.MenuInfo:
        return base.MenuInfo(QIcon(":/assets/icons/GizmoIcon.png"), True,
            tutorial=Tutorial(self.get_menu_name(), self.mw)
                .add_text("This menu is meant to rotate, scale and move either the entire "
                    "vehicles or only parts of.")
                .add_steps(
                    "Make sure your vehicle is saved in BR then (re)load in BEI.",
                    "(Optional) Limit what in your vehicle is transformed (offset / rotated / scaled).",
                    "Set transform values (offset / rotation / scale / scale rounding).",
                    "Press \"Set vehicle transform\" then re-open your vehicle in Brick Rigs.",
                )

                .add_header("Selecting bricks")
                .add_text("Applying transform only on parts of the vehicle can be extremely "
                    "useful: creating tiny details, dealing with size limits, etc.")
                .add_text("Selecting only parts of your vehicle is done using filters. If no "
                    "filters are specified, the whole vehicle will be selected.")
                .refer_to("getting_started_filters")

                .add_header("Transforms")
                .add_text("Most transforms are more or less likely to break connections between "
                    "bricks. Transforms are made in the following order: rotate, then scale, then "
                    "round, then offset.")
                .add_text("Rotate: You can rotate by set angles (in degrees) either: the vehicle "
                    "around the center, each brick around its center, or the vehicle around a "
                    "specific point (pivot point).\n"
                    "Scale: You can multiply or divide the scale of a vehicle by a factor. "
                    "Bricks that are not scalable will just be moved. When scaling, it is likely "
                    "many bricks are disconnected.\n"
                    "Brick Size Rounding: Round the brick sizes of vehicles (either "
                    "normally, up or down) by a given step.\n"
                    "Offset: Move the vehicle towards a direction. Only transform that "
                    "shouldn't break connections.")

                .add_sep()
                .add_tips(pmd("**Trying to build tiny details the editor won't let you make?**\n"
                    "You can upscale your vehicle in order to build small details at a scale the "
                    "editor will allow you to, then downscale it back to the original scale with "
                    "the tiny details added."),
                    pmd("**You're limited by editor size limits?**\n"
                    "Using offset transforms, you can move your vehicle around, past the editor "
                    "limits, and build the parts you're working on within bounds."
                    "Keep in mind floating point error may accumulate, use responsibly.")
                )
            )

    def save_changes(self):
        brvfile = self.mw.vehicle_selector_banner.get_brvfile_copy()
        if brvfile is None:
            VehicleLoadingIssueDialog.create(self.mw, True).exec(); return

        error = self.settings.error()
        if error is not None:
            CannotSaveDialog.create(self.mw, error).exec(); return

        bricks = [brick for brick in brvfile.bricks if self.brick_selector.is_allowed(brick)]
        if not bricks:
            NoBricksMatchDialog.create(self.mw).exec(); return

        transform = self.settings.get_transform()
        transform_bricks(bricks, transform, self.settings.get_pivot(bricks))

        summary = f"{transform.describe().capitalize()} {len(bricks):,} brick{'' if len(bricks) == 1 else 's'}."
        logger.info(f"Transforming vehicle: {summary}")
        self.mw.vehicle_selector_banner.save_brv(brvfile, description=f"{summary} Applied with the {self.get_menu_name()}.")
