from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import Qt

from collections import Counter

from ui.widgets import Button, Label, StyledLabel, LabelStyle, Surface
from ui.components.brick.property_utils import get_or_make_property_display_name

from menus.rule_based_editor.actions import plural

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.vehicle.vehicle_data import VehicleData


LISTED_BRICKS_LIMIT = 200
LISTED_TYPES_LIMIT = 6


class SelectionPreview(Surface):
    """How many bricks (and which) match the conditions."""

    def __init__(self):
        super().__init__()
        self.bricks: list[brickedit.Brick] = []
        self.vehicle_data: 'VehicleData | None' = None
        layout = self.layout()

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        header.addWidget(StyledLabel("Selection", LabelStyle.LARGE_5), stretch=1)
        self.show_list_button = Button("Show bricks")
        self.show_list_button.set_checkable(True)
        self.show_list_button.toggled.connect(self._update_list)
        header.addWidget(self.show_list_button)

        self.count_label = Label("")
        layout.addWidget(self.count_label)

        self.types_label = Label("", muted=True)
        self.types_label.set_font_size(11)
        layout.addWidget(self.types_label)

        self.list_label = Label("", muted=True)
        self.list_label.set_font_size(11)
        self.list_label.qt_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.list_label)
        self.list_label.hide()

    def set_message(self, text: str):
        self.bricks, self.vehicle_data = [], None
        self.count_label.set_text(text)
        self.types_label.hide()
        self._update_list()

    def set_selection(self, bricks: list[brickedit.Brick], vehicle_data: 'VehicleData'):
        self.bricks, self.vehicle_data = bricks, vehicle_data
        self.count_label.set_text(f"{len(bricks):,} of {plural(len(vehicle_data.brvfile.bricks))} selected.")

        types = Counter(get_or_make_property_display_name(brick.meta().name()) for brick in bricks)
        shown = [f"{name} ×{count:,}" for name, count in types.most_common(LISTED_TYPES_LIMIT)]
        if len(types) > LISTED_TYPES_LIMIT:
            shown.append(f"{len(types) - LISTED_TYPES_LIMIT:,} other types")
        self.types_label.set_text(" · ".join(shown))
        self.types_label.setVisible(bool(shown))
        self._update_list()

    def _update_list(self, *_):
        shown = self.show_list_button.qt_widget.isChecked() and bool(self.bricks)
        self.list_label.setVisible(shown)
        if not shown:
            return
        lines = []
        for brick in self.bricks[:LISTED_BRICKS_LIMIT]:
            index = self.vehicle_data.brick_indices.get(brick.ref.id, -1) if self.vehicle_data is not None else -1
            x, y, z = brick.pos.as_tuple()
            lines.append(f"#{index}  {get_or_make_property_display_name(brick.meta().name())}  ({x:g}, {y:g}, {z:g})")
        if len(self.bricks) > LISTED_BRICKS_LIMIT:
            lines.append(f"... and {plural(len(self.bricks) - LISTED_BRICKS_LIMIT)} more")
        self.list_label.set_text("\n".join(lines))
