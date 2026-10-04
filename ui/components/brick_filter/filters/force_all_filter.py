from PySide6.QtWidgets import QHBoxLayout

from ui.widgets import Label
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, FilterTarget, BaseFilter
from ui.models import TooltipContents

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class ForceAllFilter(BaseFilter):

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode):

        super().__init__(mw)
        self.mode = mode

        self.hlayout = QHBoxLayout()
        self.master_layout.addLayout(self.hlayout)

        self.label = Label("Ignore all filters and include")
        self.hlayout.addWidget(self.label, stretch=1)

        self.hlayout.addWidget(self.remove_filter_button)


    CONFIG_TYPE = "force_all"

    def is_allowed(self, brick: 'brickedit.Brick') -> FilterResult:
        return FilterResult.FORCE_ALLOWED

    @classmethod
    def get_filter_name(cls, mode: FilterMode) -> str:
        return f"Ignore all filters and include"

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return TooltipContents("All bricks are included. Ignores vetoes. If this filter is present, no other filter will have any effect.")

    @classmethod
    def get_filter_target(cls):
        return FilterTarget.ALLOW_NONE_IF_EMPTY_ONLY

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return ForceAllFilter(mw, mode)

