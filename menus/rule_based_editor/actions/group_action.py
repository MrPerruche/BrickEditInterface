from ui.widgets import Switcher, Label
from ui.models import TooltipContents
from ui.components.brick_filter.filters.group_filter import GROUP_NAMING_TOOLTIP
from ui.components.brick_filter.filters.base_filter import BaseFilter
from ui.components.vehicle.brick_ops import IdAllocator
from systems.bei_files import ConfigReader

from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural


KINDS = ("Editor group", "Weld group")
KIND_KEYS = ("editor", "weld")  # Saved
OPERATIONS = ("Named group", "New group", "No group")
OPERATION_KEYS = ("named", "new", "none")  # Saved
EXISTING, NEW, NONE = range(3)


class GroupAction(BaseAction):

    def __init__(self, mw):
        super().__init__(mw)

        self.kind_sw = Switcher(list(KINDS))
        self.add_setting_row("Group type", self.kind_sw)

        self.operation_sw = Switcher(list(OPERATIONS))
        self.add_setting_row("Move to", self.operation_sw, TooltipContents(
            "Move to", "Named group: one named with a text brick. New group: one for all selected bricks."))

        self.wanted_group: str | None = None  # Last group picked. Kept listed if a reloaded vehicle doesn't have it
        self.group_cb = BaseFilter.make_combo_box()
        self.group_row = self.add_setting_row("Group", self.group_cb, GROUP_NAMING_TOOLTIP)
        self.no_named_group_label = Label("No named group of this type.", muted=True)
        self.master_layout.addWidget(self.no_named_group_label)

        self.kind_sw.index_changed.connect(self._on_kind_changed)
        self.operation_sw.index_changed.connect(self._refresh)
        self.group_cb.item_changed.connect(self._on_group_selected)
        mw.vehicle_selector_banner.vehicle_loaded.connect(self._refresh)
        self._refresh()


    def _on_kind_changed(self, *_):
        self.wanted_group = None  # Names of editor groups have nothing to do with names of weld groups
        self._refresh()

    def _on_group_selected(self, *_):
        self.wanted_group = self.group_cb.get_current_text() or None
        self.emit_options_changed()


    def _is_editor(self) -> bool:
        return (self.kind_sw.get_idx() or 0) == 0

    def _named_groups(self) -> dict[str, str]:
        """Group name -> group id, for the selected group type"""
        vehicle_data = self.mw.vehicle_selector_banner.get_brvfile_ref_data()
        if vehicle_data is None:
            return {}
        be_to_bei = vehicle_data.editor_be_to_bei if self._is_editor() else vehicle_data.weld_be_to_bei
        named = {}
        for group_id, name in be_to_bei.items():
            named.setdefault(name, group_id)
        return named


    def _refresh(self, *_):
        previous = self.wanted_group or self.group_cb.get_current_text()
        names = sorted(self._named_groups())
        if self.wanted_group is not None and self.wanted_group not in names:
            names.append(self.wanted_group)  # Can't be applied (see apply), but isn't silently replaced
        self.group_cb.qt_widget.blockSignals(True)
        try:
            self.group_cb.clear_items()
            for name in names:
                self.group_cb.add_item(name)
            if previous in names:
                self.group_cb.set_current_idx(names.index(previous))
        finally:
            self.group_cb.qt_widget.blockSignals(False)

        existing = (self.operation_sw.get_idx() or 0) == EXISTING
        self.group_row.setVisible(existing and bool(names))
        self.no_named_group_label.setVisible(existing and not names)
        self.emit_options_changed()


    @classmethod
    def get_name(cls) -> str:
        return "Set group"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Move the selected bricks to an editor or weld group")

    @classmethod
    def get_description(cls) -> str:
        return "Moves the selected bricks to a named group, a new group, or out of their group."

    def describe(self, count: int) -> str:
        operation = self.operation_sw.get_idx() or 0
        kind = KINDS[self.kind_sw.get_idx() or 0].lower()
        if operation == NONE:
            return f"Ungroup {plural(count)}"
        return f"Move {plural(count)} to {'a new' if operation == NEW else 'an' if kind[0] in 'aeiou' else 'a'} {kind}"

    CONFIG_TYPE = "group"

    def get_config(self) -> dict:
        config = {"group_type": KIND_KEYS[self.kind_sw.get_idx() or 0],
                  "move_to": OPERATION_KEYS[self.operation_sw.get_idx() or 0]}
        if self.group_cb.get_current_text():
            config["group"] = self.group_cb.get_current_text()
        return config

    def apply_config(self, config: ConfigReader) -> None:
        self.kind_sw.set_index(KIND_KEYS.index(config.get_choice("group_type", KIND_KEYS, KIND_KEYS[0])))
        self.operation_sw.set_index(OPERATION_KEYS.index(config.get_choice("move_to", OPERATION_KEYS, OPERATION_KEYS[0])))
        group = config.get_str("group")
        if group:
            self.wanted_group = group
        self._refresh()

    def apply(self, ctx: ActionContext) -> ActionResult:
        operation = self.operation_sw.get_idx() or 0
        kind = KINDS[self.kind_sw.get_idx() or 0].lower()
        editor = self._is_editor()

        if operation == EXISTING:
            name = self.group_cb.get_current_text()
            group_id = self._named_groups().get(name)
            if group_id is None:
                raise ActionError(f"Select a named {kind} to move the bricks to." if not name else
                                  f"This vehicle has no {kind} named \"{name}\".")
            done = f"to the {kind} \"{name}\""
        elif operation == NEW:
            group_id = IdAllocator(ctx.brvfile).new("editor" if editor else "weld")
            done = f"to a new {kind}"
        else:
            group_id = None
            done = f"out of their {kind}"

        bricks = ctx.selected_bricks()
        for brick in bricks:
            if editor:
                brick.ref.editor = group_id
            else:
                brick.ref.weld = group_id
        return ActionResult(f"Moved {plural(len(bricks))} {done}.", bool(bricks))
