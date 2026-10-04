from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon

from collections import defaultdict

from ui.widgets import Label, Button
from ui.models import TooltipContents
from ui.components.brick.property_set import PropertySet
from utils import wipe_layout

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural

import brickedit


class EditPropertiesAction(BaseAction):
    """The brick editor's property editor, applied to every selected brick at once (formulas included)."""

    def __init__(self, mw):
        super().__init__(mw)
        self.property_set: PropertySet | None = None
        self._loaded_ids: tuple[str, ...] | None = None  # Selection the property set was built from
        self._pending: list[brickedit.Brick] | None = None  # Selection waiting for a reload (property set edited)

        info = Label("Properties of the selected bricks. Properties with different values can be edited with "
                     "formulas, like in the brick editor's \"do not split selection\" mode.", muted=True)
        self.master_layout.addWidget(info)

        self.stale_row = QHBoxLayout()
        self.stale_row.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.stale_row)
        self.stale_label = Label("The selection changed since these properties were loaded.")
        self.stale_row.addWidget(self.stale_label, stretch=1)
        self.reload_button = Button("Reload", QIcon.fromTheme("view-refresh"), tint_icon=True)
        self.reload_button.set_tooltip(TooltipContents("Load the properties of the current selection. Discards your edits."))
        self.reload_button.clicked.connect(self._reload_pending)
        self.stale_row.addWidget(self.reload_button)
        self._set_stale(False)

        self.empty_label = Label("No bricks selected.", muted=True)
        self.master_layout.addWidget(self.empty_label)

        self.property_set_container = QVBoxLayout()
        self.property_set_container.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.property_set_container)


    def _set_stale(self, stale: bool):
        self.stale_label.setVisible(stale)
        self.reload_button.setVisible(stale)

    def _reload_pending(self):
        if self._pending is not None:
            self._build(self._pending)

    def has_edits(self) -> bool:
        return self.property_set is not None and self.property_set.edited


    def on_selection_changed(self, bricks: list[brickedit.Brick]) -> None:
        ids = tuple(brick.ref.id for brick in bricks)
        if ids == self._loaded_ids:
            self._pending = None
            self._set_stale(False)
            return
        if self.has_edits():
            # Don't throw the user's edits away: they choose when to reload
            self._pending = bricks
            self._set_stale(True)
            return
        self._build(bricks)


    def _build(self, bricks: list[brickedit.Brick]):
        self._pending = None
        self._set_stale(False)
        self._loaded_ids = tuple(brick.ref.id for brick in bricks)

        wipe_layout(self.property_set_container)
        self.property_set = None
        self.empty_label.setVisible(not bricks)
        if not bricks:
            self.emit_options_changed()
            return

        properties: dict[str, set] = defaultdict(set)
        positions, rotations = set(), set()
        for brick in bricks:
            positions.add(brick.pos)
            rotations.add(brick.rot)
            for prop, value in (brick.get_all_properties() | brick.ppatch).items():
                properties[prop].add(bytes(value) if isinstance(value, bytearray) else value)

        self.property_set = PropertySet(None, properties, set(), positions, rotations)  # type: ignore[arg-type]
        self.property_set.brick_title.hide()
        self.property_set.properties_edited.connect(self.emit_options_changed)
        self.property_set_container.addWidget(self.property_set)
        self.emit_options_changed()


    @classmethod
    def get_name(cls) -> str:
        return "Edit properties"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Edit the position, rotation and properties of the selected bricks",
                               "Works like the brick editor, with every selected brick on a single page.")

    def describe(self, count: int) -> str:
        return f"Edit {plural(count)}"

    CONFIG_TYPE = "edit_properties"

    def config_warning(self) -> str | None:
        if self.has_edits():
            return "Property edits aren't saved in presets: \"Edit properties\" is saved without them."
        return None

    def apply(self, ctx: ActionContext) -> ActionResult:
        if self._pending is not None:
            raise ActionError("The selection changed since the properties were loaded. Reload them (your edits "
                              "will be lost) or go back to the previous selection.")
        if not self.has_edits():
            raise ActionError("No property was edited.")
        bricks = ctx.selected_bricks()
        self.property_set.update_bricks(bricks)  # type: ignore[union-attr]  # Raises FormulaApplyError
        return ActionResult(f"Edited {plural(len(bricks))}.")
