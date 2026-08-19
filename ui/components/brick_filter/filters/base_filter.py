from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from ui.widgets import Widget, Surface, ToolButton
from ui.models import TooltipContents

from enum import Enum

from brickedit import Brick

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


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
