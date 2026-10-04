from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt

from ui.widgets import Widget, Label, ComboBox
from ui.theme import Theme, register_has_theme_and_apply
from ui.components.brick_filter.filters import *
from ui.models import TooltipContents

from ui.components.brick_filter.filter_selector_entry import FilterEntry

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.brick_filter.brick_selector import BrickSelector
    from mainwindow import BrickEditInterface



FILTER_MODE_TOOLTIP = TooltipContents(text="""\
Filters can have 2 different modes:
<ul>
  <li>Should: Matching bricks are included, unless another filter removes them.</li>
  <li>Must: Bricks must match this filter, or they are removed.</li>
</ul>
Filters can be negated (Should/Must not), in which case bricks match this filter if the condition is not met.\
""")

OR_FILTER = "Should", "should"
NOR_FILTER = "Should not", "should not"
AND_FILTER = "Must", "must"
NAND_FILTER = "Must not", "must not"


class FilterSelector(Widget):

    WIDTH = 250

    def __init__(self, mw: 'BrickEditInterface', brick_selector: 'BrickSelector', parent=None):
        super().__init__(parent)
        self.mw = mw

        self.setProperty("filter_selector", True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setWindowFlags(Qt.Popup)

        self.setFixedWidth(self.WIDTH)

        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(12, 12, 12, 12)
        self.setLayout(self.master_layout)

        self.brick_selector = brick_selector

        # Filter mode
        self.filter_mode_layout = QHBoxLayout()
        self.filter_mode_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.filter_mode_layout)

        self.filter_mode_label = Label("Mode")
        self.filter_mode_label.set_tooltip(FILTER_MODE_TOOLTIP)
        self.filter_mode_layout.addWidget(self.filter_mode_label)

        self.filter_mode_combo_box = ComboBox()
        self.filter_mode_combo_box.add_item(OR_FILTER[0])
        self.filter_mode_combo_box.add_item(NOR_FILTER[0])
        self.filter_mode_combo_box.add_item(AND_FILTER[0])
        self.filter_mode_combo_box.add_item(NAND_FILTER[0])
        self.filter_mode_layout.addWidget(self.filter_mode_combo_box)

        # Own layout so the entries can be packed tight without squashing the mode row (2 px keeps the bordered
        #  buttons apart)
        self.entries_layout = QVBoxLayout()
        self.entries_layout.setContentsMargins(0, 0, 0, 0)
        self.entries_layout.setSpacing(6)
        self.master_layout.addLayout(self.entries_layout)

        self.filter_entries: list[FilterEntry] = []
        for filter_cls in filter_classes:

            # Filter targets our brick selector? If not, then they're incompatible. Must not be included.
            if not filter_cls.get_filter_target().target_matches(self.brick_selector.allow_all_if_empty):
                continue

            filter_entry = FilterEntry(self.mw, self, filter_cls)
            self.filter_entries.append(filter_entry)
            self.entries_layout.addWidget(filter_entry)
            filter_entry.filter_selected.connect(self.entry_adds_filter)

        self.filter_mode_combo_box.item_changed.connect(self.update_modes)
        register_has_theme_and_apply(self)


    def entry_adds_filter(self, entry: FilterEntry):
        self.brick_selector.add_filter(entry.filter_class.new(self.mw, self.get_mode()))
        self.hide()


    def get_mode(self) -> FilterMode:
        return {
            OR_FILTER[0]: FilterMode.SHOULD,
            NOR_FILTER[0]: FilterMode.SHOULD_NOT,
            AND_FILTER[0]: FilterMode.MUST,
            NAND_FILTER[0]: FilterMode.MUST_NOT,
        }[self.filter_mode_combo_box.get_current_text()]


    def update_modes(self):
        for filter_entry in self.filter_entries:
            filter_entry.update_mode()


    def _apply_theme(self, theme: Theme):
        self.setStyleSheet(f"""
            *[filter_selector] {{
                background-color: {theme.background.color};

                border: 2px solid {theme.border.color};
                border-radius: 4px;
            }}
        """)
