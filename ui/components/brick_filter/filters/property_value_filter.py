from PySide6.QtWidgets import QVBoxLayout

from enum import Enum
from math import isfinite

from ui.widgets import Label, Switcher, NumberChannelEdit, ChannelMode
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.components.brick.property_utils import get_or_make_property_display_name
from ui.components.brick.property_widgets import (
    BasePropertyWidget, get_property_widget, get_property_widget_cls,
    TextPropertyWidget, AsciiPropertyWidget, BooleanPropertyWidget, FloatPropertyWidget, UnsignedInteger8PropertyWidget,
    Vec2PropertyWidget, Vec3PropertyWidget, ColorPropertyWidget,
)
from ui.components.brick.materials import MATERIAL_DISPLAY_NAMES
from ui.models import TooltipContents
from systems.bei_files import ConfigReader, BeiFileError, enum_key
from utils import wipe_layout

import brickedit
from brickedit import Brick

from typing import TYPE_CHECKING, Hashable
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class PropertyComparison(Enum):
    EQUALS = 0
    WITHIN = 1


COMPARISONS = ("equal to", "within")
PROPERTY_VALUE_TOOLTIP = TooltipContents(
    "Property value",
    "Equal to: the property must have exactly this value (decimal numbers are compared with float precision).\n"
    "Within: every component of the property must be between the minimum and the maximum (included). Only for "
    "numbers and vectors.\n"
    "Bricks which don't have the property never match. For anything more complex, use \"satisfy condition\"."
)
NUMBER_WIDGETS = (FloatPropertyWidget, UnsignedInteger8PropertyWidget)
VECTOR_WIDGETS = (Vec2PropertyWidget, Vec3PropertyWidget)


def _close(a: float, b: float) -> bool:
    """Equal within float32 precision (values in files are float32, values typed by users are not)"""
    return a == b or (isfinite(a) and isfinite(b) and abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b)))


def _float_components(value) -> tuple[float, ...] | None:
    """Components of decimal values (compared with float precision). None for anything else (compared exactly)"""
    if isinstance(value, brickedit.Vec2 | brickedit.Vec3):
        return value.as_tuple()
    if isinstance(value, float):
        return (value,)
    return None


def values_equal(a: Hashable, b: Hashable) -> bool:
    ca, cb = _float_components(a), _float_components(b)
    if ca is not None and cb is not None:
        return len(ca) == len(cb) and all(_close(x, y) for x, y in zip(ca, cb))
    return a == b


def _within(value: float, low: float, high: float) -> bool:
    if isinstance(value, float):
        return low <= value <= high or _close(value, low) or _close(value, high)
    return low <= value <= high


def enum_values(prop: str) -> list[str]:
    """Every value an enum property is known to take (constants of its brickedit class)"""
    meta_cls = brickedit.p.pmeta_registry.get(prop)
    if not isinstance(meta_cls, type):
        return []
    values = {getattr(meta_cls, name) for name in dir(meta_cls) if name.isupper()}
    return [v for v in values if isinstance(v, str)]


# ----- Saving values (rule presets)

def value_to_config(value):
    """TOML compatible form of a property value. None if it can't be saved."""
    if isinstance(value, brickedit.Vec2 | brickedit.Vec3):
        return list(value.as_tuple())
    if isinstance(value, bool | int | float | str):
        return value
    return None


def _is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and isfinite(value)


def value_from_config(raw, widget_cls: type[BasePropertyWidget], where: str):
    """Value of a property edited with widget_cls, from its value_to_config form. Raises BeiFileError."""
    if issubclass(widget_cls, TextPropertyWidget):  # Ascii (enums) included
        if isinstance(raw, str):
            return raw
        expected = "text"
    elif widget_cls is BooleanPropertyWidget:
        if isinstance(raw, bool):
            return raw
        expected = "true or false"
    elif widget_cls is FloatPropertyWidget:
        if _is_number(raw):
            return float(raw)
        expected = "a number"
    elif widget_cls in (UnsignedInteger8PropertyWidget, ColorPropertyWidget):
        maximum = 255 if widget_cls is UnsignedInteger8PropertyWidget else 0xFFFFFFFF
        if isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw <= maximum:
            return raw
        expected = f"an integer between 0 and {maximum}"
    elif widget_cls in VECTOR_WIDGETS:
        size = 3 if widget_cls is Vec3PropertyWidget else 2
        if isinstance(raw, list) and len(raw) == size and all(map(_is_number, raw)):
            return (brickedit.Vec3 if size == 3 else brickedit.Vec2)(*(float(c) for c in raw))
        expected = f"a list of {size} numbers"
    else:
        raise BeiFileError(f"{where}: values of this property can't be compared.")
    raise BeiFileError(f"{where}: the value must be {expected}.")


class PropertyValueFilter(BaseFilter):
    """A user friendly alternative to conditions such as prop('BrickMaterial') == 'Steel'."""

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode, prop: str | None = None,
                 comparison: PropertyComparison = PropertyComparison.EQUALS):
        super().__init__(mw)
        self.mode = mode
        self.properties: list[str] = []  # Internal names, in the combo box's order
        self.wanted_property = prop
        self._matcher = None  # value -> bool, or None if nothing can match
        self._value_config = dict  # () -> value settings to save, set by the _build_* methods

        self.add_title_row(f"Property", PROPERTY_VALUE_TOOLTIP)

        self.property_cb = self.make_combo_box()
        self.master_layout.addWidget(self.property_cb)

        self.comparison_sw = Switcher(list(COMPARISONS), comparison.value)
        self.add_setting_row(f"{mode.get_naming_tuple()[1]} be", self.comparison_sw, PROPERTY_VALUE_TOOLTIP, label_stretch=5)

        self.value_layout = QVBoxLayout()
        self.value_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.value_layout)

        self.on_vehicle_reload()
        self.property_cb.item_changed.connect(self._on_property_selected)
        self.comparison_sw.index_changed.connect(self._rebuild_value_widgets)


    # ----- Property list

    def on_vehicle_reload(self):  # Connected to a signal with an argument: must not take any
        self._refresh()

    def _refresh(self, initial: dict | None = None):
        """initial: value settings to start from (see apply_config), instead of a value found in the vehicle"""
        vehicle_data = self.get_vehicle_data()
        properties = set(vehicle_data.unique_properties) if vehicle_data is not None else set()
        if self.wanted_property is not None:
            properties.add(self.wanted_property)
        self.properties = sorted(properties, key=get_or_make_property_display_name)

        self.property_cb.qt_widget.blockSignals(True)
        try:
            self.property_cb.clear_items()
            for prop in self.properties:
                self.property_cb.add_item(get_or_make_property_display_name(prop))
            if self.wanted_property not in self.properties:
                self.wanted_property = self.properties[0] if self.properties else None
            if self.wanted_property is not None:
                self.property_cb.set_current_idx(self.properties.index(self.wanted_property))
        finally:
            self.property_cb.qt_widget.blockSignals(False)
        self._rebuild_value_widgets(initial=initial)

    def _on_property_selected(self, *_):
        idx = self.property_cb.get_current_idx()
        if 0 <= idx < len(self.properties) and self.properties[idx] != self.wanted_property:
            self.wanted_property = self.properties[idx]
            self._rebuild_value_widgets()

    def get_comparison(self) -> PropertyComparison:
        return PropertyComparison(self.comparison_sw.get_idx() or 0)


    # ----- Value widgets

    def _vehicle_values(self, prop: str, limit: int = 10_000) -> list:
        """Values of prop among the loaded vehicle's bricks (some of them)"""
        vehicle_data = self.get_vehicle_data()
        if vehicle_data is None:
            return []
        values = []
        for brick in vehicle_data.brvfile.bricks[:limit]:
            if prop in brick.ppatch or prop in brick.meta().p:
                values.append(brick.get_property(prop))
        return values

    def _rebuild_value_widgets(self, *_, initial: dict | None = None):
        """initial: {"value": v} or {"min": v, "max": v}, already converted (see apply_config)"""
        wipe_layout(self.value_layout)
        self._matcher = None
        self._value_config = dict
        initial = initial or {}
        prop = self.wanted_property
        if prop is not None:
            values = [v for v in self._vehicle_values(prop) if v is not None]
            sample = values[0] if values else None
            widget_cls = get_property_widget_cls(prop, allow_unknown=False)

            if self.get_comparison() == PropertyComparison.EQUALS:
                start = initial.get("value", sample)
                if widget_cls is AsciiPropertyWidget:
                    self._build_enum_equals(prop, values, initial.get("value"))
                elif widget_cls is not None and start is not None:
                    self._build_equals(prop, start)
                else:
                    self._unsupported("Comparing this property's value is not supported.")
            elif widget_cls in NUMBER_WIDGETS:
                self._build_number_range(widget_cls is UnsignedInteger8PropertyWidget, sample, initial)
            elif widget_cls in VECTOR_WIDGETS and (sample is not None or initial):
                self._build_vector_range(prop, sample if sample is not None else initial["min"], initial)
            else:
                self._unsupported("\"within\" cannot be used here.")
        self.emit_edited()

    def _unsupported(self, text: str):
        self.value_layout.addWidget(Label(text, muted=True))

    def _set_matcher(self, matcher):
        self._matcher = matcher
        self.emit_edited()

    def _build_equals(self, prop: str, sample):
        widget = get_property_widget(prop, (sample,), False, sample, show_text=False)
        if widget is None:
            self._unsupported("Comparing this property's value is not supported.")
            return
        self.value_layout.addWidget(widget)

        def update(*_):
            expected = widget.get_value(sample)
            self._value_config = lambda: {"value": value_to_config(expected)} if value_to_config(expected) is not None else {}
            self._set_matcher(lambda value: values_equal(value, expected))
        widget.value_changed.connect(update)
        update()

    def _build_enum_equals(self, prop: str, vehicle_values: list, initial: str | None):
        def display(value: str) -> str:
            return MATERIAL_DISPLAY_NAMES.get(value, get_or_make_property_display_name(value))
        known = set(enum_values(prop)) | {v for v in vehicle_values if isinstance(v, str)}
        if initial is not None:
            known.add(initial)  # Eg. a modded material
        options = sorted(known, key=display)
        combo = self.make_combo_box([display(v) for v in options])
        start = initial if initial is not None else vehicle_values[0] if vehicle_values else None
        if start in options:
            combo.set_current_idx(options.index(start))
        self.value_layout.addWidget(combo)

        def update(*_):
            idx = combo.get_current_idx()
            expected = options[idx] if 0 <= idx < len(options) else None
            self._value_config = lambda: {"value": expected} if expected is not None else {}
            self._set_matcher((lambda value: value == expected) if expected is not None else None)
        combo.item_changed.connect(update)
        update()

    def _build_number_range(self, integer: bool, sample, initial: dict):
        mode = ChannelMode.INT if integer else ChannelMode.FLOAT64
        low, high = NumberChannelEdit(mode, allow_nan=False), NumberChannelEdit(mode, allow_nan=False)
        start = sample if isinstance(sample, int | float) and not isinstance(sample, bool) else 0
        low.setValue(initial.get("min", start))
        high.setValue(initial.get("max", start))
        self.add_setting_row("Minimum", low, layout=self.value_layout)
        self.add_setting_row("Maximum", high, layout=self.value_layout)
        convert = int if integer else float

        def update(*_):
            lo, hi = convert(low.value()), convert(high.value())
            self._value_config = lambda: {"min": lo, "max": hi}
            self._set_matcher(lambda value: isinstance(value, int | float) and not isinstance(value, bool)
                                            and _within(value, lo, hi))
        low.value_changed.connect(update)
        high.value_changed.connect(update)
        update()

    def _build_vector_range(self, prop: str, sample, initial: dict):
        widget_cls = Vec3PropertyWidget if isinstance(sample, brickedit.Vec3) else Vec2PropertyWidget
        low_start, high_start = initial.get("min", sample), initial.get("max", sample)
        low = widget_cls(prop, (low_start,), False, low_start, show_text=False)
        high = widget_cls(prop, (high_start,), False, high_start, show_text=False)
        self.add_setting_row("Minimum", low, layout=self.value_layout)
        self.add_setting_row("Maximum", high, layout=self.value_layout)

        def update(*_):
            lo, hi = low.get_value(low_start).as_tuple(), high.get_value(high_start).as_tuple()
            self._value_config = lambda: {"min": list(lo), "max": list(hi)}
            def matcher(value) -> bool:
                comps = _float_components(value)
                return comps is not None and len(comps) == len(lo) and all(
                    _within(c, l, h) for c, l, h in zip(comps, lo, hi))
            self._set_matcher(matcher)
        low.value_changed.connect(update)
        high.value_changed.connect(update)
        update()


    # ----- Saving

    CONFIG_TYPE = "property_value"

    def get_config(self) -> dict:
        config = {"comparison": enum_key(self.get_comparison())}
        if self.wanted_property is not None:
            config["property"] = self.wanted_property
        return config | self._value_config()

    def apply_config(self, config: ConfigReader) -> None:
        prop = config.get_str("property") or self.wanted_property
        comparison = config.get_enum("comparison", PropertyComparison, self.get_comparison())
        widget_cls = get_property_widget_cls(prop, allow_unknown=False) if prop else None

        initial = {}
        if widget_cls is not None:
            keys = ("value",) if comparison == PropertyComparison.EQUALS else ("min", "max")
            if all(key in config.data for key in keys):
                initial = {key: value_from_config(config.get_raw(key), widget_cls, config.where) for key in keys}

        self.wanted_property = prop
        self.comparison_sw.blockSignals(True)  # Rebuilt once, below
        try:
            self.comparison_sw.set_index(comparison.value)
        finally:
            self.comparison_sw.blockSignals(False)
        self._refresh(initial)


    # ----- Filtering

    def is_allowed(self, brick: Brick) -> FilterResult:
        matcher, prop = self._matcher, self.wanted_property
        if matcher is None or prop is None:
            return self.mode.filter_did_not_match()
        try:
            value = brick.get_property(prop)
        except brickedit.BrickError:
            return self.mode.filter_did_not_match()
        return self.mode.filter_matched() if matcher(value) else self.mode.filter_did_not_match()

    @classmethod
    def get_filter_name(cls, mode: FilterMode):
        return f"Property {mode.get_naming_tuple()[1]} be (...)"

    @classmethod
    def get_tooltip_contents(cls) -> TooltipContents | None:
        return PROPERTY_VALUE_TOOLTIP

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return PropertyValueFilter(mw, mode)
