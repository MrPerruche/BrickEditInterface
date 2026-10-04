from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal

from ui.widgets import Widget, StyledLabel, LabelStyle
from ui.components.brick.property_widgets import BasePropertyWidget, get_property_widget, Vec3PropertyWidget
from ui.components.brick.property_utils import get_or_make_property_display_name

from utils import wipe_layout

from collections import defaultdict

from typing import Hashable, TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.brick_filter.brick_selector import BrickSelector

import brickedit


class FormulaApplyError(Exception):
    """A property's formula could not produce a valid value for one of the bricks it applies to.
    This is a user input problem (eg. 1/(x-1) when x is 1, or a result out of range), not a bug:
    the message is meant to be shown to the user as is."""

    def __init__(self, property_display_name: str, brick: brickedit.Brick, input_value: str, reason: str):
        self.property_display_name = property_display_name
        self.input_value = input_value
        self.reason = reason
        super().__init__(
            f"The formula for \"{property_display_name}\" could not be applied to brick "
            f"{get_or_make_property_display_name(brick.meta().name())} (current value: {input_value}). "
            "Nothing was saved.\n"
            f"{reason}"
        )


POSITION_KEY = "@position"  # Keys of the position and rotation edits (see get_edits), unlike any property name
ROTATION_KEY = "@rotation"


def _make_pos_or_rot_widget(title: str, value_set: set[brickedit.Vec3], formula_mode: bool = False):
    if len(value_set) < 1:
        return Vec3PropertyWidget(title, (brickedit.Vec3(0, 0, 0),), formula_mode, brickedit.Vec3(0, 0, 0))
    return Vec3PropertyWidget(title, tuple(value_set), formula_mode or len(value_set) > 1, next(iter(value_set)))


class PropertySet(Widget):

    properties_edited = Signal()

    def __init__(
        self, bs: 'BrickSelector', properties: dict[str, set], frozen_properties: set[str],
        positions: set[brickedit.Vec3], rotations: set[brickedit.Vec3], formula_properties: set[str] = frozenset()
        ):
        """formula_properties: properties (or POSITION_KEY / ROTATION_KEY) shown in formula mode even if every brick
        has the same value, eg. to apply formula edits (see apply_edits)."""

        super().__init__()

        self.bs = bs
        self.edited = False
        self.formula_properties = formula_properties

        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.brick_title = StyledLabel("", LabelStyle.HEADER_5, True)
        self.master_layout.addWidget(self.brick_title)

        self.properties_layout = QVBoxLayout()
        self.properties_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.properties_layout)

        self.property_widgets = []
        self.pos_widget = None
        self.rot_widget = None

        self.failed_properties = set()
        self.set_property_set(properties, frozen_properties, positions, rotations)


    def on_property_edited(self):
        self.edited = True
        self.properties_edited.emit()


    def set_property_set(self, properties: dict[str, set], frozen_properties: set[str],
    positions: set[brickedit.Vec3], rotations: set[brickedit.Vec3]
    ):
        self.setUpdatesEnabled(False)

        try:
            self.property_widgets = []
            wipe_layout(self.properties_layout)

            sorted_properties: list[tuple[str, set]] = sorted([(k, v) for k, v in properties.items()], key=lambda x: x[0])

            self.failed_properties = set()

            # Brick's position
            self.pos_widget = _make_pos_or_rot_widget("Position", positions, POSITION_KEY in self.formula_properties)
            self.pos_widget.value_changed.connect(self.on_property_edited)
            self.properties_layout.addWidget(self.pos_widget)

            # Brick's rotation
            self.rot_widget = _make_pos_or_rot_widget("Rotation", rotations, ROTATION_KEY in self.formula_properties)
            self.rot_widget.value_changed.connect(self.on_property_edited)
            self.properties_layout.addWidget(self.rot_widget)

            for (prop, values) in sorted_properties:

                formula_mode = len(values) > 1 or prop in self.formula_properties
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


    # --- Edits as data (see property_edits)

    def widgets_by_key(self) -> dict[str, BasePropertyWidget]:
        """Property name (or POSITION_KEY / ROTATION_KEY) -> its widget"""
        widgets: dict[str, BasePropertyWidget] = {}
        if self.pos_widget is not None and self.rot_widget is not None:
            widgets |= {POSITION_KEY: self.pos_widget, ROTATION_KEY: self.rot_widget}
        return widgets | {widget.get_property(): widget for widget in self.property_widgets}

    def get_edits(self) -> dict[str, dict]:
        """Property name (or POSITION_KEY / ROTATION_KEY) -> edit, for every widget which changes something"""
        return {key: edit for key, widget in self.widgets_by_key().items() if (edit := widget.get_edit()) is not None}

    def apply_edits(self, edits: dict[str, dict]) -> dict[str, str]:
        """Shows edits (from get_edits, maybe of another selection) in the widgets. Edits needing formula mode must
        be in formula_properties. Edits of properties without a widget are ignored. Returns the edits which couldn't
        be applied: key -> why."""
        widgets = self.widgets_by_key()
        failed = {}
        for key, edit in edits.items():
            if key not in widgets:
                continue
            try:
                widgets[key].apply_edit(edit)
                self.edited = True
            except ValueError as e:
                failed[key] = str(e)
        return failed


    @staticmethod
    def _evaluate(pw: BasePropertyWidget, brick: brickedit.Brick, default_value):
        try:
            return pw.get_value(default_value)
        except ValueError as e:  # Formula channels raise ValueError for anything the user wrote wrong
            raise FormulaApplyError(get_or_make_property_display_name(pw.get_property()), brick,
                                    pw.format_value(default_value), str(e)) from e


    def update_bricks(self, bricks: list[brickedit.Brick]):
        """Note: Edits are applied through mutability.

        Raises FormulaApplyError if a formula fails for any brick. Bricks may then be partially
        edited, so only call this on a copy that is discarded on failure."""

        cache: dict[str, dict[Hashable, Hashable | None]] = defaultdict(dict)

        assert self.pos_widget is not None and self.rot_widget is not None, "Widgets are None! PropertySet.update_bricks is called before PropertySet is properly initialized."

        for brick in bricks:

            # Brick's transform. Once per brick: formulas like x+1 must not stack.
            if self.rot_widget.is_dirty():
                brick.rot = self._evaluate(self.rot_widget, brick, brick.rot)
            if self.pos_widget.is_dirty():
                brick.pos = self._evaluate(self.pos_widget, brick, brick.pos)

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
                    new_value = self._evaluate(pw, brick, default_value)
                    if pw.is_cachable():
                        cache[pw_prop][default_value] = new_value

                brick.set_property(pw_prop, new_value)

        # print(bricks, len(self.property_widgets))
