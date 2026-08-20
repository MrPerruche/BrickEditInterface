from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QSizePolicy, QComboBox

from ui.widgets import Label, ComboBox
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick.property_utils import get_or_make_property_display_name
from ui.components.brick.property_widgets import get_property_widget_cls
from ui.models import TooltipContents

from utils import wipe_layout

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface




class HasPropertyFilter(BaseFilter):

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode):
        super().__init__(mw)
        self.mode = mode

        self.label_layout = QHBoxLayout()
        self.label_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.label_layout)

        self.label = Label(f"{mode.get_naming_tuple()[0]} have property")
        self.label_layout.addWidget(self.label, stretch=1)

        self.label_layout.addWidget(self.remove_filter_button)

        self.combo_box = ComboBox(tint_icons=True)
        self.combo_box.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Fixed
        )
        self.combo_box.qt_widget.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.master_layout.addWidget(self.combo_box)

        self.internal_properties = []

        self.on_vehicle_reload()  # Populate combo box


    def on_vehicle_reload(self):
        # Get old property to put back later if possible
        old_index = self.combo_box.get_current_idx()
        old_property = None
        if self.internal_properties and old_index < len(self.internal_properties):
            old_property = self.internal_properties[old_index]

        # Clear stuff then remake
        self.combo_box.clear_items()

        vehicle_data = self.mw.vehicle_selector_banner.get_brvfile_ref_data()
        if vehicle_data is None:
            # print("no vehicle_data found")
            return

        self.internal_properties = []
        for i, prop in enumerate(sorted(vehicle_data.unique_properties)):
            # Add the item
            self.internal_properties.append(prop)
            pretty_name = get_or_make_property_display_name(prop)
            self.combo_box.add_item(pretty_name)
            # If its the old one, set index to that
            if prop == old_property:
                self.combo_box.set_current_idx(i)


    def is_allowed(self, brick: Brick) -> FilterResult:
        if len(self.internal_properties) == 0:
            return self.mode.filter_did_not_match()

        brick_props = set((brick.get_all_properties() | brick.ppatch).keys())
        target_prop = self.internal_properties[self.combo_box.get_current_idx()]
        return self.mode.filter_matched() if target_prop in brick_props else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} have property (...)"

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return None

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return HasPropertyFilter(mw, mode)

