from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QBoxLayout, QWidget, QSizePolicy, QComboBox
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from ui.widgets import Widget, Surface, ToolButton, Label, ComboBox
from ui.models import TooltipContents

from enum import Enum

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface
    from ui.components.vehicle.vehicle_data import VehicleData
    from systems.bei_files import ConfigReader


class FilterResult(Enum):
    VETOED = 0         # Brick is denied by a filter
    IGNORE = 1         # Brick is not allowed by a filter but may be allowed by other filters
    ALLOWED = 2        # Brick is included unless vetoed
    FORCE_ALLOWED = 3  # Ignores all vetoes.


class FilterMode(Enum):
    SHOULD = 0
    SHOULD_NOT = 1
    MUST = 2
    MUST_NOT = 3

    def get_naming_tuple(self) -> tuple[str, str]:
        return {
            FilterMode.SHOULD: ("Should", "should"),
            FilterMode.SHOULD_NOT: ("Shouldn't", "shouldn't"),
            FilterMode.MUST: ("Must", "must"),
            FilterMode.MUST_NOT: ("Must not", "must not"),
        }[self]

    def filter_matched(self) -> FilterResult:
        # If positive, then matching allows
        if self in (FilterMode.SHOULD, FilterMode.MUST):
            return FilterResult.ALLOWED
        # If of type should then tolerate, else veto
        return FilterResult.IGNORE if self == FilterMode.SHOULD_NOT else FilterResult.VETOED

    def filter_did_not_match(self) -> FilterResult:
        # If negative, then matching allows
        if self in (FilterMode.SHOULD_NOT, FilterMode.MUST_NOT):
            return FilterResult.ALLOWED
        # If of type should then tolerate, else veto
        return FilterResult.IGNORE if self == FilterMode.SHOULD else FilterResult.VETOED


class FilterTarget(Enum):
    """Defines in which brick selector types a filter can be applied. All brick selectors, only those whose allow_all_if_empty = True, or = False."""
    ALL_BRICK_SELECTORS = 0
    ALLOW_ALL_IF_EMPTY_ONLY = 1
    ALLOW_NONE_IF_EMPTY_ONLY = 2

    def target_matches(self, allow_all_if_empty: bool):
        return self == self.ALL_BRICK_SELECTORS or (self == self.ALLOW_NONE_IF_EMPTY_ONLY) ^ allow_all_if_empty



class BaseFilter(Widget):
    
    remove_requested = Signal(object)
    filter_edited = Signal(object)

    def __init__(self, mw: 'BrickEditInterface'):
        super().__init__()
        self.mw = mw

        self.true_master_layout = QVBoxLayout()
        self.true_master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.true_master_layout)

        self.surface = Surface(highlight=False)
        self.true_master_layout.addWidget(self.surface)
        self.master_layout = self.surface.layout()

        self.remove_filter_button = ToolButton(QIcon.fromTheme("edit-delete"), tint_icon=True)
        self.remove_filter_button.clicked.connect(self.request_remove)
        # Filter's job to add this button somewhere

        mw.vehicle_selector_banner.vehicle_loaded.connect(self.on_vehicle_reload)


    # Layout helpers

    LABEL_STRETCH = 4
    WIDGET_STRETCH = 11

    def add_title_row(self, text: str, tooltip: TooltipContents | None = None) -> Label:
        """Adds the filter's description followed by the remove button"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(layout)

        label = Label(text)
        if tooltip is not None:
            label.set_tooltip(tooltip)
        layout.addWidget(label, stretch=1)
        layout.addWidget(self.remove_filter_button)
        return label

    def add_setting_row(self, text: str, widget: QWidget, tooltip: TooltipContents | None = None,
                        layout: QBoxLayout | None = None, label_stretch: int | None = None) -> Widget:
        """Adds a "label | widget" row to layout (default: the filter's). Returns the row, which can be hidden.
        label_stretch: share of the label against WIDGET_STRETCH (default: LABEL_STRETCH), eg. for long labels."""
        row = Widget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label = Label(text)
        if tooltip is not None:
            label.set_tooltip(tooltip)
        row_layout.addWidget(label, stretch=self.LABEL_STRETCH if label_stretch is None else label_stretch)
        row_layout.addWidget(widget, stretch=self.WIDGET_STRETCH)

        (self.master_layout if layout is None else layout).addWidget(row)
        return row

    @staticmethod
    def make_combo_box(items: list[str] = (), idx: int = 0) -> ComboBox:
        """Combo box which doesn't widen the filter to fit its longest item"""
        combo_box = ComboBox(tint_icons=True)
        combo_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        combo_box.qt_widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for item in items:
            combo_box.add_item(item)
        if items:
            combo_box.set_current_idx(idx)
        return combo_box

    def emit_edited(self, *_):
        self.filter_edited.emit(self)

    def get_vehicle_data(self) -> 'VehicleData | None':
        """Data of the loaded vehicle (the one being filtered), if any"""
        return self.mw.vehicle_selector_banner.get_brvfile_ref_data()


    # Saving (rule presets, see systems.bei_files)

    CONFIG_TYPE: str | None = None
    """Stable id of the filter in saved files. None: can't be saved. Never change it once released."""

    def get_config(self) -> dict:
        """The filter's settings, TOML compatible. The mode is saved by the caller."""
        return {}

    def apply_config(self, config: 'ConfigReader') -> None:
        """Restores settings saved by get_config. Raises BeiFileError if a value is invalid."""


    def request_remove(self):
        self.remove_requested.emit(self)

    def on_vehicle_reload(self):
        pass

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return None

    def is_allowed(self, brick: Brick) -> FilterResult:
        raise NotImplementedError(f"Method is_allowed not implemented by {self.__class__.__name__}")

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        raise NotImplementedError(f"Method get_filter_name not implemented by {cls.__name__}")

    @classmethod
    def get_filter_target(cls):
        return FilterTarget.ALL_BRICK_SELECTORS

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        raise NotImplementedError(f"Method new not implemented by {cls.__name__}")
