from ui.widgets import Label
from ui.models import TooltipContents
from ui.components.vehicle.brick_ops import remove_bricks

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, plural


class DeleteAction(BaseAction):

    def __init__(self, mw):
        super().__init__(mw)
        info = Label("Removes and disconnects selected bricks.", muted=True)
        self.master_layout.addWidget(info)

    @classmethod
    def get_name(cls) -> str:
        return "Delete"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Delete the selected bricks")

    def describe(self, count: int) -> str:
        return f"Delete {plural(count)}"

    def removes_bricks(self) -> bool:
        return True

    def next_selection_hint(self) -> str | None:
        return "No bricks left for the next actions."

    CONFIG_TYPE = "delete"

    def apply(self, ctx: ActionContext) -> ActionResult:
        removed = remove_bricks(ctx.brvfile, ctx.selected_ids)
        return ActionResult(f"Deleted {plural(removed)}.", removed > 0, next_selection=set())
