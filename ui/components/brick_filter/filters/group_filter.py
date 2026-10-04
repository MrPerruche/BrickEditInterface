from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QComboBox

from ui.widgets import Label, ComboBox
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.models import TooltipContents
from systems.bei_files import ConfigReader

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


GROUP_NAMING_TOOLTIP = TooltipContents("You can name any group (weld or editor) by creating a text brick (any type) and setting the text to\n<code>bei#&lt;my group name&gt;</code>")


class BaseGroupFilter(BaseFilter):

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode):
        super().__init__(mw)
        self.mode = mode
        self.wanted_group: str | None = None  # Last group picked. Kept listed if a reloaded vehicle doesn't have it

        self.label_layout = QHBoxLayout()
        self.label_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.label_layout)

        self.label = Label(f"{mode.get_naming_tuple()[0]} be in {self.group_name()} group")
        self.label.set_tooltip(GROUP_NAMING_TOOLTIP)
        self.label_layout.addWidget(self.label, stretch=1)

        self.label_layout.addWidget(self.remove_filter_button)

        self.combo_box = ComboBox(tint_icons=True)
        self.combo_box.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Fixed
        )
        self.combo_box.qt_widget.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.master_layout.addWidget(self.combo_box)

        self.on_vehicle_reload()  # Populate combo box
        self.combo_box.item_changed.connect(self._on_group_selected)


    def _on_group_selected(self, *_):
        self.wanted_group = self.combo_box.get_current_text() or None
        self.emit_edited()


    def on_vehicle_reload(self):
        # print("on_vehicle_reload called")
        previous_selection = self.wanted_group or self.combo_box.get_current_text()

        # Repopulating is not an edit from the user
        self.combo_box.qt_widget.blockSignals(True)
        try:
            self.combo_box.clear_items()

            vehicle_data = self.mw.vehicle_selector_banner.get_brvfile_ref_data()
            names = []
            if vehicle_data is not None:
                groups = vehicle_data.editor_groups if self.group_name() == "editor" else vehicle_data.weld_groups
                names = list(groups.keys())
            if self.wanted_group is not None and self.wanted_group not in names:
                names.append(self.wanted_group)  # Matches nothing, but doesn't silently switch to another group
            for group_name in names:
                self.combo_box.add_item(group_name)

            if previous_selection:
                idx = self.combo_box.qt_widget.findText(previous_selection)
                if idx != -1:
                    self.combo_box.set_current_idx(idx)
        finally:
            self.combo_box.qt_widget.blockSignals(False)


    def get_config(self) -> dict:
        group = self.combo_box.get_current_text()
        return {"group": group} if group else {}

    def apply_config(self, config: ConfigReader) -> None:
        group = config.get_str("group")
        if group:
            self.wanted_group = group
            self.on_vehicle_reload()
            self.emit_edited()


    def is_allowed(self, brick: Brick) -> FilterResult:
        raise NotImplementedError(f"Method is_allowed not implemented by {self.__class__.__name__}")

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        raise NotImplementedError(f"Method get_filter_name not implemented by {cls.__name__}")

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return GROUP_NAMING_TOOLTIP

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        raise NotImplementedError(f"Method new not implemented by {cls.__name__}")

    @staticmethod
    def group_name():
        raise NotImplementedError()



class EditorGroupFilter(BaseGroupFilter):

    CONFIG_TYPE = "editor_group"

    def is_allowed(self, brick: Brick) -> FilterResult:

        vehicle_data = self.get_vehicle_data()
        if vehicle_data is None:
            return self.mode.filter_did_not_match()
        target_group = self.combo_box.get_current_text()

        brick_group = vehicle_data.editor_be_to_bei.get(brick.ref.editor, None)

        match = brick_group is not None and target_group == brick_group
        return self.mode.filter_matched() if match else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} be in editor group (...)"

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return EditorGroupFilter(mw, mode)

    @staticmethod
    def group_name():
        return "editor"


class WeldGroupFilter(BaseGroupFilter):

    CONFIG_TYPE = "weld_group"

    def is_allowed(self, brick: Brick) -> FilterResult:

        vehicle_data = self.get_vehicle_data()
        if vehicle_data is None:
            return self.mode.filter_did_not_match()
        target_group = self.combo_box.get_current_text()

        brick_group = vehicle_data.weld_be_to_bei.get(brick.ref.weld, None)

        match = brick_group is not None and target_group == brick_group
        return self.mode.filter_matched() if match else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"{mode.get_naming_tuple()[0]} be in weld group (...)"

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return WeldGroupFilter(mw, mode)

    @staticmethod
    def group_name():
        return "weld"
