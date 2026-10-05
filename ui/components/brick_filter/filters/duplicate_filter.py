from enum import Enum

from ui.widgets import NumberChannelEdit, ChannelMode
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.vehicle.brick_analysis import DuplicateAnalysis, DuplicateComparison
from ui.models import TooltipContents
from systems.bei_files import ConfigReader, enum_key

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class DuplicateMatch(Enum):
    COPIES = 0        # Every brick but the first of its group
    HAS_COPIES = 1    # Every brick of a group, the first included
    BEYOND_N = 2      # Every brick past the first N of its group
    FIRST_ONLY = 3    # The first brick of each group, only if it has copies

    def display_name(self) -> str:
        return {
            DuplicateMatch.COPIES: "a copy (not the 1st)",
            DuplicateMatch.HAS_COPIES: "duplicated (1st too)",
            DuplicateMatch.BEYOND_N: "a copy past the Nth",
            DuplicateMatch.FIRST_ONLY: "duplicated (1st only)",
        }[self]


DUPLICATE_TOOLTIP = TooltipContents(
    "Duplicates",
    "Bricks are duplicates if they have the same type, the same position, the same orientation and (depending on "
    "the comparison) the same properties.\n"
    "Among duplicates, the first one is the one which comes first in the vehicle's file. Copies are counted over "
    "the whole vehicle, so combining this condition with others never changes which brick is the first.\n\n"
    "a copy (not the 1st): every duplicate but the first.\n"
    "duplicated (1st too): every duplicate, the first included.\n"
    "a copy past the Nth: every duplicate but the first N.\n"
    "duplicated (1st only): only the first of each group of duplicates."
)
COMPARE_TOOLTIP = TooltipContents(
    "Compare",
    "Everything: type, position, rotation and every property.\n"
    "All but color: same, except the color may differ.\n"
    "Type & transform: type, position and rotation only. Bricks stacked on top of each other."
)
TOLERANCE_TOOLTIP = TooltipContents("Tolerance", "How far apart (in cm, on each axis) two positions can be while still being considered the same.")


class DuplicateFilter(BaseFilter):

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode,
                 match: DuplicateMatch = DuplicateMatch.COPIES,
                 comparison: DuplicateComparison = DuplicateComparison.EVERYTHING,
                 keep_count: int = 1, tolerance: float = 0.1):
        super().__init__(mw)
        self.mode = mode

        self.add_title_row(f"{mode.get_naming_tuple()[0]} be", DUPLICATE_TOOLTIP)

        self.match_cb = self.make_combo_box([m.display_name() for m in DuplicateMatch], match.value)
        self.master_layout.addWidget(self.match_cb)

        self.keep_count_nce = NumberChannelEdit(ChannelMode.INT, minimum=1, maximum=65535, allow_nan=False, allow_inf=False)
        self.keep_count_nce.setValue(keep_count)
        self.keep_count_row = self.add_setting_row("N", self.keep_count_nce)

        self.comparison_cb = self.make_combo_box([c.display_name() for c in DuplicateComparison], comparison.value)
        self.add_setting_row("Compare", self.comparison_cb, COMPARE_TOOLTIP)

        self.tolerance_nce = NumberChannelEdit(ChannelMode.FLOAT32, minimum=0, allow_nan=False, allow_inf=False)
        self.tolerance_nce.setValue(tolerance)
        self.add_setting_row("Tolerance", self.tolerance_nce, TOLERANCE_TOOLTIP)

        self._update_visibility()
        self.match_cb.item_changed.connect(self._update_visibility)
        for signal in (self.match_cb.item_changed, self.comparison_cb.item_changed,
                       self.keep_count_nce.value_changed, self.tolerance_nce.value_changed):
            signal.connect(self.emit_edited)


    def _update_visibility(self, *_):
        self.keep_count_row.setVisible(self.get_match() == DuplicateMatch.BEYOND_N)

    def get_match(self) -> DuplicateMatch:
        return DuplicateMatch(max(self.match_cb.get_current_idx(), 0))

    def get_comparison(self) -> DuplicateComparison:
        return DuplicateComparison(max(self.comparison_cb.get_current_idx(), 0))


    def get_analysis(self) -> DuplicateAnalysis | None:
        vehicle_data = self.get_vehicle_data()
        if vehicle_data is None:
            return None
        comparison, tolerance = self.get_comparison(), float(self.tolerance_nce.value())
        return vehicle_data.get_analysis(
            ("duplicates", comparison, tolerance),
            lambda: DuplicateAnalysis(vehicle_data.brvfile.bricks, comparison, tolerance)
        )


    CONFIG_TYPE = "duplicate"

    def get_config(self) -> dict:
        return {
            "match": enum_key(self.get_match()),
            "n": int(self.keep_count_nce.value()),
            "compare": enum_key(self.get_comparison()),
            "tolerance": float(self.tolerance_nce.value()),
        }

    def apply_config(self, config: ConfigReader) -> None:
        self.match_cb.set_current_idx(config.get_enum("match", DuplicateMatch, self.get_match()).value)
        self.keep_count_nce.setValue(config.get_int("n", int(self.keep_count_nce.value()), 1, 65535))
        self.comparison_cb.set_current_idx(config.get_enum("compare", DuplicateComparison, self.get_comparison()).value)
        self.tolerance_nce.setValue(config.get_float("tolerance", float(self.tolerance_nce.value()), minimum=0.0))

    def is_allowed(self, brick: Brick) -> FilterResult:
        analysis = self.get_analysis()
        info = analysis.get(brick) if analysis is not None else None
        if info is None:
            return self.mode.filter_did_not_match()

        match = self.get_match()
        if match == DuplicateMatch.COPIES:
            matched = info.occurrence > 1
        elif match == DuplicateMatch.HAS_COPIES:
            matched = info.group_size > 1
        elif match == DuplicateMatch.FIRST_ONLY:
            matched = info.occurrence == 1 and info.group_size > 1
        else:
            matched = info.occurrence > self.keep_count_nce.value()
        return self.mode.filter_matched() if matched else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} be a duplicate (...)"

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return DUPLICATE_TOOLTIP

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return DuplicateFilter(mw, mode)
