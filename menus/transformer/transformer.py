from PySide6.QtGui import QIcon

from menus import base

from ui.widgets import Button, LabelStyle, Separator
from ui.dialogs import VehicleLoadingIssueDialog, CannotSaveDialog, NoBricksMatchDialog
from ui.components import BrickSelector
from ui.components.vehicle.brick_transform import transform_bricks
from ui.components.vehicle.transform_settings import TransformSettings, CENTER

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
        return base.MenuInfo(QIcon(":/assets/icons/GizmoIcon.png"), True)

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
