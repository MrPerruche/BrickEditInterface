from ui.widgets import LineEdit
from ui.validators import HEX_4COLOR_VALIDATOR
from ui.models import TooltipContents
from ui.components.brick.materials import MATERIALS
from ui.components.brick_filter.filters.base_filter import BaseFilter
from ui.components.brick_filter.filters.color_filter import HEX_COLOR
from systems.bei_files import ConfigReader, BeiFileError

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural

import brickedit


COLOR_TOOLTIP = TooltipContents("RRGGBBAA hexadecimal color")
KEEP_MATERIAL = "Keep current"


class PaintAction(BaseAction):
    """Sets the color (and optionally the material) of the selected bricks. Handy to spot them in Brick Rigs before
    deciding what to do."""

    def __init__(self, mw, color: str = "FF00FFFF"):
        super().__init__(mw)
        self.color_le = LineEdit(color)
        self.color_le.set_validator(HEX_4COLOR_VALIDATOR)
        self.color_le.text_changed.connect(self._update_preview)
        self.add_setting_row("Color", self.color_le, COLOR_TOOLTIP)

        self.material_cb = BaseFilter.make_combo_box([KEEP_MATERIAL] + [display for _, display, _ in MATERIALS])
        self.material_cb.item_changed.connect(self.emit_options_changed)
        self.add_setting_row("Material", self.material_cb)

        self._update_preview()

    def set_color(self, color: str):
        self.color_le.set_text(color)

    def _update_preview(self, *_):
        rgba = self.color_le.get_text()
        self.color_le.set_border_color('#' + rgba[-2:] + rgba[:-2])  # ARGB
        self.emit_options_changed()

    def get_packed_color(self) -> int:
        return int(self.color_le.get_text(), 16)  # RRGGBBAA, packed like ColorPropertyWidget

    def get_material(self) -> str | None:
        """Internal material name, or None to keep each brick's material"""
        idx = self.material_cb.get_current_idx()
        return MATERIALS[idx - 1][0] if idx >= 1 else None

    @classmethod
    def get_name(cls) -> str:
        return "Paint"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Set the color and material of the selected bricks")

    def describe(self, count: int) -> str:
        return f"Paint {plural(count)}"

    CONFIG_TYPE = "paint"

    def get_config(self) -> dict:
        return {"color": self.color_le.get_text().upper(), "material": self.get_material() or ""}

    def apply_config(self, config: ConfigReader) -> None:
        color = config.get_str("color", self.color_le.get_text())
        if not HEX_COLOR.fullmatch(color):
            raise BeiFileError(f"{config.where}: \"{color}\" is not a RRGGBBAA color.")
        self.set_color(color.upper())
        material = config.get_str("material")
        materials = [name for name, _, _ in MATERIALS]
        if material and material not in materials:
            raise BeiFileError(f"{config.where}: unknown material \"{material}\".")
        self.material_cb.set_current_idx(materials.index(material) + 1 if material else 0)

    def apply(self, ctx: ActionContext) -> ActionResult:
        if not self.color_le.is_valid():
            raise ActionError("The color is not a valid RRGGBBAA hexadecimal color.")
        color, material = self.get_packed_color(), self.get_material()
        painted = 0
        for brick in ctx.selected_bricks():
            changed = False
            for prop, value in ((brickedit.p.BRICK_COLOR, color), (brickedit.p.BRICK_MATERIAL, material)):
                if value is None:
                    continue
                try:
                    brick.get_property(prop)
                except brickedit.BrickError:
                    continue  # Brick without color / material
                brick.set_property(prop, value)
                changed = True
            painted += changed
        return ActionResult(f"Painted {plural(painted)}.", painted > 0)
