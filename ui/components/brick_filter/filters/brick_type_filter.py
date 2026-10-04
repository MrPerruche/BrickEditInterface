from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick.property_utils import get_or_make_property_display_name
from systems.bei_files import ConfigReader

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class BrickTypeFilter(BaseFilter):

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode, brick_type: str | None = None):
        super().__init__(mw)
        self.mode = mode
        self.types: list[str] = []  # Internal names, in the combo box's order
        self.wanted_type = brick_type  # Kept while the vehicle doesn't have it, in case it's reloaded

        self.add_title_row(f"Brick type {mode.get_naming_tuple()[1]} be")
        self.combo_box = self.make_combo_box()
        self.master_layout.addWidget(self.combo_box)

        self.on_vehicle_reload()
        self.combo_box.item_changed.connect(self._on_type_selected)


    def on_vehicle_reload(self):
        vehicle_data = self.get_vehicle_data()
        types = set(vehicle_data.unique_types) if vehicle_data is not None else set()
        if self.wanted_type is not None:
            types.add(self.wanted_type)
        self.types = sorted(types, key=get_or_make_property_display_name)

        self.combo_box.qt_widget.blockSignals(True)
        try:
            self.combo_box.clear_items()
            for brick_type in self.types:
                self.combo_box.add_item(get_or_make_property_display_name(brick_type))
            if self.wanted_type in self.types:
                self.combo_box.set_current_idx(self.types.index(self.wanted_type))
            elif self.types:
                self.wanted_type = self.types[0]
        finally:
            self.combo_box.qt_widget.blockSignals(False)


    def _on_type_selected(self):
        idx = self.combo_box.get_current_idx()
        if 0 <= idx < len(self.types):
            self.wanted_type = self.types[idx]
        self.emit_edited()


    CONFIG_TYPE = "brick_type"

    def get_config(self) -> dict:
        return {"brick_type": self.wanted_type} if self.wanted_type is not None else {}

    def apply_config(self, config: ConfigReader) -> None:
        brick_type = config.get_str("brick_type")
        if brick_type:
            self.wanted_type = brick_type  # Kept even if the vehicle (or BEI) doesn't know it: modded bricks
            self.on_vehicle_reload()
            self.emit_edited()

    def is_allowed(self, brick: Brick) -> FilterResult:
        if brick.meta().name() == self.wanted_type:
            return self.mode.filter_matched()
        return self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"Brick type {mode.get_naming_tuple()[1]} be (...)"

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return BrickTypeFilter(mw, mode)
