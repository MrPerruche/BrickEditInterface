from PySide6.QtWidgets import QVBoxLayout

from collections import defaultdict

from ui.widgets import Label
from ui.models import TooltipContents
from ui.components.brick.property_set import PropertySet, POSITION_KEY, ROTATION_KEY
from ui.components.brick.property_edits import needs_formula_mode, read_edit
from ui.components.brick.property_widgets import Vec3PropertyWidget, get_property_widget_cls
from ui.components.brick.property_utils import get_or_make_property_display_name
from systems.bei_files import ConfigReader, BeiFileError
from utils import wipe_layout

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural

import brickedit

import logging
logger = logging.getLogger(__name__)


SAVED_TRANSFORM_KEYS = {POSITION_KEY: "position", ROTATION_KEY: "rotation"}  # Edit key -> key in saved files


def _display_name(key: str) -> str:
    return {POSITION_KEY: "Position", ROTATION_KEY: "Rotation"}.get(key) or get_or_make_property_display_name(key)


def _property_set(bricks: list[brickedit.Brick], edits: dict[str, dict]) -> tuple[PropertySet, dict[str, str]]:
    """A property set of bricks showing edits, and the edits it couldn't show (key -> why)"""
    properties: dict[str, set] = defaultdict(set)
    positions, rotations = set(), set()
    for brick in bricks:
        positions.add(brick.pos)
        rotations.add(brick.rot)
        for prop, value in (brick.get_all_properties() | brick.ppatch).items():
            properties[prop].add(bytes(value) if isinstance(value, bytearray) else value)
    formula_keys = {key for key, edit in edits.items() if needs_formula_mode(edit)}
    property_set = PropertySet(None, properties, set(), positions, rotations, formula_keys)  # type: ignore[arg-type]
    return property_set, property_set.apply_edits(edits)


class EditPropertiesAction(BaseAction):
    """The brick editor's property editor, applied to every selected brick at once (formulas included).

    The edits (self.edits) are the action's settings: saved in presets, and applied again whenever the selection
    changes, to whatever bricks the action applies to. Formulas are evaluated for each brick."""

    def __init__(self, mw):
        super().__init__(mw)
        self.edits: dict[str, dict] = {}  # Property name, POSITION_KEY or ROTATION_KEY -> edit (see property_edits)
        self.property_set: PropertySet | None = None
        self._bricks: list[brickedit.Brick] = []
        self._loaded_ids: frozenset[str] | None = None  # Selection the property set was built from
        self._not_shown: dict[str, str] = {}  # Edits the property set couldn't show: key -> why

        self.empty_label = Label("No bricks selected.", muted=True)
        self.master_layout.addWidget(self.empty_label)

        self.hidden_edits_label = Label("", muted=True)  # Edits of properties the selected bricks don't have
        self.hidden_edits_label.set_font_size(11)
        self.master_layout.addWidget(self.hidden_edits_label)
        self.hidden_edits_label.hide()

        self.property_set_container = QVBoxLayout()
        self.property_set_container.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.property_set_container)


    def has_edits(self) -> bool:
        return bool(self.edits)

    def on_selection_changed(self, bricks: list[brickedit.Brick]) -> None:
        self._bricks = bricks
        if frozenset(brick.ref.id for brick in bricks) != self._loaded_ids:
            self._build()

    def _build(self):
        bricks = self._bricks
        self._loaded_ids = frozenset(brick.ref.id for brick in bricks)
        wipe_layout(self.property_set_container)
        self.property_set = None
        self._not_shown = {}
        self.empty_label.setVisible(not bricks)
        if bricks:
            self.property_set, self._not_shown = _property_set(bricks, self.edits)
            for key, reason in self._not_shown.items():
                logger.warning(f"Edit of {key} can't be shown: {reason}")
            self.property_set.brick_title.hide()
            self.property_set.properties_edited.connect(self._on_edited)
            self.property_set_container.addWidget(self.property_set)
        self._update_hidden_edits()
        self.emit_options_changed()

    def _on_edited(self):
        """Keeps self.edits in sync with the property set. Edits it doesn't show are kept as they are."""
        if self.property_set is None:
            return
        shown = set(self.property_set.widgets_by_key()) - set(self._not_shown)
        self.edits = {key: edit for key, edit in self.edits.items() if key not in shown} | self.property_set.get_edits()
        self._update_hidden_edits()
        self.emit_options_changed()

    def _update_hidden_edits(self):
        shown = set() if self.property_set is None else set(self.property_set.widgets_by_key()) - set(self._not_shown)
        hidden = sorted(_display_name(key) for key in self.edits if key not in shown)
        self.hidden_edits_label.set_text(f"Also edits {', '.join(hidden)} where present." if hidden else "")
        self.hidden_edits_label.setVisible(bool(hidden))


    @classmethod
    def get_name(cls) -> str:
        return "Edit properties"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Edit the properties of the selected bricks, like the brick editor")

    @classmethod
    def get_description(cls) -> str:
        return ("Edits the position, rotation and properties of every selected brick at once, "
            "using formulas, like the brick editor.")

    def describe(self, count: int) -> str:
        return f"Edit {plural(count)}"


    CONFIG_TYPE = "edit_properties"

    def get_config(self) -> dict:
        config: dict = {name: dict(self.edits[key]) for key, name in SAVED_TRANSFORM_KEYS.items() if key in self.edits}
        properties = [{"property": key} | edit for key, edit in sorted(self.edits.items())
                      if key not in SAVED_TRANSFORM_KEYS]
        if properties:
            config["properties"] = properties
        return config

    def apply_config(self, config: ConfigReader) -> None:
        edits: dict[str, dict] = {}
        for key, name in SAVED_TRANSFORM_KEYS.items():
            if name in config.data:
                table = ConfigReader(config.get_raw(name), f"{config.where}, {name}")
                edits[key] = read_edit(table, Vec3PropertyWidget, name)
        for table in config.get_tables("properties"):
            prop = table.get_str("property")
            if not prop or prop in SAVED_TRANSFORM_KEYS:
                raise BeiFileError(f"{table.where}: \"property\" must be the name of a brick property.")
            if prop in edits:
                raise BeiFileError(f"{table.where}: \"{prop}\" is edited twice.")
            edits[prop] = read_edit(table, get_property_widget_cls(prop, allow_unknown=True), prop)
        self.edits = edits
        self._build()


    def apply(self, ctx: ActionContext) -> ActionResult:
        if not self.edits:
            raise ActionError("No property was edited.")
        bricks = ctx.selected_bricks()
        shown = self.property_set is not None and frozenset(brick.ref.id for brick in bricks) == self._loaded_ids
        # Other bricks than the ones shown (eg. copies made by a previous action) get the edits as they're shown
        property_set, not_shown = (self.property_set, self._not_shown) if shown else _property_set(bricks, self.edits)
        try:
            if not_shown:
                key, reason = next(iter(not_shown.items()))
                raise ActionError(f"The edit of \"{_display_name(key)}\" can't be applied: {reason}.")
            property_set.update_bricks(bricks)  # type: ignore[union-attr]  # Raises FormulaApplyError
        finally:
            if not shown:
                property_set.deleteLater()  # type: ignore[union-attr]
        return ActionResult(f"Edited {plural(len(bricks))}.")
