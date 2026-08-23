"""
editor.py -- GradientBar plus the surrounding controls.

Drop-in replacement for menus/shared_widgets/multi_color_selector.py's
MultiColorSelectorWidget: get_colors_pos() / get_colors() return the exact
same shape, so menus/gradient_maker/gradient_maker.py's create_vehicle()
needs no changes to keep working. current_space() / current_long_hue()
give you what that file's own color-space radio buttons + "longer hue"
checkbox used to -- you can likely delete those and call this instead.

Every widget built in *this* file comes from ui.widgets (Label, ComboBox,
Button, ToolButton, NumberChannelEdit) -- nothing here is a raw QLabel /
QComboBox / QPushButton. The only two exceptions are GradientBar and
ColorSwatchButton, imported from bar.py, which are custom-painted widgets
with no wrapper equivalent (see bar.py's docstring). That's the entire
"raw Qt inventory" for this folder -- everything else is your components.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from .bar import ColorSwatchButton, GradientBar
from .color_math import ColorSpace, ColorStop, DEFAULT_SPACES

from ui.widgets import Button, ChannelMode, ComboBox, Label, NumberChannelEdit, ToolButton
from ui.widgets import Widget as _BaseWidget
from ui.models import TooltipContents


_LONGER_HUE_TOOLTIP = TooltipContents(
    "Interpolates the long way around the hue wheel instead of the short "
    "way. Only affects OKLCH and HSV.",
)


class GradientEditor(_BaseWidget):
    """GradientBar plus a color-space combo, a "longer hue" toggle, and a
    selected-stop detail row (swatch, position field, add/remove)."""

    stopsChanged = Signal()  # forwarded straight from GradientBar.stopsChanged

    def __init__(self, stops: Optional[list[ColorStop]] = None,
                 spaces: list[ColorSpace] = DEFAULT_SPACES, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # -- color space + longer-hue row -- #
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_row.addWidget(Label("Interpolation:"))

        self._spaces = spaces
        self.space_combo = ComboBox()
        for sp in spaces:
            self.space_combo.add_item(sp.label)
        mode_row.addWidget(self.space_combo, 1)

        self.longer_hue_button = Button("Longer hue")
        self.longer_hue_button.set_checkable(True)
        self.longer_hue_button.set_tooltip(_LONGER_HUE_TOOLTIP)
        mode_row.addWidget(self.longer_hue_button)

        root.addLayout(mode_row)

        # -- the bar -- #
        self.bar = GradientBar(stops=stops, parent=self)
        root.addWidget(self.bar)

        # -- selected stop detail row -- #
        detail_row = QHBoxLayout()
        detail_row.setSpacing(6)

        self.swatch = ColorSwatchButton(parent=self)
        detail_row.addWidget(self.swatch)

        self.position_edit = NumberChannelEdit(mode=ChannelMode.FLOAT64, decimals=2, minimum=0.0, maximum=100.0, allow_nan=False, allow_inf=False)
        detail_row.addWidget(self.position_edit, 1)

        self.add_button = ToolButton()
        self.add_button.set_icon_from_theme("list-add")
        detail_row.addWidget(self.add_button)

        self.remove_button = ToolButton()
        self.remove_button.set_icon_from_theme("edit-delete")
        detail_row.addWidget(self.remove_button)

        root.addLayout(detail_row)

        # -- wiring -- #
        self._syncing = False
        self.space_combo.item_changed.connect(self._on_space_combo_changed)
        self.longer_hue_button.toggled.connect(self._on_long_hue_toggled)
        self.swatch.clicked.connect(self._on_swatch_clicked)
        self.position_edit.value_changed.connect(self._on_position_changed)
        self.add_button.clicked.connect(lambda: self.bar.add_stop())
        self.remove_button.clicked.connect(self.bar.remove_selected)
        self.bar.selectionChanged.connect(self._on_selection_changed)
        self.bar.stopsChanged.connect(self.stopsChanged.emit)

        self.space_combo.set_current_idx(0)
        self._on_space_combo_changed(0)
        self._on_selection_changed(self.bar.selected_stop())

    # -- forwarded data API (matches the old MultiColorSelectorWidget) -- #

    def get_colors_pos(self) -> list[tuple]:
        return self.bar.get_colors_pos()

    def get_colors(self) -> list:
        return self.bar.get_colors()

    def get_color_at_pos(self, pos: float):
        return self.bar.get_color_at_pos(pos)

    def set_colors_pos(self, values: list[tuple]) -> None:
        self.bar.set_colors_pos(values)

    def current_space(self) -> ColorSpace:
        return self.bar.space()

    def current_long_hue(self) -> bool:
        return self.bar.long_hue()

    # -- internal wiring -- #

    def _on_space_combo_changed(self, index: int) -> None:
        space = self._spaces[index]
        self.bar.set_space(space)
        self.longer_hue_button.set_enabled(space.hue_capable)
        if not space.hue_capable:
            self.longer_hue_button.set_checked(False)
            self.bar.set_long_hue(False)

    def _on_long_hue_toggled(self, checked: bool) -> None:
        self.bar.set_long_hue(checked)

    def _on_selection_changed(self, stop: Optional[ColorStop]) -> None:
        self._syncing = True
        has_stop = stop is not None
        self.swatch.setEnabled(has_stop)
        self.position_edit.set_enabled(has_stop)
        self.remove_button.set_enabled(has_stop and self.bar.stop_count() > GradientBar.MIN_STOPS)
        if has_stop:
            self.swatch.set_color(stop.color)
            self.position_edit.setValue(stop.position)
        self._syncing = False

    def _on_swatch_clicked(self) -> None:
        stop = self.bar.selected_stop()
        if stop is None:
            return
        self.bar.edit_stop_color(stop)
        self.swatch.set_color(stop.color)

    def _on_position_changed(self, value) -> None:
        if self._syncing:
            return
        stop = self.bar.selected_stop()
        if stop is not None:
            self.bar.set_stop_position(stop, float(value))
