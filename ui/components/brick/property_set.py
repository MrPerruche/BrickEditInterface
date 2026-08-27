from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Signal

from ui.widgets import Widget
from ui.components.brick.property_widgets import BasePropertyWidget, get_property_widget

from utils import wipe_layout

from collections import defaultdict

from typing import Hashable, TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.brick_filter.brick_selector import BrickSelector

import brickedit



class PropertySet(Widget):

    properties_edited = Signal()

    def __init__(self, bs: 'BrickSelector', properties: dict[str, set], frozen_properties: set[str]):
        super().__init__()

        self.bs = bs

        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.properties_layout = QVBoxLayout()
        self.properties_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.properties_layout)

        self.property_widgets = []

        self.failed_properties = set()
        self.set_property_set(properties, frozen_properties)


    def on_property_edited(self):
        self.properties_edited.emit()


    def set_property_set(self, properties: dict[str, set], frozen_properties: set[str]):
        self.setUpdatesEnabled(False)

        try:
            self.property_widgets = []
            wipe_layout(self.properties_layout)

            sorted_properties: list[tuple[str, set]] = sorted([(k, v) for k, v in properties.items()], key=lambda x: x[0])

            self.failed_properties = set()

            for (prop, values) in sorted_properties:

                formula_mode = len(values) > 1
                if len(values) == 0:
                    continue

                widget = get_property_widget(prop, values, formula_mode, None if formula_mode else next(iter(values)), show_text=True)
                if widget is None:
                    self.failed_properties.add(prop)
                    continue
                if prop in frozen_properties:
                    widget.set_enabled(False)
                widget.value_changed.connect(self.on_property_edited)

                self.property_widgets.append(widget)
                self.properties_layout.addWidget(widget)

        finally:
            self.setUpdatesEnabled(True)

        return self.failed_properties



    def update_bricks(self, bricks: list[brickedit.Brick]):
        """Note: Edits are applied through mutability"""

        cache: dict[str, dict[Hashable, Hashable | None]] = defaultdict(dict)

        for brick in bricks:
            for pw in self.property_widgets:

                if not pw.is_dirty():
                    # print(f"{pw.get_property()} not dirty")
                    continue
                pw_prop: str = pw.get_property()
                # print(pw_prop)

                try:
                    default_value: Hashable = brick.get_property(pw_prop)
                except brickedit.BrickError:
                    # print("brickerror")
                    continue

                if pw.is_cachable() and default_value in cache[pw_prop]:
                    new_value = cache[pw_prop][default_value]
                else:
                    new_value = pw.get_value(default_value)
                    if pw.is_cachable():
                        cache[pw_prop][default_value] = new_value

                brick.set_property(pw_prop, new_value)

        # print(bricks, len(self.property_widgets))
