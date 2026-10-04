from dataclasses import dataclass

from ui.components.vehicle.vehicle_data import VehicleData

from menus.rule_based_editor.actions import ActionContext, ActionResult, BaseAction

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


@dataclass
class ActionOutcome:
    index: int
    action: BaseAction
    result: ActionResult | None  # None if no brick was left to apply it to (skipped)

    def summary(self) -> str:
        return self.result.summary if self.result is not None else "No bricks left to apply it to, skipped."

    def describe(self) -> str:
        return f"{self.index + 1}. {self.action.get_name()}: {self.summary()}"


class ActionFailed(Exception):
    """An action couldn't be applied. error is the original exception (ActionError, FormulaApplyError...)."""

    def __init__(self, index: int, action: BaseAction, error: Exception):
        self.index, self.action, self.error = index, action, error
        super().__init__(f"Action {index + 1} ({action.get_name()}) can't be applied: {error}")


def run_actions(mw: 'BrickEditInterface', actions: list[BaseAction], brvfile: brickedit.BRVFile,
                selected_ids: set[str], vehicle_data: VehicleData) -> list[ActionOutcome]:
    """Applies actions to brvfile (a copy of the loaded vehicle, edited in place). vehicle_data must describe
    brvfile (the loaded vehicle's data does: same bricks, same ref ids). Raises ActionFailed."""
    outcomes = []
    for index, action in enumerate(actions):
        if not selected_ids and action.needs_selection():
            outcomes.append(ActionOutcome(index, action, None))
            continue
        ctx = ActionContext(mw, brvfile, set(selected_ids), vehicle_data)
        try:
            result = action.apply(ctx)
        except Exception as e:
            raise ActionFailed(index, action, e) from e
        outcomes.append(ActionOutcome(index, action, result))
        if result.changed and index < len(actions) - 1:
            vehicle_data = VehicleData(brvfile)  # Duplicates, mirrors... must be found again
        if result.next_selection is not None:
            selected_ids = result.next_selection
    return outcomes
