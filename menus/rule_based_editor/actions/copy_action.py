from ui.widgets import NumberChannelEdit, ChannelMode, BoolSwitch
from ui.models import TooltipContents
from ui.components.brick.property_widgets import Vec3PropertyWidget
from ui.components.vehicle.brick_ops import IdAllocator, copy_brick, remap_references
from systems.bei_files import ConfigReader

from menus.rule_based_editor.actions.base_action import (
    BaseAction, ActionContext, ActionResult, ActionError, plural, MAX_BRICKS
)

import brickedit


class CopyAction(BaseAction):
    """Copies the selection, each copy moved by the offset from the previous one (an array)."""

    def __init__(self, mw):
        super().__init__(mw)

        self.count_nce = NumberChannelEdit(ChannelMode.INT, minimum=1, maximum=MAX_BRICKS, allow_nan=False, allow_inf=False)
        self.count_nce.setValue(1)
        self.add_setting_row("Copies", self.count_nce)

        self.offset_widget = Vec3PropertyWidget('', (brickedit.Vec3(0.0, 0.0, 0.0),), False,
                                                brickedit.Vec3(0.0, 0.0, 30.0), show_text=False)
        self.add_setting_row("Offset", self.offset_widget, TooltipContents(
            "Offset", "How far each copy is moved from the previous one (cm)."))

        self.groups_switch = BoolSwitch(False)
        self.add_setting_row("Copy groups", self.groups_switch, TooltipContents(
            "Copy groups", "Put copies in the editor and weld groups of the original bricks. Otherwise, they "
                           "aren't in any group."))

        for signal in (self.count_nce.value_changed, self.offset_widget.value_changed, self.groups_switch.on_toggled):
            signal.connect(self.emit_options_changed)


    @classmethod
    def get_name(cls) -> str:
        return "Copy"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Copy the selected bricks one or more times",
                               "Wires between copied bricks are copied too.")

    def describe(self, count: int) -> str:
        copies = self.count_nce.value()
        return f"Copy {plural(count)}" + (f" {copies:,} times" if copies > 1 else "")

    def next_selection_hint(self) -> str | None:
        return "The next actions apply to the copies only."


    CONFIG_TYPE = "copy"

    def get_config(self) -> dict:
        return {
            "copies": int(self.count_nce.value()),
            "offset": list(self.offset_widget.get_value(brickedit.Vec3(0.0, 0.0, 0.0)).as_tuple()),
            "copy_groups": self.groups_switch.get_value(),
        }

    def apply_config(self, config: ConfigReader) -> None:
        self.count_nce.setValue(config.get_int("copies", int(self.count_nce.value()), 1, MAX_BRICKS))
        self.offset_widget.set_value(config.get_vec3("offset", self.offset_widget.get_value(brickedit.Vec3(0.0, 0.0, 0.0))))
        self.groups_switch.set_value(config.get_bool("copy_groups", self.groups_switch.get_value()))

    def apply(self, ctx: ActionContext) -> ActionResult:
        copies = int(self.count_nce.value())
        offset = self.offset_widget.get_value(brickedit.Vec3(0.0, 0.0, 0.0))
        keep_groups = self.groups_switch.get_value()
        bricks = ctx.selected_bricks()

        if len(ctx.brvfile.bricks) + copies * len(bricks) > MAX_BRICKS:
            raise ActionError(f"Copying would make this vehicle exceed {MAX_BRICKS:,} bricks.")

        ids = IdAllocator(ctx.brvfile)
        new_bricks = []
        for n in range(1, copies + 1):
            delta = offset * float(n)
            batch, mapping = [], {}
            for brick in bricks:
                copy = copy_brick(brick, ids, keep_groups, pos=brick.pos + delta)
                mapping[brick.ref.id] = copy.ref.id
                batch.append(copy)
            remap_references(batch, mapping)  # Wires inside the selection point to the copies
            new_bricks.extend(batch)

        ctx.brvfile.bricks.extend(new_bricks)
        return ActionResult(f"Created {plural(len(new_bricks))} ({copies:,} {'copy' if copies == 1 else 'copies'} of "
                            f"{plural(len(bricks))}).", bool(new_bricks),
                            next_selection={brick.ref.id for brick in new_bricks})
