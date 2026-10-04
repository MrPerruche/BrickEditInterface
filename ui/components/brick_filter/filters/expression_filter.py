from ui.widgets import Label, LineEdit
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick_filter.condition import (
    ConditionModel, ConditionValidator, CONDITION_VARIABLES_TOOLTIP, SAMPLE_BRICK
)
from ui.models import TooltipContents
from systems.bei_files import ConfigReader

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface
    from ui.components.vehicle.vehicle_data import VehicleData


HINT_TEXT = "Hover for the list of variables."


class ExpressionFilter(BaseFilter):
    """Matches bricks for which a condition written by the user is true. A brick for which the condition can't be
    evaluated (eg. it uses a property the brick doesn't have) does not match."""

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode, condition: str = "y > 0"):
        super().__init__(mw)
        self.mode = mode
        self.model = ConditionModel()

        self.add_title_row(f"{mode.get_naming_tuple()[0]} satisfy condition", CONDITION_VARIABLES_TOOLTIP)

        self.validator = ConditionValidator(self._sample, self)
        self.condition_le = LineEdit(condition)
        self.condition_le.set_validator(self.validator)
        self.condition_le.set_tooltip(CONDITION_VARIABLES_TOOLTIP)
        self.condition_le.text_changed.connect(self._on_text_changed)
        self.master_layout.addWidget(self.condition_le)

        self.status_label = Label(HINT_TEXT, muted=True)
        self.status_label.set_font_size(11)
        self.status_label.set_tooltip(CONDITION_VARIABLES_TOOLTIP)
        self.master_layout.addWidget(self.status_label)

        self._on_text_changed()


    def _sample(self) -> tuple[Brick, 'VehicleData | None']:
        vehicle_data = self.get_vehicle_data()
        if vehicle_data is not None and vehicle_data.brvfile.bricks:
            return vehicle_data.brvfile.bricks[0], vehicle_data
        return SAMPLE_BRICK, None


    def _on_text_changed(self, *_):
        text = self.condition_le.get_text()  # Last acceptable text
        if text != self.model.text:
            try:
                self.model.parse(text)
            except ValueError:
                self.model.clear()
            self.emit_edited()

        error = self.validator.last_error if not self.condition_le.is_valid() else None
        self.status_label.set_text(f"Not applied: {error}" if error else HINT_TEXT)


    CONFIG_TYPE = "condition"

    def get_config(self) -> dict:
        return {"condition": self.condition_le.get_true_text()}

    def apply_config(self, config: ConfigReader) -> None:
        # An invalid condition is shown as such and matches nothing (the default condition must not be used instead)
        self.condition_le.reset_text(config.get_str("condition", self.condition_le.get_true_text()))

    def is_allowed(self, brick: Brick) -> FilterResult:
        if not self.model.is_parsed():
            return self.mode.filter_did_not_match()
        try:
            match = self.model.evaluate(brick, self.get_vehicle_data())
        except ValueError:
            match = False
        return self.mode.filter_matched() if match else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} satisfy condition (...)"

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return CONDITION_VARIABLES_TOOLTIP

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return ExpressionFilter(mw, mode)
