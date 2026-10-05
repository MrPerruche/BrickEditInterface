from ui.widgets import Label, LineEdit, Switcher
from ui.models import TooltipContents
from ui.components.brick_filter.condition import (
    ConditionModel, ConditionValidator, CONDITION_VARIABLES_TOOLTIP, SAMPLE_BRICK
)
from systems.bei_files import ConfigReader

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.vehicle.vehicle_data import VehicleData


SOURCES = ("Selected bricks", "Whole vehicle")
SOURCE_KEYS = ("selection", "vehicle")  # Saved
SELECTION, VEHICLE = range(2)

SOURCE_TOOLTIP = TooltipContents(
    "Among", "Selected bricks: narrow them down. Whole vehicle: start over, to apply another rule."
)


class SelectAction(BaseAction):
    """Changes which bricks the next actions apply to, with a formula. Only formulas: conditions read the loaded
    vehicle (see BaseFilter.get_vehicle_data), not the vehicle as edited by the previous actions."""

    def __init__(self, mw, formula: str = "y > 0"):
        super().__init__(mw)
        self.model = ConditionModel()

        self.source_sw = Switcher(list(SOURCES))
        self.source_sw.index_changed.connect(self.emit_options_changed)
        self.add_setting_row("Among", self.source_sw, SOURCE_TOOLTIP)

        self.validator = ConditionValidator(self._sample, self)
        self.formula_le = LineEdit(formula)
        self.formula_le.set_validator(self.validator)
        self.formula_le.set_tooltip(CONDITION_VARIABLES_TOOLTIP)
        self.formula_le.text_changed.connect(self._on_text_changed)
        self.add_setting_row("Formula", self.formula_le, CONDITION_VARIABLES_TOOLTIP)

        self.status_label = Label("", muted=True)  # Formula errors
        self.status_label.set_font_size(11)
        self.master_layout.addWidget(self.status_label)

        self._on_text_changed()


    def _sample(self) -> tuple[Brick, 'VehicleData | None']:
        vehicle_data = self.mw.vehicle_selector_banner.get_brvfile_ref_data()
        if vehicle_data is not None and vehicle_data.brvfile.bricks:
            return vehicle_data.brvfile.bricks[0], vehicle_data
        return SAMPLE_BRICK, None

    def _on_text_changed(self, *_):
        text = self.formula_le.get_text()  # Last acceptable text
        if text != self.model.text:
            try:
                self.model.parse(text)
            except ValueError:
                self.model.clear()
            self.emit_options_changed()
        error = self._error()
        self.status_label.set_text(f"Invalid formula: {error}" if error else "")
        self.status_label.setVisible(bool(error))

    def _error(self) -> str | None:
        if self.formula_le.is_valid():
            return None
        return self.validator.last_error or "the formula is incomplete"

    def _source(self) -> int:
        return self.source_sw.get_idx() or 0


    @classmethod
    def get_name(cls) -> str:
        return "Select"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Change which bricks the next actions apply to")

    @classmethod
    def get_description(cls) -> str:
        return "Changes which bricks the next actions apply to, with a formula."

    def describe(self, count: int) -> str:
        return f"Select among {plural(count)}" if self._source() == SELECTION else "Select bricks of the vehicle"

    def needs_selection(self) -> bool:
        return self._source() == SELECTION

    def next_selection_hint(self) -> str | None:
        return "Next actions apply to the matching bricks."


    CONFIG_TYPE = "select"

    def get_config(self) -> dict:
        return {"among": SOURCE_KEYS[self._source()], "formula": self.formula_le.get_true_text()}

    def apply_config(self, config: ConfigReader) -> None:
        self.source_sw.set_index(SOURCE_KEYS.index(config.get_choice("among", SOURCE_KEYS, SOURCE_KEYS[self._source()])))
        # An invalid formula is shown as such and can't be applied (the default formula must not be used instead)
        self.formula_le.reset_text(config.get_str("formula", self.formula_le.get_true_text()))


    def apply(self, ctx: ActionContext) -> ActionResult:
        error = self._error()
        if error is not None or not self.model.is_parsed():
            raise ActionError(f"The formula of \"{self.get_name()}\" is not valid: {error or 'it is empty'}.")

        source = self._source()
        pool = ctx.brvfile.bricks if source == VEHICLE else ctx.selected_bricks()
        selected = set()
        for brick in pool:
            try:
                if self.model.evaluate(brick, ctx.vehicle_data):
                    selected.add(brick.ref.id)
            except ValueError:
                pass  # Can't be evaluated for this brick (eg. a property it doesn't have): doesn't match, like conditions

        if source == VEHICLE:
            summary = f"Selected {plural(len(selected))} of the vehicle."
        else:
            summary = f"Selected {plural(len(selected))} out of {len(pool):,}."
        return ActionResult(summary, changed=False, next_selection=selected)
