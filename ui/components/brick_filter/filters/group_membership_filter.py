from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick_filter.filters.group_filter import GROUP_NAMING_TOOLTIP
from systems.bei_files import ConfigReader

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


# (display name, editor group?, named groups match, unnamed groups match)
MEMBERSHIPS = (
    ("any editor group", True, True, True),
    ("a named editor group", True, True, False),
    ("an unnamed editor group", True, False, True),
    ("any weld group", False, True, True),
    ("a named weld group", False, True, False),
    ("an unnamed weld group", False, False, True),
)
MEMBERSHIP_KEYS = ("any_editor", "named_editor", "unnamed_editor", "any_weld", "named_weld", "unnamed_weld")  # Saved


class GroupMembershipFilter(BaseFilter):
    """Whether a brick is in a group at all, unlike EditorGroupFilter / WeldGroupFilter which look for one group"""

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode, membership: int = 0):
        super().__init__(mw)
        self.mode = mode

        self.add_title_row(f"{mode.get_naming_tuple()[0]} be in", GROUP_NAMING_TOOLTIP)
        self.combo_box = self.make_combo_box([name for name, *_ in MEMBERSHIPS], membership)
        self.combo_box.item_changed.connect(self.emit_edited)
        self.master_layout.addWidget(self.combo_box)


    CONFIG_TYPE = "group_membership"

    def get_config(self) -> dict:
        return {"membership": MEMBERSHIP_KEYS[max(self.combo_box.get_current_idx(), 0)]}

    def apply_config(self, config: ConfigReader) -> None:
        key = config.get_choice("membership", MEMBERSHIP_KEYS, MEMBERSHIP_KEYS[0])
        self.combo_box.set_current_idx(MEMBERSHIP_KEYS.index(key))

    def is_allowed(self, brick: Brick) -> FilterResult:
        vehicle_data = self.get_vehicle_data()
        idx = max(self.combo_box.get_current_idx(), 0)
        _, editor, named_ok, unnamed_ok = MEMBERSHIPS[idx]

        group = brick.ref.editor if editor else brick.ref.weld
        if group is None or vehicle_data is None:
            return self.mode.filter_did_not_match()

        named = group in (vehicle_data.editor_be_to_bei if editor else vehicle_data.weld_be_to_bei)
        match = named_ok if named else unnamed_ok
        return self.mode.filter_matched() if match else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} be in a group (...)"

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return GroupMembershipFilter(mw, mode)
