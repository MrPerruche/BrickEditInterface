"""Settings of a BrickTransform (see brick_transform): pivot, rotation, scale, rounding and offset. Used by the Vehicle
Transformer and the Rule Based Editor's Transform action."""

from math import isfinite

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Signal

from ui.widgets import Widget, Label, StyledLabel, LabelStyle, Switcher, NumberChannelEdit, ChannelMode
from ui.models import TooltipContents
from ui.components.brick.property_widgets import Vec3PropertyWidget
from ui.components.vehicle.brick_transform import BrickTransform, positions_center, ROUND_OFF
from systems.bei_files import ConfigReader, BeiFileError

import brickedit


PIVOTS = ("Selection center", "Each brick", "Point")
PIVOT_KEYS = ("center", "each", "point")  # Saved (rule presets)
CENTER, EACH, POINT = range(3)

SCALE_OPERATIONS = ("Multiply", "Divide")
SCALE_OPERATION_KEYS = ("multiply", "divide")  # Saved (rule presets)
MULTIPLY, DIVIDE = range(2)

ROUNDINGS = ("Off", "Regular", "Up", "Down")      # Indexes are brick_transform's ROUND_* (like the Transformer)
ROUNDING_KEYS = ("off", "regular", "up", "down")  # Saved (rule presets)

LABEL_STRETCH = 8
WIDGET_STRETCH = 19

PIVOT_TOOLTIP = TooltipContents("Pivot", "What the bricks are rotated and scaled about.")
POINT_TOOLTIP = TooltipContents("0, 0, 0 is the vehicle's center.")
ROUNDING_TOOLTIP = TooltipContents("Scale rounding", "Rounds sizes (bricks, wheels, spinners), once scaled. Not positions.")


def _zero() -> brickedit.Vec3:
    return brickedit.Vec3(0.0, 0.0, 0.0)


def _vec3_widget() -> Vec3PropertyWidget:
    return Vec3PropertyWidget('', (_zero(),), False, _zero(), show_text=False)


class TransformSettings(Widget):
    """"Label | widget" rows (proportions of the image importer) setting up a BrickTransform and its pivot, in one
    titled section per part of the transform. section_style: style of the section titles, eg. HEADER_3 when the
    sections are a menu's own, HEADER_5 when nested in something (an action)."""

    changed = Signal()

    def __init__(self, pivot: int = CENTER, switcher_stretch: int = WIDGET_STRETCH,
                 section_style: LabelStyle = LabelStyle.HEADER_5, parent=None):
        super().__init__(parent)
        self.section_style = section_style
        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)

        self._add_section("Rotation")

        self.pivot_sw = Switcher(list(PIVOTS), pivot)
        self._add_row("Pivot", self.pivot_sw, PIVOT_TOOLTIP, switcher_stretch)
        self.point_widget = _vec3_widget()
        self.point_row = self._add_row("Point (cm)", self.point_widget, POINT_TOOLTIP)

        self.rotation_widget = _vec3_widget()
        self._add_row("Angle", self.rotation_widget)

        self._add_section("Scale")
        self.scale_operation_sw = Switcher(list(SCALE_OPERATIONS))
        self._add_row("Operation", self.scale_operation_sw, None, switcher_stretch)
        self.factor_label = Label("Multiply by")
        self.factor_nce = NumberChannelEdit(ChannelMode.FLOAT32, allow_nan=False, allow_inf=False,
                                            constraint=lambda v: v > 0, constraint_message="the factor must be above 0")
        self.factor_nce.setValue(1.0)
        self._add_row(self.factor_label, self.factor_nce)

        self._add_section("Brick Size Rounding")
        self.rounding_sw = Switcher(list(ROUNDINGS))
        self._add_row("Mode", self.rounding_sw, ROUNDING_TOOLTIP, switcher_stretch)
        self.step_nce = NumberChannelEdit(ChannelMode.FLOAT32, allow_nan=False, allow_inf=False,
                                          constraint=lambda v: v > 0, constraint_message="the step must be above 0")
        self.step_nce.setValue(1.0)
        self.step_row = self._add_row("Step (cm)", self.step_nce)

        self._add_section("Position")
        self.offset_widget = _vec3_widget()
        self._add_row("Offset (cm)", self.offset_widget)

        self.pivot_sw.index_changed.connect(self._update_point_row)
        self.scale_operation_sw.index_changed.connect(self._update_factor_label)
        self.rounding_sw.index_changed.connect(self._update_step_row)
        for signal in (self.pivot_sw.index_changed, self.point_widget.value_changed, self.rotation_widget.value_changed,
                       self.scale_operation_sw.index_changed, self.factor_nce.value_changed,
                       self.rounding_sw.index_changed, self.step_nce.value_changed, self.offset_widget.value_changed):
            signal.connect(self._emit_changed)
        self._update_point_row()
        self._update_factor_label()
        self._update_step_row()


    def _add_section(self, title: str):
        self.master_layout.addWidget(StyledLabel(title, self.section_style))

    def _add_row(self, label: str | Label, widget: QWidget, tooltip: TooltipContents | None = None,
                 stretch: int = WIDGET_STRETCH) -> Widget:
        row = Widget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        if isinstance(label, str):
            label = Label(label)
        if tooltip is not None:
            label.set_tooltip(tooltip)
        layout.addWidget(label, stretch=LABEL_STRETCH)
        layout.addWidget(widget, stretch=stretch)
        self.master_layout.addWidget(row)
        return row

    def _emit_changed(self, *_):
        self.changed.emit()

    def _update_point_row(self, *_):
        self.point_row.setVisible(self.pivot_mode() == POINT)

    def _update_factor_label(self, *_):
        self.factor_label.set_text("Divide by" if self.scale_operation() == DIVIDE else "Multiply by")

    def _update_step_row(self, *_):
        self.step_row.setVisible(self.rounding() != ROUND_OFF)


    def pivot_mode(self) -> int:
        return self.pivot_sw.get_idx() or 0

    def scale_operation(self) -> int:
        return self.scale_operation_sw.get_idx() or 0

    def rounding(self) -> int:
        return self.rounding_sw.get_idx() or 0

    def get_transform(self) -> BrickTransform:
        factor = float(self.factor_nce.value())
        scale = 1.0 / factor if self.scale_operation() == DIVIDE and factor else factor  # 0 stays invalid
        return BrickTransform(self.rotation_widget.get_value(_zero()), scale, self.offset_widget.get_value(_zero()),
                              self.rounding(), float(self.step_nce.value()))

    def get_pivot(self, bricks: list[brickedit.Brick]) -> brickedit.Vec3 | None:
        """Pivot to transform bricks about (see transform_bricks). None: each brick about its own position."""
        mode = self.pivot_mode()
        if mode == EACH:
            return None
        return positions_center(bricks) if mode == CENTER else self.point_widget.get_value(_zero())

    def error(self) -> str | None:
        """Why the transform can't be applied, if it can't. A clause, eg. "the factor must be above 0"."""
        transform = self.get_transform()
        if not transform.is_valid():
            return ("the angles, scale factor, rounding step and offset must be numbers, and the factor and step above "
                    "0")
        if transform.is_identity():
            return "this transform changes nothing"
        if self.pivot_mode() == POINT and not all(isfinite(c) for c in self.point_widget.get_value(_zero()).as_tuple()):
            return "the pivot's position must be numbers"
        return None


    # ----- Saving (rule presets, see systems.bei_files)

    def get_config(self) -> dict:
        return {
            "pivot": PIVOT_KEYS[self.pivot_mode()],
            "point": list(self.point_widget.get_value(_zero()).as_tuple()),
            "rotation": list(self.rotation_widget.get_value(_zero()).as_tuple()),
            "scale_operation": SCALE_OPERATION_KEYS[self.scale_operation()],
            "scale": float(self.factor_nce.value()),  # The factor, as typed
            "rounding": ROUNDING_KEYS[self.rounding()],
            "round_step": float(self.step_nce.value()),
            "offset": list(self.offset_widget.get_value(_zero()).as_tuple()),
        }

    def apply_config(self, config: ConfigReader) -> None:
        """Raises BeiFileError if a value is invalid."""
        self.pivot_sw.set_index(PIVOT_KEYS.index(config.get_choice("pivot", PIVOT_KEYS, PIVOT_KEYS[self.pivot_mode()])))
        self.point_widget.set_value(config.get_vec3("point", self.point_widget.get_value(_zero())))
        self.rotation_widget.set_value(config.get_vec3("rotation", self.rotation_widget.get_value(_zero())))
        # Presets saved before scale_operation existed multiply
        self.scale_operation_sw.set_index(SCALE_OPERATION_KEYS.index(
            config.get_choice("scale_operation", SCALE_OPERATION_KEYS, SCALE_OPERATION_KEYS[MULTIPLY])))
        factor = config.get_float("scale", float(self.factor_nce.value()))
        if factor <= 0:
            raise BeiFileError(f"{config.where}: \"scale\" must be above 0.")
        self.factor_nce.setValue(factor)
        self.rounding_sw.set_index(ROUNDING_KEYS.index(config.get_choice("rounding", ROUNDING_KEYS, ROUNDING_KEYS[ROUND_OFF])))
        step = config.get_float("round_step", float(self.step_nce.value()))
        if step <= 0:
            raise BeiFileError(f"{config.where}: \"round_step\" must be above 0.")
        self.step_nce.setValue(step)
        self.offset_widget.set_value(config.get_vec3("offset", self.offset_widget.get_value(_zero())))
