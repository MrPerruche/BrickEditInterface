from enum import Enum

from ui.widgets import NumberChannelEdit, ChannelMode, Switcher, BoolSwitch
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.vehicle.brick_analysis import (
    MirrorAnalysis, MirrorInfo, MirrorSide, AXIS_NAMES, AXIS_KEYS, GAME_POSITION_TOLERANCE, GAME_ANGLE_TOLERANCE
)
from ui.models import TooltipContents
from systems.bei_files import ConfigReader, enum_key

from brickedit import Brick

from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class MirrorStatus(Enum):
    MISSING = 0
    HAS_COUNTERPART = 1
    ON_PLANE = 2
    ROTATION_MISMATCH = 3
    COLOR_MISMATCH = 4
    PROPERTY_MISMATCH = 5
    ANY_ISSUE = 6
    COHERENT = 7

    def display_name(self) -> str:
        return {
            MirrorStatus.MISSING: "No counterpart",
            MirrorStatus.HAS_COUNTERPART: "Has counterpart",
            MirrorStatus.ON_PLANE: "On mirror plane",
            MirrorStatus.ROTATION_MISMATCH: "Bad rotation/size",
            MirrorStatus.COLOR_MISMATCH: "Bad color",
            MirrorStatus.PROPERTY_MISMATCH: "Bad properties",
            MirrorStatus.ANY_ISSUE: "Any issue",
            MirrorStatus.COHERENT: "Perfectly mirrored",
        }[self]

    def matches(self, info: MirrorInfo) -> bool:
        return _STATUS_TESTS[self](info)


_STATUS_TESTS: dict[MirrorStatus, Callable[[MirrorInfo], bool]] = {
    MirrorStatus.MISSING: lambda i: i.missing,
    MirrorStatus.HAS_COUNTERPART: lambda i: not i.missing and i.side != MirrorSide.ON_PLANE,
    MirrorStatus.ON_PLANE: lambda i: i.side == MirrorSide.ON_PLANE,
    MirrorStatus.ROTATION_MISMATCH: lambda i: not i.missing and not i.rotation_ok,
    MirrorStatus.COLOR_MISMATCH: lambda i: not i.missing and not i.color_ok,
    MirrorStatus.PROPERTY_MISMATCH: lambda i: not i.missing and not i.properties_ok,
    MirrorStatus.ANY_ISSUE: lambda i: i.has_issue,
    MirrorStatus.COHERENT: lambda i: not i.has_issue,
}

SIDES = ("Both", "+ side", "- side")
SIDE_KEYS = ("both", "positive", "negative")  # Saved
SIDE_FILTERS = (None, MirrorSide.POSITIVE, MirrorSide.NEGATIVE)


MIRROR_TOOLTIP = TooltipContents(
    "Mirror status",
    "Each brick is paired with the brick of the same type (or its left / right version) located at its mirrored "
    "position. A brick without one is missing a counterpart. Bricks on the mirror plane are their own counterpart, "
    "or are paired with a brick at the same place which is their mirror image (eg. two stacked panels).\n"
    "A pair is perfectly mirrored if both bricks are rotated like mirror images of each other, and share the same "
    "color and properties, mirrored like Brick Rigs does (eg. spinner angles are inverted).\n"
    "By default, only exact mirror images count, like in Brick Rigs. Increase the tolerances for vehicles built "
    "without the game's mirror tools.\n"
    "Brick Rigs vehicles are usually symmetric along the Y axis."
)
SIDE_TOOLTIP = TooltipContents(
    "Side",
    "Only consider bricks on one side of the mirror plane. Eg. to delete the bricks missing a counterpart on one "
    "side only. Bricks on the plane are only included with \"Both\"."
)
POSITION_TOLERANCE_TOOLTIP = TooltipContents(
    "Position tolerance",
    "How far (in cm, on each axis) a counterpart can be from the exact mirrored position. Bricks closer than this to "
    "the mirror plane are on it.\n"
    f"Brick Rigs: {GAME_POSITION_TOLERANCE:g} cm. Eg. 0.1 accepts bricks placed by hand."
)
ANGLE_TOLERANCE_TOOLTIP = TooltipContents(
    "Angle tolerance",
    "How far (in degrees) a counterpart's rotation can be from the exact mirror image's.\n"
    f"Brick Rigs: about {GAME_ANGLE_TOLERANCE:g}°. Eg. 1 accepts bricks rotated by hand."
)
TURNED_TOOLTIP = TooltipContents(
    "Turned symmetric bricks",
    "Also accept a counterpart turned in a way that only looks the same if the brick is symmetric: eg. upside down, "
    "or a 30×60 plate turned by 90° and resized to 60×30. Asymmetric bricks facing the wrong way are accepted too.\n"
    "Brick Rigs doesn't. Bricks on the mirror plane can always be turned: Brick Rigs never pairs a brick with itself."
)


class MirrorFilter(BaseFilter):

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode,
                 status: MirrorStatus = MirrorStatus.MISSING, axis: int = 1, plane_offset: float = 0.0,
                 side: int = 0, tolerance: float = GAME_POSITION_TOLERANCE,
                 angle_tolerance: float = GAME_ANGLE_TOLERANCE, turned: bool = False):
        super().__init__(mw)
        self.mode = mode

        self.add_title_row(f"{mode.get_naming_tuple()[0]} have mirror status", MIRROR_TOOLTIP)

        self.status_cb = self.make_combo_box([s.display_name() for s in MirrorStatus], status.value)
        self.master_layout.addWidget(self.status_cb)

        self.axis_sw = Switcher(list(AXIS_NAMES), axis)
        self.add_setting_row("Mirror axis", self.axis_sw)

        self.offset_nce = NumberChannelEdit(ChannelMode.FLOAT32, allow_nan=False, allow_inf=False)
        self.offset_nce.setValue(plane_offset)
        self.add_setting_row("Plane at", self.offset_nce, TooltipContents(
            "Position of the mirror plane along the mirror axis (cm). 0 is the vehicle's center in Brick Rigs."))

        self.side_sw = Switcher(list(SIDES), side)
        self.add_setting_row("Side", self.side_sw, SIDE_TOOLTIP)

        self.tolerance_nce = NumberChannelEdit(ChannelMode.FLOAT32, decimals=4, minimum=0, allow_nan=False,
                                               allow_inf=False)
        self.tolerance_nce.setValue(tolerance)
        self.add_setting_row("Position tolerance", self.tolerance_nce, POSITION_TOLERANCE_TOOLTIP)

        self.angle_tolerance_nce = NumberChannelEdit(ChannelMode.FLOAT32, decimals=4, minimum=0, maximum=180,
                                                     allow_nan=False, allow_inf=False)
        self.angle_tolerance_nce.setValue(angle_tolerance)
        self.add_setting_row("Angle tolerance", self.angle_tolerance_nce, ANGLE_TOLERANCE_TOOLTIP)

        self.turned_switch = BoolSwitch(turned)
        self.add_setting_row("Turned symmetric bricks", self.turned_switch, TURNED_TOOLTIP)

        for signal in (self.status_cb.item_changed, self.axis_sw.index_changed, self.offset_nce.value_changed,
                       self.side_sw.index_changed, self.tolerance_nce.value_changed,
                       self.angle_tolerance_nce.value_changed, self.turned_switch.on_toggled):
            signal.connect(self.emit_edited)


    def get_status(self) -> MirrorStatus:
        return MirrorStatus(max(self.status_cb.get_current_idx(), 0))

    def get_axis(self) -> int:
        return self.axis_sw.get_idx() or 0

    def get_analysis(self) -> MirrorAnalysis | None:
        vehicle_data = self.get_vehicle_data()
        if vehicle_data is None:
            return None
        return MirrorAnalysis.cached(
            vehicle_data, self.get_axis(), float(self.offset_nce.value()), float(self.tolerance_nce.value()),
            float(self.angle_tolerance_nce.value()), self.turned_switch.get_value()
        )


    CONFIG_TYPE = "mirror"

    def get_config(self) -> dict:
        return {
            "status": enum_key(self.get_status()),
            "axis": AXIS_KEYS[self.get_axis()],
            "plane": float(self.offset_nce.value()),
            "side": SIDE_KEYS[self.side_sw.get_idx() or 0],
            "tolerance": float(self.tolerance_nce.value()),
            "angle_tolerance": float(self.angle_tolerance_nce.value()),
            "turned_bricks": self.turned_switch.get_value(),
        }

    def apply_config(self, config: ConfigReader) -> None:
        self.status_cb.set_current_idx(config.get_enum("status", MirrorStatus, self.get_status()).value)
        self.axis_sw.set_index(AXIS_KEYS.index(config.get_choice("axis", AXIS_KEYS, AXIS_KEYS[self.get_axis()])))
        self.offset_nce.setValue(config.get_float("plane", float(self.offset_nce.value())))
        self.side_sw.set_index(SIDE_KEYS.index(config.get_choice("side", SIDE_KEYS, SIDE_KEYS[self.side_sw.get_idx() or 0])))
        self.tolerance_nce.setValue(config.get_float("tolerance", float(self.tolerance_nce.value()), minimum=0.0))
        self.angle_tolerance_nce.setValue(config.get_float(
            "angle_tolerance", float(self.angle_tolerance_nce.value()), minimum=0.0, maximum=180.0))
        self.turned_switch.set_value(config.get_bool("turned_bricks", self.turned_switch.get_value()))

    def is_allowed(self, brick: Brick) -> FilterResult:
        analysis = self.get_analysis()
        info = analysis.get(brick) if analysis is not None else None
        if info is None:
            return self.mode.filter_did_not_match()

        side = SIDE_FILTERS[self.side_sw.get_idx() or 0]
        matched = (side is None or info.side == side) and self.get_status().matches(info)
        return self.mode.filter_matched() if matched else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} have mirror status (...)"

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return MIRROR_TOOLTIP

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return MirrorFilter(mw, mode)
