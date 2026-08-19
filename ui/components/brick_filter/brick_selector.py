from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from enum import Enum

from ui.widgets import Widget, Surface, Button, Label
from ui.components.brick_filter.filter_selector import FilterSelector
from ui.components.brick_filter.filters import FilterMode, FilterResult, BaseFilter, ColorFilter

from utils import wipe_layout

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


ADD_BTN_ICON = QIcon.fromTheme("list-add")
NO_FILTERS_LABEL_ALLOW_ALL_IF_EMPTY = "All bricks selected."
NO_FILTERS_LABEL = "No bricks selected."

class BrickSelector(Widget):


    filters_changed = Signal()


    def __init__(self, mw: 'BrickEditInterface', filters: list[BaseFilter] | None = None, allow_all_if_empty: bool = False, parent=None):
        """Brick selector widget
        filters=None will create 1 filter with a random color"""
        super().__init__(parent=parent)

        self.mw = mw
        self.allow_all_if_empty = allow_all_if_empty

        self.true_master_layout = QVBoxLayout()
        self.true_master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.true_master_layout)
        self.surface = Surface()
        # self.surface.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.true_master_layout.addWidget(self.surface)
        self.master_layout = self.surface.layout()

        # layout stuff

        self.add_btn_layout = QHBoxLayout()
        self.master_layout.addLayout(self.add_btn_layout)

        self.widget_name_label = Label("Brick filters")
        self.add_btn_layout.addWidget(self.widget_name_label)

        self.add_button = Button("Add a filter", icon=ADD_BTN_ICON, tint_icon=True)
        self.add_button.clicked.connect(self.open_filter_selector)
        self.add_btn_layout.addWidget(self.add_button)

        self.filter_selector = FilterSelector(mw, self, parent=self)

        self.no_filters_label = Label(NO_FILTERS_LABEL_ALLOW_ALL_IF_EMPTY if self.allow_all_if_empty else NO_FILTERS_LABEL)
        # self.no_filters_label.hide()
        self.master_layout.addWidget(self.no_filters_label)

        self.filters_layout = QVBoxLayout()
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.filters_layout)

        # filters
        self.filters = filters if filters is not None else [ColorFilter(mw, FilterMode.SHOULD)]
        self.set_filters(self.filters)


    def set_filters(self, filters: list[BaseFilter]):
        self.filters = filters
        wipe_layout(self.filters_layout)

        if filters:
            self.no_filters_label.hide()
        else:
            self.no_filters_label.show()

        for f in self.filters:
            self._add_filter_widget(f)

        self.filters_changed.emit()


    def add_filter(self, filter: BaseFilter):
        if not self.filters:
            self.no_filters_label.hide()

        self.filters.append(filter)
        self._add_filter_widget(filter)

        self.filters_changed.emit()


    def remove_filter(self, filter: BaseFilter):
        self.filters.remove(filter)
        filter.deleteLater()

        if not self.filters:
            self.no_filters_label.show()

        self.filters_changed.emit()


    def filter_changed(self, filter: BaseFilter):
        self.filters_changed.emit()


    def _add_filter_widget(self, filter: BaseFilter):
        filter.remove_requested.connect(self.remove_filter)
        self.filters_layout.addWidget(filter)


    def set_allow_all_if_empty(self, allow_all_if_empty: bool):
        self.allow_all_if_empty = allow_all_if_empty
        self.no_filters_label.set_text(NO_FILTERS_LABEL_ALLOW_ALL_IF_EMPTY if self.allow_all_if_empty else NO_FILTERS_LABEL)


    def is_allowed(self, brick: brickedit.Brick) -> bool:

        # Edge case: no filters
        if not self.filters:
            return self.allow_all_if_empty

        matches_one_filter = False
        has_been_vetoed = False
        for f in self.filters:

            filter_result = f.is_allowed(brick)

            # Brick force allowed -> ignore all vetoes. Will always be allowed.
            if filter_result == FilterResult.FORCE_ALLOWED:
                return True
            # Brick vetoed -> Do not allow unless a force allow is available
            if filter_result == FilterResult.VETOED:
                has_been_vetoed = True
            # Brick allowed -> matches at least one filter.
            elif filter_result == FilterResult.ALLOWED:
                matches_one_filter = True
            # Else ignored, go to next filter

        # True if any filter allowed otherwise false
        return matches_one_filter and not has_been_vetoed


    def get_frozen_properties(self) -> set[str]:
        return {brickedit.p.BRICK_COLOR} if any([isinstance(f, ColorFilter) for f in self.filters]) else set()


    def is_property_editable(self, property_name: str) -> bool:
        return property_name in self.get_frozen_properties()
        # return not (property_name == brickedit.p.BRICK_COLOR and any([isinstance(f, ColorFilter) for f in self.filters]))


    def open_filter_selector(self):
        pos = self.add_button.mapToGlobal(self.add_button.rect().bottomRight())
        pos.setX(pos.x() - FilterSelector.WIDTH)
        self.filter_selector.move(pos)
        self.filter_selector.show()
