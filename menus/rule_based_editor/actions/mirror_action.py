from ui.widgets import Switcher, NumberChannelEdit, ChannelMode, BoolSwitch
from ui.models import TooltipContents
from ui.components.vehicle.brick_analysis import (
    MirrorAnalysis, MirrorSide, AXIS_NAMES, AXIS_KEYS, GAME_POSITION_TOLERANCE, is_reference_property
)
from systems.bei_files import ConfigReader
from ui.components.vehicle.brick_ops import IdAllocator, mirror_brick, remap_references, remove_bricks

from menus.rule_based_editor.actions.base_action import (
    BaseAction, ActionContext, ActionResult, ActionError, plural, MAX_BRICKS, COPY_GROUPS_TOOLTIP
)


COUNTERPARTS = ("Skip", "Replace", "Keep both")
COUNTERPART_KEYS = ("skip", "replace", "keep_both")  # Saved
SKIP, REPLACE, KEEP_BOTH = range(3)

COUNTERPART_TOOLTIP = TooltipContents(
    "If the mirrored position is taken",
    "Skip: don't mirror. Replace: delete the brick there (its wires go to the new one). Keep both: may duplicate."
)
TOLERANCE_TOOLTIP = TooltipContents(
    "Tolerance (cm)",
    f"Max gap to count as the same position, or as on the plane. Brick Rigs: {GAME_POSITION_TOLERANCE:g}."
)


class MirrorAction(BaseAction):

    def __init__(self, mw, axis: int = 1, plane_offset: float = 0.0, counterparts: int = SKIP):
        super().__init__(mw)

        self.axis_sw = Switcher(list(AXIS_NAMES), axis)
        self.add_setting_row("Mirror axis", self.axis_sw)

        self.offset_nce = NumberChannelEdit(ChannelMode.FLOAT32, allow_nan=False, allow_inf=False)
        self.offset_nce.setValue(plane_offset)
        self.add_setting_row("Plane at (cm)", self.offset_nce, TooltipContents("0 is the vehicle's center."))

        self.counterparts_sw = Switcher(list(COUNTERPARTS), counterparts)
        self.add_setting_row("Counterparts", self.counterparts_sw, COUNTERPART_TOOLTIP)

        self.tolerance_nce = NumberChannelEdit(ChannelMode.FLOAT32, decimals=4, minimum=0, allow_nan=False,
                                               allow_inf=False)
        self.tolerance_nce.setValue(GAME_POSITION_TOLERANCE)
        self.add_setting_row("Tolerance", self.tolerance_nce, TOLERANCE_TOOLTIP)

        self.groups_switch = BoolSwitch(False)
        self.add_setting_row("Copy groups", self.groups_switch, COPY_GROUPS_TOOLTIP)

        for signal in (self.axis_sw.index_changed, self.offset_nce.value_changed, self.counterparts_sw.index_changed,
                       self.tolerance_nce.value_changed, self.groups_switch.on_toggled):
            signal.connect(self.emit_options_changed)


    @classmethod
    def get_name(cls) -> str:
        return "Mirror"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Create mirrored copies of the selected bricks", "Mirrors like Brick Rigs does.")

    def describe(self, count: int) -> str:
        return f"Mirror {plural(count)}"

    def removes_bricks(self) -> bool:
        return (self.counterparts_sw.get_idx() or 0) == REPLACE

    def next_selection_hint(self) -> str | None:
        return "Next actions apply to the mirror images."


    CONFIG_TYPE = "mirror"

    def get_config(self) -> dict:
        return {
            "axis": AXIS_KEYS[self.axis_sw.get_idx() or 0],
            "plane": float(self.offset_nce.value()),
            "counterparts": COUNTERPART_KEYS[self.counterparts_sw.get_idx() or 0],
            "tolerance": float(self.tolerance_nce.value()),
            "copy_groups": self.groups_switch.get_value(),
        }

    def apply_config(self, config: ConfigReader) -> None:
        self.axis_sw.set_index(AXIS_KEYS.index(config.get_choice("axis", AXIS_KEYS, AXIS_KEYS[self.axis_sw.get_idx() or 0])))
        self.offset_nce.setValue(config.get_float("plane", float(self.offset_nce.value())))
        self.counterparts_sw.set_index(COUNTERPART_KEYS.index(
            config.get_choice("counterparts", COUNTERPART_KEYS, COUNTERPART_KEYS[self.counterparts_sw.get_idx() or 0])))
        self.tolerance_nce.setValue(config.get_float("tolerance", float(self.tolerance_nce.value()), minimum=0.0))
        self.groups_switch.set_value(config.get_bool("copy_groups", self.groups_switch.get_value()))


    def apply(self, ctx: ActionContext) -> ActionResult:
        axis = self.axis_sw.get_idx() or 0
        offset = float(self.offset_nce.value())
        tolerance = float(self.tolerance_nce.value())
        counterparts = self.counterparts_sw.get_idx() or 0
        keep_groups = self.groups_switch.get_value()

        # Pairs of the loaded vehicle (ctx.brvfile is a copy of it: same ref ids). Only positions matter here
        analysis = MirrorAnalysis.cached(ctx.vehicle_data, axis, offset, tolerance)

        ids = IdAllocator(ctx.brvfile)
        created: dict[str, str] = {}   # original ref id -> id of its new mirror image
        replaced: dict[str, str] = {}  # removed counterpart id -> id of the brick replacing it
        new_bricks = []
        on_plane = skipped = ambiguous = 0

        for brick in ctx.selected_bricks():
            info = analysis.info.get(brick.ref.id)
            if info is None or info.side == MirrorSide.ON_PLANE:
                on_plane += 1
                continue
            if not info.missing:
                if counterparts == SKIP:
                    skipped += 1
                    continue
                if counterparts == REPLACE and info.counterpart in ctx.selected_ids:
                    ambiguous += 1  # Both sides selected: which one replaces the other?
                    continue

            mirrored = mirror_brick(brick, axis, offset, ids, keep_groups)
            created[brick.ref.id] = mirrored.ref.id
            new_bricks.append(mirrored)
            if not info.missing and counterparts == REPLACE:
                replaced[info.counterpart] = mirrored.ref.id  # type: ignore[index]

        if len(ctx.brvfile.bricks) + len(new_bricks) - len(replaced) > MAX_BRICKS:
            raise ActionError(f"Mirroring would make this vehicle exceed {MAX_BRICKS:,} bricks.")

        # Wire mirrored bricks like their originals, but to the mirror image of each source when there is one
        def mirrored_id(ref_id: str) -> str | None:
            if ref_id in created:
                return created[ref_id]
            source = analysis.info.get(ref_id)
            if source is not None and source.counterpart is not None and source.side != MirrorSide.ON_PLANE:
                return replaced.get(source.counterpart, source.counterpart)
            return None
        mapping = {ref: target for brick in new_bricks for ref in _references(brick)
                   if (target := mirrored_id(ref)) is not None}
        remap_references(new_bricks, mapping)

        ctx.brvfile.bricks.extend(new_bricks)
        if replaced:
            remap_references(ctx.brvfile.bricks, replaced)
            remove_bricks(ctx.brvfile, set(replaced))

        parts = [f"Mirrored {plural(len(new_bricks))}"]
        if replaced:
            parts.append(f"replaced {plural(len(replaced), 'counterpart')}")
        if skipped:
            parts.append(f"skipped {plural(skipped)} which already had a counterpart")
        if ambiguous:
            parts.append(f"skipped {plural(ambiguous)} whose counterpart is selected too")
        if on_plane:
            parts.append(f"skipped {plural(on_plane)} on the mirror plane")
        return ActionResult(", ".join(parts) + ".", bool(new_bricks),
                            next_selection={brick.ref.id for brick in new_bricks})


def _references(brick) -> set[str]:
    refs = set()
    for prop, value in brick.ppatch.items():
        if value is None or not is_reference_property(prop):
            continue
        refs.update(value if isinstance(value, tuple) else (value,))
    return refs
