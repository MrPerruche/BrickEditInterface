from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QSizePolicy, QComboBox

from ui.widgets import Label, ComboBox
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick.property_utils import get_or_make_property_display_name
from ui.components.brick.property_widgets import get_property_widget_cls
from ui.models import TooltipContents
from systems.bei_files import ConfigReader

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
        self.wanted_property: str | None = None  # Last property picked. Kept listed if a reloaded vehicle lacks it

        self.on_vehicle_reload()  # Populate combo box
        self.combo_box.item_changed.connect(self._on_property_selected)


    def _on_property_selected(self, *_):
        idx = self.combo_box.get_current_idx()
        if 0 <= idx < len(self.internal_properties):
            self.wanted_property = self.internal_properties[idx]
        self.emit_edited()


    def on_vehicle_reload(self):
        # Get old property to put back later if possible
        old_index = self.combo_box.get_current_idx()
        old_property = self.wanted_property
        if old_property is None and self.internal_properties and 0 <= old_index < len(self.internal_properties):
            old_property = self.internal_properties[old_index]

        # Clear stuff then remake. Repopulating is not an edit from the user
        self.combo_box.qt_widget.blockSignals(True)
        try:
            self.combo_box.clear_items()

            vehicle_data = self.mw.vehicle_selector_banner.get_brvfile_ref_data()
            properties = set(vehicle_data.unique_properties) if vehicle_data is not None else set()
            if self.wanted_property is not None:
                properties.add(self.wanted_property)  # Matches nothing, but doesn't silently switch to another

            self.internal_properties = []
            for i, prop in enumerate(sorted(properties)):
                # Add the item
                self.internal_properties.append(prop)
                pretty_name = get_or_make_property_display_name(prop)
                self.combo_box.add_item(pretty_name)
                # If its the old one, set index to that
                if prop == old_property:
                    self.combo_box.set_current_idx(i)
        finally:
            self.combo_box.qt_widget.blockSignals(False)


    def is_allowed(self, brick: Brick) -> FilterResult:
        if len(self.internal_properties) == 0:
            return self.mode.filter_did_not_match()

        brick_props = set((brick.get_all_properties() | brick.ppatch).keys())
        target_prop = self.internal_properties[self.combo_box.get_current_idx()]
        return self.mode.filter_matched() if target_prop in brick_props else self.mode.filter_did_not_match()

    CONFIG_TYPE = "has_property"

    def get_config(self) -> dict:
        idx = self.combo_box.get_current_idx()
        return {"property": self.internal_properties[idx]} if 0 <= idx < len(self.internal_properties) else {}

    def apply_config(self, config: ConfigReader) -> None:
        prop = config.get_str("property")
        if prop:
            self.wanted_property = prop
            self.on_vehicle_reload()
            self.emit_edited()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} have property (...)"

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return None

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return HasPropertyFilter(mw, mode)

