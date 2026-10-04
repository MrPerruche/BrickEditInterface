from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick.property_utils import get_or_make_property_display_name
from ui.models import TooltipContents
from systems.bei_files import ConfigReader

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface




class HasPropertyFilter(BaseFilter):

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode):
        super().__init__(mw)
        self.mode = mode
        self.internal_properties: list[str] = []  # In the combo box's order
        self.wanted_property: str | None = None  # Kept listed if a reloaded vehicle doesn't have it

        self.add_title_row(f"{mode.get_naming_tuple()[0]} have property")
        self.combo_box = self.make_combo_box()
        self.master_layout.addWidget(self.combo_box)

        self.on_vehicle_reload()  # Populate combo box
        self.combo_box.item_changed.connect(self._on_property_selected)


    def _on_property_selected(self, *_):
        idx = self.combo_box.get_current_idx()
        if 0 <= idx < len(self.internal_properties):
            self.wanted_property = self.internal_properties[idx]
        self.emit_edited()


    def on_vehicle_reload(self):
        vehicle_data = self.get_vehicle_data()
        properties = set(vehicle_data.unique_properties) if vehicle_data is not None else set()
        if self.wanted_property is not None:
            properties.add(self.wanted_property)  # Matches nothing, but doesn't silently switch to another
        self.internal_properties = sorted(properties, key=get_or_make_property_display_name)

        # Repopulating is not an edit from the user
        self.combo_box.qt_widget.blockSignals(True)
        try:
            self.combo_box.clear_items()
            for prop in self.internal_properties:
                self.combo_box.add_item(get_or_make_property_display_name(prop))
            if self.wanted_property not in self.internal_properties:
                self.wanted_property = self.internal_properties[0] if self.internal_properties else None
            if self.wanted_property is not None:
                self.combo_box.set_current_idx(self.internal_properties.index(self.wanted_property))
        finally:
            self.combo_box.qt_widget.blockSignals(False)


    def is_allowed(self, brick: Brick) -> FilterResult:
        prop = self.wanted_property
        if prop is not None and (prop in brick.ppatch or prop in brick.get_all_properties()):
            return self.mode.filter_matched()
        return self.mode.filter_did_not_match()

    CONFIG_TYPE = "has_property"

    def get_config(self) -> dict:
        return {"property": self.wanted_property} if self.wanted_property is not None else {}

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

