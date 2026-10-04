from ui.models import TooltipContents
from ui.components.vehicle.brick_transform import transform_bricks
from ui.components.vehicle.transform_settings import TransformSettings, CENTER
from systems.bei_files import ConfigReader

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural


class TransformAction(BaseAction):
    """Rotates, scales and moves the selected bricks as a whole (see brick_transform)."""

    def __init__(self, mw):
        super().__init__(mw)
        self.settings = TransformSettings(CENTER)
        self.settings.changed.connect(self.emit_options_changed)
        self.master_layout.addWidget(self.settings)


    @classmethod
    def get_name(cls) -> str:
        return "Transform"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Rotate, scale and move the selected bricks")

    def describe(self, count: int) -> str:
        return f"Transform {plural(count)}"


    CONFIG_TYPE = "transform"

    def get_config(self) -> dict:
        return self.settings.get_config()

    def apply_config(self, config: ConfigReader) -> None:
        self.settings.apply_config(config)


    def apply(self, ctx: ActionContext) -> ActionResult:
        error = self.settings.error()
        if error is not None:
            raise ActionError(error[0].upper() + error[1:] + ".")
        bricks = ctx.selected_bricks()
        transform = self.settings.get_transform()
        transform_bricks(bricks, transform, self.settings.get_pivot(bricks))
        return ActionResult(f"{transform.describe().capitalize()} {plural(len(bricks))}.", bool(bricks))
