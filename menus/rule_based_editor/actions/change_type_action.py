from PySide6.QtGui import QValidator

from ui.widgets import Label, SuggestionLineEdit
from ui.validators import ASCII_NAME_VALIDATOR
from ui.models import TooltipContents
from ui.components.vehicle.brick_ops import change_brick_type
from systems.bei_files import ConfigReader, BeiFileError

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural

import brickedit


DEFAULT_TYPE = brickedit.bt.SCALABLE_BRICK.name()
MODDED_HINT = "modded"

TYPE_TOOLTIP = TooltipContents("New type", "Internal name, eg. ScalableBrick. Modded types work too.")

def type_suggestions() -> list[tuple[str, str]]:
    """Every brick type BEI knows, and the modded ones of the vehicles loaded so far (UnknownBrickMeta: BEI doesn't
    know their properties)."""
    return [(name, MODDED_HINT if isinstance(meta, brickedit.bt.UnknownBrickMeta) else "")
            for name, meta in brickedit.bt.bt_registry.items()]


class ChangeTypeAction(BaseAction):
    """Turns the selected bricks into bricks of another type, keeping what both types have in common. Any type can be
    typed, modded ones included."""

    def __init__(self, mw):
        super().__init__(mw)
        self._registry_size = len(brickedit.bt.bt_registry)

        self.type_le = SuggestionLineEdit(DEFAULT_TYPE, suggestions=type_suggestions())
        self.type_le.set_validator(ASCII_NAME_VALIDATOR)
        self.type_le.set_tooltip(TYPE_TOOLTIP)
        self.add_setting_row("New type", self.type_le, TYPE_TOOLTIP)


    def get_type(self) -> str:
        """Internal name of the new type. The last valid one while the line edit is blank."""
        return self.type_le.get_text().strip()

    def on_selection_changed(self, bricks: list[brickedit.Brick]) -> None:
        # Loading a vehicle with modded bricks registers their types (UnknownBrickMeta): suggest them too
        if len(brickedit.bt.bt_registry) != self._registry_size:
            self._registry_size = len(brickedit.bt.bt_registry)
            self.type_le.set_suggestions(type_suggestions())


    @classmethod
    def get_name(cls) -> str:
        return "Change type"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return None

    @classmethod
    def get_description(cls) -> str:
        return ("Change what type a brick is. Properties are set to either the current value if "
            "it exists in the old type, or is left to the new type's default value.")

    def describe(self, count: int) -> str:
        return f"Turn {plural(count)} into {self.get_type()}"


    CONFIG_TYPE = "change_type"

    def get_config(self) -> dict:
        return {"brick_type": self.get_type()}

    def apply_config(self, config: ConfigReader) -> None:
        brick_type = config.get_str("brick_type", self.get_type()).strip()
        if ASCII_NAME_VALIDATOR.validate(brick_type, 0)[0] != QValidator.State.Acceptable:
            raise BeiFileError(f"{config.where}: \"{brick_type}\" is not a valid brick type.")
        self.type_le.reset_text(brick_type)  # Unknown types are kept: modded bricks


    def apply(self, ctx: ActionContext) -> ActionResult:
        name = self.get_type()
        if not name:
            raise ActionError("Type the new type of the bricks.")
        meta = brickedit.bt.bt_registry.get(name)
        if meta is None:
            # Modded brick (or typo, the menu warns about it). Registers it, like loading a vehicle using it does
            meta = brickedit.bt.UnknownBrickMeta(name, {})

        changed = already = 0
        bricks = ctx.brvfile.bricks
        for i, brick in enumerate(bricks):
            if brick.ref.id not in ctx.selected_ids:
                continue
            if brick.meta().name() == meta.name():
                already += 1
                continue
            bricks[i] = change_brick_type(brick, meta)  # Same ref: the next actions still apply to it
            changed += 1

        summary = f"Turned {plural(changed)} into {name}"
        if already:
            summary += f", skipped {plural(already)} which already were"
        return ActionResult(summary + ".", changed > 0)
