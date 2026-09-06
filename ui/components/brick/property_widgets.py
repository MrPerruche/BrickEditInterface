from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, QSize

from ui.widgets import Widget, Switcher, StyledLabel, LabelStyle, LineEdit, NumberChannelEdit, FormulaChannelEdit, ChannelMode, ToolButton, Button
from ui.validators import ASCII_TEXT_ONLY, BINARY_HEX_VALIDATOR_65535_MAX
from ui.components.brick.property_utils import get_or_make_property_display_name

from utils import Sentinel

import colorsys
from typing import Hashable, TypeVar

import brickedit

import logging
logger = logging.getLogger(__name__)


T = TypeVar("T", bound=Hashable)



class BasePropertyWidget(Widget):

    value_changed = Signal(tuple)

    def __init__(self, property_name: str, test_values: tuple[T, ...], formula_mode: bool, initial_value: T, enabled: bool = True, show_text: bool = True):
        """Property name is the internal property name from Brick Rigs (eg. bGenerateLift).

        Test values is a set of values that must be tested for when evaluating a widget. Eg. when
        a user inputs a formula like 1/(x-1), this formula may yield invalid numbers if eg. x is 1.
        If any of these test values cause an error, then the input will not be allowed.

        Test values are not guarenteed to be used as they are irrelevant for some property types
        such as booleans."""
        super().__init__()

        self.property_name = property_name
        self.test_values = test_values
        self.formula_mode = formula_mode
        self.dirty = False
        self.enabled = enabled

        self._has_text = show_text
        self.display_text = get_or_make_property_display_name(property_name).upper()

        self.true_master_layout = QVBoxLayout()
        self.true_master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.true_master_layout)

        self.display_name_label = StyledLabel(self.display_text, LabelStyle.PROPERTIES)
        self.true_master_layout.addWidget(self.display_name_label)
        if not show_text:
            self.display_name_label.hide()

        self.master_layout = QHBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.true_master_layout.addLayout(self.master_layout)


    def set_display_text(self, display_text: str | None):
        if display_text is None:
            self.display_name_label.hide()
        else:
            self.display_name_label.set_text(display_text)
            self.display_name_label.show()

    def on_value_changed(self):
        self.dirty = True
        self.value_changed.emit(self.get_text())


    def get_property(self) -> str:
        return self.property_name

    def is_enabled(self) -> bool:
        return self.enabled

    def is_dirty(self) -> bool:
        return self.dirty


    def is_cachable(self) -> bool:
        return True


    def set_enabled(self, enabled: bool):
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement set_enabled()")

    def get_text(self) -> tuple[str, ...]:
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement get_text()")

    def set_value(self, value: T):
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement set_value()")

    def get_value(self, default_value: T) -> T:
        """default_value parameter is used if the widget was never edited or if formulas are used."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement get_value()")

    @classmethod
    def get_example_value(cls) -> T:
        """gives a value that is valid for this widget."""
        raise NotImplementedError(f"Subclass {cls.__name__} must implement get_example_value()")



class TextPropertyWidget(BasePropertyWidget):

    EDIT_ICON = None
    KEEP_DEFAULT_DISPLAY = "Do not edit"

    def __init__(self, property_name: str, test_values: tuple[str, ...], formula_mode: bool, initial_value: str, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)

        self.input_le: LineEdit = LineEdit()
        self.set_value('' if formula_mode else initial_value)
        self.master_layout.addWidget(self.input_le)
        self.formula_mode_value = ""

        if formula_mode:
            self.input_le.set_text(TextPropertyWidget.KEEP_DEFAULT_DISPLAY)
            self.input_le.set_enabled(False)
            if TextPropertyWidget.EDIT_ICON is None:
                TextPropertyWidget.EDIT_ICON = QIcon(':/assets/icons/BrickEditorIcon.png')
            self.edit_button = ToolButton(self.EDIT_ICON, tint_icon=True)
            self.edit_button.set_checkable(True)
            self.edit_button.toggled.connect(self.on_edit_button_toggled)
            self.master_layout.addWidget(self.edit_button)
        else:
            self.edit_button = None

        self.input_le.text_changed.connect(self.on_value_changed)
        self.set_enabled(enabled)


    def on_edit_button_toggled(self, checked: bool):
        if checked:
            self.input_le.set_text(self.formula_mode_value)
        else:
            self.formula_mode_value = self.input_le.get_text()
            self.input_le.set_text(TextPropertyWidget.KEEP_DEFAULT_DISPLAY)
        self.input_le.set_enabled(checked)
        self.on_value_changed()



    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if self.edit_button is not None:
            self.edit_button.set_enabled(enabled)
            self.input_le.set_enabled(enabled and self.edit_button.is_checked())
        else:
            self.input_le.set_enabled(enabled)

    def get_text(self):
        return (self.input_le.get_text(),)

    def set_value(self, value: str):
        self.input_le.set_text(value)

    def get_value(self, default_value: str):
        if self.edit_button is not None:  # -> Formula mode
            return self.input_le.get_text() if self.edit_button.is_checked() else default_value
        return self.input_le.get_text()

    @classmethod
    def get_example_value(cls) -> str:
        return ""



class AsciiPropertyWidget(TextPropertyWidget):
    def __init__(self, property_name: str, test_values: tuple[str, ...], formula_mode: bool, initial_value: str, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)
        self.input_le.set_validator(ASCII_TEXT_ONLY)



class BooleanPropertyWidget(BasePropertyWidget):

    FORMULA_MODE_ACTIONS = [
        ('Same', lambda value: value),
        ('Invert', lambda value: not value),
        ('Off', lambda _: False),
        ('On', lambda _: True)
    ]

    def __init__(self, property_name: str, test_values: tuple[bool, ...], formula_mode: bool, initial_value: bool | None, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)

        self.setting_widget = Switcher([name for name, _ in self.FORMULA_MODE_ACTIONS] if formula_mode else ["Off", "On"])
        self.set_value(0 if formula_mode or initial_value is None else int(initial_value)) # If in formula mode, set value to 0 for "Same"
        self.setting_widget.index_changed.connect(self.on_value_changed)

        self.master_layout.addWidget(self.setting_widget)

        self.set_enabled(enabled)
        self.setting_widget.left_arrow.set_enabled(False)


    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.setting_widget.set_enabled(enabled)

    def get_text(self):
        value = self.setting_widget.get_idx()
        return (self.FORMULA_MODE_ACTIONS[value][0] if self.formula_mode else ["Off", "On"][value],)

    def set_value(self, value: int):
        self.setting_widget.set_index(value)

    def get_value(self, default_value: bool) -> bool:
        idx = self.setting_widget.get_idx()
        return self.FORMULA_MODE_ACTIONS[idx](default_value) if self.formula_mode else bool(idx)

    @classmethod
    def get_example_value(cls) -> bool:
        return False



class FloatPropertyWidget(BasePropertyWidget):

    def __init__(self, property_name: str, test_values: tuple[float, ...], formula_mode: bool, initial_value: float, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)

        self.value_input = FormulaChannelEdit() if formula_mode else NumberChannelEdit()
        self.set_value(initial_value)
        if formula_mode:
            self.value_input.formula_changed.connect(self.on_value_changed)
        else:
            self.value_input.value_changed.connect(self.on_value_changed)

        self.master_layout.addWidget(self.value_input)

        self.set_enabled(enabled)


    def set_enabled(self, enabled: bool):
        self.value_input.set_enabled(enabled)
        self.enabled = enabled

    def get_text(self):
        return (self.value_input.get_text(),)

    def set_value(self, value: float):
        if self.formula_mode:
            self.value_input.setFormula('x')
        else:
            self.value_input.setValue(value)

    def get_value(self, default_value: float):
        return self.value_input.evaluate_at(x=default_value) if self.formula_mode else self.value_input.value()

    @classmethod
    def get_example_value(cls) -> float:
        return 0.0



class Vec2PropertyWidget(BasePropertyWidget):

    def __init__(self, property_name: str, test_values: tuple[brickedit.Vec2, ...], formula_mode: bool, initial_value: brickedit.Vec2, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)

        self._is_called_by_function_flag: bool = False
        self.is_locked: bool = False

        self.lock_button = ToolButton(QIcon(":/assets/icons/Unlocked.png"), True)
        self.lock_button.set_checkable(True)
        extra_variables = {"x": 0.0, "y": 0.0}
        self.x_widget = FormulaChannelEdit(variable_name="x", extra_variables=extra_variables) if formula_mode else NumberChannelEdit()
        self.y_widget = FormulaChannelEdit(variable_name="y", extra_variables=extra_variables) if formula_mode else NumberChannelEdit()
        self.set_value(initial_value)

        self.lock_button.clicked.connect(self.on_lock_toggled)
        if formula_mode:
            self.x_widget.formula_changed.connect(lambda value: self.on_value_changed(value, 0))
            self.y_widget.formula_changed.connect(lambda value: self.on_value_changed(value, 1))
        else:
            self.x_widget.value_changed.connect(lambda value: self.on_value_changed(value, 0))
            self.y_widget.value_changed.connect(lambda value: self.on_value_changed(value, 1))

        self.master_layout.addWidget(self.lock_button)
        self.master_layout.addWidget(self.x_widget)
        self.master_layout.addWidget(self.y_widget)

        self.set_enabled(enabled)

    def on_lock_toggled(self):
        self.is_locked = not self.is_locked
        self.lock_button.set_icon(QIcon(":/assets/icons/Locked.png" if self.is_locked else ":/assets/icons/Unlocked.png"))
        self.lock_button.set_checked(self.is_locked)

    def set_enabled(self, enabled: bool):
        self.x_widget.set_enabled(enabled)
        self.y_widget.set_enabled(enabled)
        self.enabled = enabled

    def on_value_changed(self, value, w: int):
        if self._is_called_by_function_flag:
            return
        self._is_called_by_function_flag = True

        self.dirty = True
        self.value_changed.emit(self.get_text())
        if self.is_locked:
                self.set_value(brickedit.Vec2(
                    value if w == 0 else self.get_value(brickedit.Vec2(0.0, 0.0)).y,
                    self.get_value(brickedit.Vec2(0.0, 0.0)).x if w == 0 else value
                    ))
        self._is_called_by_function_flag = False

    def get_text(self):
        return (self.x_widget.get_text(), self.y_widget.get_text())

    def set_value(self, value: brickedit.Vec2):
        if self.formula_mode:
            self.x_widget.setFormula('x')
            self.y_widget.setFormula('y')
        else:
            self.x_widget.setValue(value.x)
            self.y_widget.setValue(value.y)

    def get_value(self, default_value: brickedit.Vec2):
        eval_table = {
            'x': default_value.x,
            'y': default_value.y
        }
        return brickedit.Vec2(
            x=self.x_widget.evaluate_at(**eval_table),
            y=self.y_widget.evaluate_at(**eval_table)
        ) if self.formula_mode else brickedit.Vec2(
            x=self.x_widget.value(),
            y=self.y_widget.value()
        )

    @classmethod
    def get_example_value(cls) -> brickedit.Vec2:
        return brickedit.Vec2(0, 0)



class Vec3PropertyWidget(BasePropertyWidget):

    def __init__(self, property_name: str, test_values: tuple[brickedit.Vec3, ...], formula_mode: bool, initial_value: brickedit.Vec3, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)

        self._is_called_by_function_flag: bool = False
        self.is_locked: bool = False

        self.lock_button = ToolButton(QIcon(":/assets/icons/Unlocked.png"), True)
        self.lock_button.set_checkable(True)
        extra_variables = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.x_widget = FormulaChannelEdit(variable_name="x", extra_variables=extra_variables) if formula_mode else NumberChannelEdit()
        self.y_widget = FormulaChannelEdit(variable_name="y", extra_variables=extra_variables) if formula_mode else NumberChannelEdit()
        self.z_widget = FormulaChannelEdit(variable_name="z", extra_variables=extra_variables) if formula_mode else NumberChannelEdit()
        self.set_value(initial_value)

        self.lock_button.clicked.connect(self.on_lock_toggled)
        if formula_mode:
            self.x_widget.formula_changed.connect(lambda value: self.on_value_changed(value, 0))
            self.y_widget.formula_changed.connect(lambda value: self.on_value_changed(value, 1))
            self.z_widget.formula_changed.connect(lambda value: self.on_value_changed(value, 2))
        else:
            self.x_widget.value_changed.connect(lambda value: self.on_value_changed(value, 0))
            self.y_widget.value_changed.connect(lambda value: self.on_value_changed(value, 1))
            self.z_widget.value_changed.connect(lambda value: self.on_value_changed(value, 2))

        self.master_layout.addWidget(self.lock_button)
        self.master_layout.addWidget(self.x_widget)
        self.master_layout.addWidget(self.y_widget)
        self.master_layout.addWidget(self.z_widget)

        self.set_enabled(enabled)


    def on_lock_toggled(self):
        self.is_locked = not self.is_locked
        self.lock_button.set_icon(QIcon(":/assets/icons/Locked.png" if self.is_locked else ":/assets/icons/Unlocked.png"))
        self.lock_button.set_checked(self.is_locked)

    def on_value_changed(self, value, w: int):
        if self._is_called_by_function_flag:
            return
        self._is_called_by_function_flag = True

        self.dirty = True
        self.value_changed.emit(self.get_text())
        if self.is_locked:
                self.set_value(brickedit.Vec3(
                    value if w == 0 else self.get_value(brickedit.Vec3(0.0, 0.0, 0.0)).y if w == 1 else self.get_value(brickedit.Vec3(0.0, 0.0, 0.0)).z,
                    self.get_value(brickedit.Vec3(0.0, 0.0, 0.0)).x if w == 0 else value if w == 1 else self.get_value(brickedit.Vec3(0.0, 0.0, 0.0)).z,
                    self.get_value(brickedit.Vec3(0.0, 0.0, 0.0)).x if w == 0 else self.get_value(brickedit.Vec3(0.0, 0.0, 0.0)).y if w == 1 else value
                    ))
        self._is_called_by_function_flag = False

    def set_enabled(self, enabled: bool):
        self.x_widget.set_enabled(enabled)
        self.y_widget.set_enabled(enabled)
        self.z_widget.set_enabled(enabled)
        self.enabled = enabled

    def get_text(self):
        return (self.x_widget.get_text(), self.y_widget.get_text(), self.z_widget.get_text())

    def set_value(self, value: brickedit.Vec3 | None):
        if self.formula_mode:
            self.x_widget.setFormula('x')
            self.y_widget.setFormula('y')
            self.z_widget.setFormula('z')
        else:
            assert value is not None, f"Value is None for {self.property_name}"
            self.x_widget.setValue(value.x)
            self.y_widget.setValue(value.y)
            self.z_widget.setValue(value.z)

    def get_value(self, default_value: brickedit.Vec3) -> bool:
        eval_table = {
            'x': default_value.x,
            'y': default_value.y,
            'z': default_value.z
        }
        return brickedit.Vec3(
            x=self.x_widget.evaluate_at(**eval_table),
            y=self.y_widget.evaluate_at(**eval_table),
            z=self.z_widget.evaluate_at(**eval_table)
        ) if self.formula_mode else brickedit.Vec3(
            x=self.x_widget.value(),
            y=self.y_widget.value(),
            z=self.z_widget.value()
        )

    @classmethod
    def get_example_value(cls) -> brickedit.Vec3:
        return brickedit.Vec3(0, 0, 0)



class Integer8PropertyWidget(BasePropertyWidget):

    args = {
        'mode': ChannelMode.INT,
        'minimum': -128,
        'maximum': 127,
        'allow_nan': False,
        'allow_inf': False
    }

    def __init__(self, property_name: str, test_values: tuple[int, ...], formula_mode: bool, initial_value: int, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)

        self.value_input = FormulaChannelEdit(**self.args) if formula_mode else NumberChannelEdit(**self.args)
        self.set_value(initial_value)
        if formula_mode:
            self.value_input.formula_changed.connect(self.on_value_changed)
        else:
            self.value_input.value_changed.connect(self.on_value_changed)

        self.master_layout.addWidget(self.value_input)

        self.set_enabled(enabled)


    def set_enabled(self, enabled: bool):
        self.value_input.set_enabled(enabled)
        self.enabled = enabled


    def get_text(self):
        return (self.value_input.get_text(),)

    def set_value(self, value: int):
        if self.formula_mode:
            self.value_input.setFormula('x')
        else:
            self.value_input.setValue(value)

    def get_value(self, default_value: int) -> int:
        return self.value_input.evaluate_at(x=default_value) if self.formula_mode else self.value_input.value()

    @classmethod
    def get_example_value(cls) -> int:
        return 0



class ColorPropertyWidget(BasePropertyWidget):

    rgb_args = {
        'mode': ChannelMode.INT,
        'minimum': 0,
        'maximum': 255,
        'allow_nan': False,
        'allow_inf': False
    }

    hsv_h_args = {
        'mode': ChannelMode.FLOAT32,
        'minimum': 0,
        'maximum': 360,
        'decimals': 1,
        'allow_nan': False,
        'allow_inf': False
    }

    hsv_sv_args = {
        'mode': ChannelMode.FLOAT32,
        'minimum': 0,
        'maximum': 100,
        'decimals': 1,
        'allow_nan': False,
        'allow_inf': False
    }

    def __init__(
        self,
        property_name: str,
        test_values: tuple[int, ...],
        formula_mode: bool,
        initial_value: int,
        enabled: bool = True,
        show_text: bool = True
    ):
        super().__init__(
            property_name,
            test_values,
            formula_mode,
            initial_value,
            enabled,
            show_text
        )

        self.color_space = 'rgba'
        self.color_space_widget = Button('RGB')
        self.color_space_widget.clicked.connect(self.on_color_space_changed)
        self.master_layout.addWidget(self.color_space_widget, stretch=10)

        channel_type = FormulaChannelEdit if formula_mode else NumberChannelEdit

        if formula_mode:
            extra_variables = {
                'r': 0.0,
                'g': 0.0,
                'b': 0.0,
                'a': 0.0,
                'h': 0.0,
                's': 0.0,
                'v': 0.0
            }

            self.r_widget = channel_type(
                variable_name='r',
                extra_variables=extra_variables,
                **self.rgb_args
            )
            self.g_widget = channel_type(
                variable_name='g',
                extra_variables=extra_variables,
                **self.rgb_args
            )
            self.b_widget = channel_type(
                variable_name='b',
                extra_variables=extra_variables,
                **self.rgb_args
            )
            self.a_widget = channel_type(
                variable_name='a',
                extra_variables=extra_variables,
                **self.rgb_args
            )

            self.h_widget = channel_type(
                variable_name='h',
                extra_variables=extra_variables,
                **self.hsv_h_args
            )
            self.s_widget = channel_type(
                variable_name='s',
                extra_variables=extra_variables,
                **self.hsv_sv_args
            )
            self.v_widget = channel_type(
                variable_name='v',
                extra_variables=extra_variables,
                **self.hsv_sv_args
            )
            self.ha_widget = channel_type(
                variable_name='a',
                extra_variables=extra_variables,
                **self.rgb_args
            )
        else:
            self.r_widget = channel_type(**self.rgb_args)
            self.g_widget = channel_type(**self.rgb_args)
            self.b_widget = channel_type(**self.rgb_args)
            self.a_widget = channel_type(**self.rgb_args)

            self.h_widget = channel_type(**self.hsv_h_args)
            self.s_widget = channel_type(**self.hsv_sv_args)
            self.v_widget = channel_type(**self.hsv_sv_args)
            self.ha_widget = channel_type(**self.rgb_args)

        self.rgb_widgets = (self.r_widget, self.g_widget, self.b_widget, self.a_widget)
        self.hsv_widgets = (self.h_widget, self.s_widget, self.v_widget, self.ha_widget)
        self.widgets = self.rgb_widgets + self.hsv_widgets

        for widget in self.widgets:
            if formula_mode:
                widget.formula_changed.connect(self.on_value_changed)
            else:
                widget.value_changed.connect(self.on_value_changed)

        for widget in self.widgets:
            self.master_layout.addWidget(widget, stretch=10)

        self.set_value(initial_value)
        self.set_enabled(enabled)
        self._update_channel_visibility()

    def on_color_space_changed(self):
        self.color_space = 'rgba' if self.color_space == 'hsva' else 'hsva'
        self.color_space_widget.set_text(
            'RGB' if self.color_space == 'rgba' else 'HSV'
        )
        self._update_channel_visibility()

    def _update_channel_visibility(self):
        rgb = self.color_space == 'rgba'

        for widget in self.rgb_widgets:
            widget.setVisible(rgb)

        for widget in self.hsv_widgets:
            widget.setVisible(not rgb)

    def set_enabled(self, enabled: bool):
        for widget in self.widgets:
            widget.set_enabled(enabled)

        self.enabled = enabled

    def get_text(self):
        widgets = self.rgb_widgets if self.color_space == 'rgba' else self.hsv_widgets
        return tuple(widget.get_text() for widget in widgets)

    @staticmethod
    def _rgba_to_hsva(r: int, g: int, b: int, a: int):
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        return (h * 360.0, s * 100.0, v * 100.0, a)

    @staticmethod
    def _hsva_to_rgba(h: float, s: float, v: float, a: float):
        r, g, b = colorsys.hsv_to_rgb(h / 360.0, s / 100.0, v / 100.0)

        return (round(r * 255), round(g * 255), round(b * 255), round(a))

    @staticmethod
    def _pack_rgba(r: int, g: int, b: int, a: int) -> int:
        return (r << 24) | (g << 16) | (b << 8) | a

    def set_value(self, value: int):
        if value is None:
            value = self.get_example_value()

        r = value >> 24 & 0xFF
        g = value >> 16 & 0xFF
        b = value >> 8 & 0xFF
        a = value & 0xFF

        h, s, v, _ = self._rgba_to_hsva(r, g, b, a)

        if self.formula_mode:
            for widget, variable in zip(self.rgb_widgets, ('r', 'g', 'b', 'a')):
                widget.setFormula(variable)

            for widget, variable in zip(self.hsv_widgets, ('h', 's', 'v', 'a')):
                widget.setFormula(variable)

            return

        for widget, channel_value in zip(self.rgb_widgets, (r, g, b, a)):
            widget.setValue(channel_value)

        for widget, channel_value in zip(self.hsv_widgets, (h, s, v, a)):
            widget.setValue(channel_value)

    def get_value(self, default_value: int) -> int:
        default_r = default_value >> 24 & 0xFF
        default_g = default_value >> 16 & 0xFF
        default_b = default_value >> 8 & 0xFF
        default_a = default_value & 0xFF

        default_h, default_s, default_v, _ = self._rgba_to_hsva(default_r, default_g, default_b, default_a)

        if self.formula_mode:
            eval_table = {
                'r': default_r,
                'g': default_g,
                'b': default_b,
                'a': default_a,
                'h': default_h,
                's': default_s,
                'v': default_v
            }

            if self.color_space == 'rgba':
                r = self.r_widget.evaluate_at(**eval_table)
                g = self.g_widget.evaluate_at(**eval_table)
                b = self.b_widget.evaluate_at(**eval_table)
                a = self.a_widget.evaluate_at(**eval_table)

                return self._pack_rgba(r, g, b, a)

            h = self.h_widget.evaluate_at(**eval_table)
            s = self.s_widget.evaluate_at(**eval_table)
            v = self.v_widget.evaluate_at(**eval_table)
            a = self.ha_widget.evaluate_at(**eval_table)

            r, g, b, a = self._hsva_to_rgba(h, s, v, a)

            return self._pack_rgba(r, g, b, a)

        if self.color_space == 'rgba':
            r = self.r_widget.value()
            g = self.g_widget.value()
            b = self.b_widget.value()
            a = self.a_widget.value()

            return self._pack_rgba(r, g, b, a)

        h = self.h_widget.value()
        s = self.s_widget.value()
        v = self.v_widget.value()
        a = self.ha_widget.value()

        r, g, b, a = self._hsva_to_rgba(h, s, v, a)

        # Keep the hidden RGB representation synchronized with HSV edits.
        for widget, channel_value in zip(
            self.rgb_widgets,
            (r, g, b, a),
        ):
            widget.setValue(channel_value)

        return self._pack_rgba(r, g, b, a)

    @classmethod
    def get_example_value(cls) -> int:
        return 0xbcbcbcff



def format_bin(data: bytes):
    return " ".join(f"{byte:02X}" for byte in data)

def from_bin(data: str):
    return bytes.fromhex(data)


class UnknownTypePropertyWidget(BasePropertyWidget):

    EDIT_ICON = None
    KEEP_DEFAULT_DISPLAY = "Do not edit"

    def __init__(self, property_name: str, test_values: tuple[bytes, ...], formula_mode: bool, initial_value: bytes, enabled: bool = True, show_text: bool = True):
        super().__init__(property_name, test_values, formula_mode, initial_value, enabled, show_text)
        self.input_le: LineEdit = LineEdit()
        self.input_le.set_validator(BINARY_HEX_VALIDATOR_65535_MAX)
        # if isinstance(initial_value, int):
        #     print(f"{property_name} is int!: {initial_value}")
        self.set_value(b'' if formula_mode else initial_value)
        self.master_layout.addWidget(self.input_le)
        self.formula_mode_value = ""

        if formula_mode:
            self.input_le.set_text(UnknownTypePropertyWidget.KEEP_DEFAULT_DISPLAY)
            self.input_le.set_enabled(False)
            if self.EDIT_ICON is None:
                self.EDIT_ICON = QIcon(':/assets/icons/BrickEditorIcon.png')
            self.edit_button = ToolButton(self.EDIT_ICON, tint_icon=True)
            self.edit_button.set_checkable(True)
            self.edit_button.toggled.connect(self.on_edit_button_toggled)
            self.master_layout.addWidget(self.edit_button)
        else:
            self.edit_button = None

        self.input_le.text_changed.connect(self.on_value_changed)
        self.set_enabled(enabled)


    def on_edit_button_toggled(self, checked: bool):
        if checked:
            self.input_le.set_text(self.formula_mode_value)
        else:
            self.formula_mode_value = self.input_le.get_text()
            self.input_le.set_text(UnknownTypePropertyWidget.KEEP_DEFAULT_DISPLAY)
        self.input_le.set_enabled(checked)
        self.on_value_changed()



    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if self.edit_button is not None:
            self.edit_button.set_enabled(enabled)
            self.input_le.set_enabled(enabled and self.edit_button.is_checked())
        else:
            self.input_le.set_enabled(enabled)

    def get_text(self):
        return (from_bin(self.input_le.get_text()),)

    def set_value(self, value: bytes):
        self.input_le.set_text(format_bin(value))

    def get_value(self, default_value: bytes):
        if self.edit_button is not None:  # -> Formula mode
            return from_bin(self.input_le.get_text()) if self.edit_button.is_checked() else default_value
        return from_bin(self.input_le.get_text())

    @classmethod
    def get_example_value(cls) -> bytes:
        return b""


# ----------



def get_property_widget_cls(property_name: str, allow_unknown: bool = True) -> type[BasePropertyWidget] | None:
    property_meta_cls = brickedit.p.pmeta_registry.get(property_name, brickedit.p.UnknownPropertyMeta)
    if not isinstance(property_meta_cls, type):
        return None

    if issubclass(property_meta_cls, brickedit.p.EnumMeta):
        return AsciiPropertyWidget
    elif issubclass(property_meta_cls, brickedit.p.TextMeta):
        return TextPropertyWidget
    elif issubclass(property_meta_cls, brickedit.p.BooleanMeta):
        return BooleanPropertyWidget
    elif issubclass(property_meta_cls, brickedit.p.Float32Meta):
        return FloatPropertyWidget
    elif issubclass(property_meta_cls, brickedit.p.Vec2Meta):
        return Vec2PropertyWidget
    elif issubclass(property_meta_cls, brickedit.p.ExitLocation):
        return None
    elif issubclass(property_meta_cls, brickedit.p.BrickSize):
        return Vec3PropertyWidget
    elif issubclass(property_meta_cls, brickedit.p.NumFractionalDigits):
        return Integer8PropertyWidget
    elif issubclass(property_meta_cls, (brickedit.p.Color3ChannelsMeta, brickedit.p.Color4ChannelsMeta)):
        return ColorPropertyWidget

    return UnknownTypePropertyWidget if allow_unknown else None


def get_property_widget(
    property_name: str,
    test_values: tuple[T, ...],
    formula_mode: bool,
    initial_value: T,
    enabled: bool = True,
    show_text: bool = True
) -> BasePropertyWidget | None:

    widget_cls = get_property_widget_cls(property_name, allow_unknown=True)

    if widget_cls is None:
        return None

    if issubclass(widget_cls, UnknownTypePropertyWidget):
        if all([isinstance(test_value, bytes) for test_value in test_values]):
            try:
                return UnknownTypePropertyWidget(property_name, test_values, formula_mode, initial_value, enabled, show_text)
            except (TypeError, ValueError):
                return None
        else:
            return None

    # if initial_value is None:
    #     logger.warning(f"Initial value is None for property widget_cls{property_name, test_values, formula_mode, initial_value, enabled, show_text}. Defaulting to {widget_cls.get_example_value() = } ")
    #     initial_value = widget_cls.get_example_value()
    return widget_cls(property_name, test_values, formula_mode, initial_value, enabled, show_text)
