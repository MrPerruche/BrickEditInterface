from .expression_widget import ExpressionWidget, ExpressionType,  ExpressionSymbol

from custom_validators import *

from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget, QCheckBox, QComboBox
from brickedit import p, vec, Brick


def _is_true(s: str):
    s = s.lower().strip()
    bs = s in ("false", "0")  # Check for things that evaluate true by bool(...) but are actually false
    if bs:
        return False
    return bool(s)



class PropertyWidget(QWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(parent)

        self.setContentsMargins(0, 0, 0, 0)

        self.master_layout = QHBoxLayout(self)
        self.master_layout.setContentsMargins(2, 4, 2, 4)
        self.default_value = default_value
        self.setLayout(self.master_layout)
        
        self.name = name
        self.display_name = display_name
        self.display_name_label = QLabel(display_name)
        self.master_layout.addWidget(self.display_name_label, 80)

    def get_text(self):
        raise NotImplementedError

    def set_value(self, value):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError

    @staticmethod
    def from_property(prop, value):
        
        pmeta = p.pmeta_registry.get(prop)
        if pmeta is None:
            return UnknownPropertyWidget(prop, value)

        display_name = prop

        # TODO: use a registry instead
        if isinstance(pmeta, type) and issubclass(pmeta, p.BooleanMeta):
            return BooleanPropertyWidget(prop, display_name, str(value))
        if isinstance(pmeta, type) and issubclass(pmeta, p.TextMeta):
            return TextPropertyWidget(prop, display_name, str(value))
        if isinstance(pmeta, type) and issubclass(pmeta, p.EnumMeta):
            return AsciiPropertyWidget(prop, display_name, str(value))
        if isinstance(pmeta, type) and issubclass(pmeta, p.Float32Meta):
            return FloatPropertyWidget(prop, display_name, str(value))
        if isinstance(pmeta, type) and issubclass(pmeta, p.Vec2Meta):
            return Vec2PropertyWidget(prop, display_name, str(value.as_tuple()))
        if isinstance(pmeta, type) and issubclass(pmeta, (p.BrickSize, p.ExitLocation)):
            return Vec3PropertyWidget(prop, display_name, str(value.as_tuple()))
        if isinstance(pmeta, type) and issubclass(pmeta, p.NumFractionalDigits):
            return Integer8PropertyWidget(prop, display_name, str(value))

        return UnknownPropertyWidget(prop, display_name, str(value))

    def get_dict_pair(self):
        return {self.name: self.get_value()}



class BooleanPropertyWidget(PropertyWidget):


    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.input_cb = QCheckBox()
        self.input_cb.setChecked(_is_true(default_value))
        self.master_layout.addWidget(self.input_cb)

    def get_text(self):
        return "True" if self.input_cb.isChecked() else "False"

    def set_value(self, value):
        self.input_cb.setChecked(_is_true(value))

    def get_value(self):
        return True if self.input_cb.isChecked() else False


class TextPropertyWidget(PropertyWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.input_le = QLineEdit()
        self.input_le.setText(self.default_value)
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(value)

    def get_value(self):
        return self.input_le.text()


class AsciiPropertyWidget(PropertyWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.input_le = QLineEdit()
        self.input_le.setText(self.default_value)
        self.input_le.setValidator(AsciiOnlyValidator())
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(value)

    def get_value(self):
        return self.input_le.text()


class FloatPropertyWidget(PropertyWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.input_le = ExpressionWidget(float(default_value), ExpressionType.FLOAT)
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.get_text()

    def set_value(self, value):
        self.input_le.setText(str(value))

    def get_value(self):
        try:
            return self.input_le.value()
        except ValueError:
            return self.default_value


class Vec2PropertyWidget(PropertyWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.values_layout = QHBoxLayout()
        self.master_layout.addLayout(self.values_layout, 100)

        x, y = default_value.strip().strip("()").split(",")

        self.input_le_x = ExpressionWidget(float(x), ExpressionType.FLOAT)
        self.values_layout.addWidget(self.input_le_x)
        self.input_le_y = ExpressionWidget(float(y), ExpressionType.FLOAT)
        self.values_layout.addWidget(self.input_le_y)

    def get_text(self):
        return f"({self.input_le_x.text()}, {self.input_le_y.text()})"

    def set_value(self, value):
        try:
            x, y = value.strip().strip("()").split(",")
        except ValueError:
            return
        self.input_le_x.setText(x)
        self.input_le_y.setText(y)

    def get_value(self):
        return vec.Vec2(self.input_le_x.value(), self.input_le_y.value())


class Vec3PropertyWidget(PropertyWidget):

    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.values_layout = QHBoxLayout()
        self.master_layout.addLayout(self.values_layout, 100)

        x, y, z = default_value.strip().strip("()").split(",")

        self.input_le_x = ExpressionWidget(float(x), ExpressionType.FLOAT)
        self.values_layout.addWidget(self.input_le_x)
        self.input_le_y = ExpressionWidget(float(y), ExpressionType.FLOAT)
        self.values_layout.addWidget(self.input_le_y)
        self.input_le_z = ExpressionWidget(float(z), ExpressionType.FLOAT)
        self.values_layout.addWidget(self.input_le_z)

    def get_text(self):
        return f"({self.input_le_x.text()}, {self.input_le_y.text()}, {self.input_le_z.text()})"

    def set_value(self, value):
        try:
            x, y, z = value.strip().strip("()").split(",")
        except ValueError:
            return
        self.input_le_x.setText(x)
        self.input_le_y.setText(y)
        self.input_le_z.setText(z)

    def get_value(self):
        return vec.Vec3(self.input_le_x.value(), self.input_le_y.value(), self.input_le_z.value())


class Integer8PropertyWidget(PropertyWidget):

    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.input_le = ExpressionWidget(int(default_value), ExpressionType.INTEGER, clamps=(-128, 127))
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.get_text()

    def set_value(self, value):
        self.input_le.setText(str(value))

    def get_value(self):
        try:
            return self.input_le.value()
        except ValueError:
            return self.default_value


class UnknownPropertyWidget(PropertyWidget):
    
    def __init__(self, name: str, property_display_name: str, default_value: str, parent=None):
        super().__init__(name, property_display_name, default_value, parent)

        self.input_le = QLineEdit()
        self.input_le.setText(f"NS: {str(self.default_value)}")
        self.input_le.setReadOnly(True)
        self.input_le.setEnabled(False)
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(f"NS: {str(value)}")

    def get_value(self):
        raise ValueError("Cannot get value of unknown property")

    def get_dict_pair(self):
        return {}




# ---------------




class DynamicPropertyWidget(QWidget):

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(parent=parent)

        self.master_layout = QHBoxLayout(self)
        self.master_layout.setContentsMargins(2, 4, 2, 4)
        self.setLayout(self.master_layout)
        
        self.name = name
        self.display_name = display_name
        self.display_name_label = QLabel(display_name)
        self.master_layout.addWidget(self.display_name_label, 80)

    def get_text(self):
        raise NotImplementedError

    def set_value(self, value):
        raise NotImplementedError

    def get_value(self, brick_x: Brick):
        raise NotImplementedError

    @staticmethod
    def from_property(prop):
        
        pmeta = p.pmeta_registry.get(prop)
        if pmeta is None:
            return UnknownDynamicPropertyWidget(prop)

        display_name = prop

        # TODO: use a registry instead
        if isinstance(pmeta, type) and issubclass(pmeta, p.BooleanMeta):
            return BooleanDynamicPropertyWidget(prop, display_name)
        if isinstance(pmeta, type) and issubclass(pmeta, p.TextMeta):
            return TextDynamicPropertyWidget(prop, display_name)
        if isinstance(pmeta, type) and issubclass(pmeta, p.EnumMeta):
            return AsciiDynamicPropertyWidget(prop, display_name)
        if isinstance(pmeta, type) and issubclass(pmeta, p.Float32Meta):
            return FloatDynamicPropertyWidget(prop, display_name)
        if isinstance(pmeta, type) and issubclass(pmeta, p.Vec2Meta):
            return Vec2DynamicPropertyWidget(prop, display_name)
        if isinstance(pmeta, type) and issubclass(pmeta, p.BrickSize):
            return Vec3DynamicPropertyWidget(prop, display_name)
        if isinstance(pmeta, type) and issubclass(pmeta, p.NumFractionalDigits):
            return Integer8DynamicPropertyWidget(prop, display_name)

        return UnknownDynamicPropertyWidget(prop, display_name)



class BooleanDynamicPropertyWidget(DynamicPropertyWidget):

    _OPT_IDX_TO_ACTION = {
        0: lambda x: x,
        1: lambda x: not x,
        2: lambda _: True,
        3: lambda _: False
    }

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)
        self.input_cb = QComboBox()
        self.input_cb.addItems(["Keep as-is", "Invert", "True (On)", "False (Off)"])
        self.input_cb.setCurrentIndex(0)
        self.master_layout.addWidget(self.input_cb, 100)

    def get_text(self):
        return self.input_cb.currentText()

    def set_value(self, value):
        self.input_cb.setCurrentIndex(self._OPT_IDX_TO_ACTION.index(value))

    def get_value(self, brick_x: Brick):
        return self._OPT_IDX_TO_ACTION[self.input_cb.currentIndex()](brick_x.get_property(self.name))


class TextDynamicPropertyWidget(DynamicPropertyWidget):

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)
        self.input_le = QLineEdit()
        self.input_le.setText("x")
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(value)

    def get_value(self, brick_x: Brick):
        value = self.input_le.text()
        # This is fine because we do not support operations on strings and if default is x then this will yield x
        if value == "x":
            return brick_x.get_property(self.name)
        return value


class AsciiDynamicPropertyWidget(DynamicPropertyWidget):

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)
        self.input_le = QLineEdit()
        self.input_le.setText("x")
        self.input_le.setValidator(AsciiOnlyValidator())
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(value)

    def get_value(self, brick_x: Brick):
        value = self.input_le.text()
        # This is fine because we do not support operations on strings and if default is x then this will yield x
        if value == "x":
            return brick_x.get_property(self.name)
        return value


class FloatDynamicPropertyWidget(DynamicPropertyWidget):

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)
        self.input_le = ExpressionWidget("x", ExpressionType.MATH_EXPR)
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(str(value))

    def get_value(self, brick_x: Brick):
        return self.input_le.value([
            ExpressionSymbol('x', lambda: brick_x.get_property(self.name), None)
        ])



class Vec2DynamicPropertyWidget(DynamicPropertyWidget):

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)
        self.input_le_x = ExpressionWidget("x", ExpressionType.MATH_EXPR)
        self.input_le_y = ExpressionWidget("x", ExpressionType.MATH_EXPR)
        self.values_layout = QHBoxLayout()
        self.values_layout.addWidget(self.input_le_x)
        self.values_layout.addWidget(self.input_le_y)
        self.master_layout.addLayout(self.values_layout)

    def get_text(self):
        return f"({self.input_le_x.text()}, {self.input_le_y.text()})"

    def set_value(self, value):
        try:
            x, y = value.strip().strip("()").split(",")
        except ValueError:
            return
        self.input_le_x.setText(x)
        self.input_le_y.setText(y)

    def get_value(self, brick_x: Brick):
        return vec.Vec2(
            self.input_le_x.value([ExpressionSymbol("x", lambda: brick_x.get_property(self.name).x, None)]),
            self.input_le_y.value([ExpressionSymbol("x", lambda: brick_x.get_property(self.name).y, None)])
        )


class Vec3DynamicPropertyWidget(DynamicPropertyWidget):

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)
        self.input_le_x = ExpressionWidget("x", ExpressionType.MATH_EXPR)
        self.input_le_y = ExpressionWidget("x", ExpressionType.MATH_EXPR)
        self.input_le_z = ExpressionWidget("x", ExpressionType.MATH_EXPR)
        self.values_layout = QHBoxLayout()
        self.values_layout.addWidget(self.input_le_x)
        self.values_layout.addWidget(self.input_le_y)
        self.values_layout.addWidget(self.input_le_z)
        self.master_layout.addLayout(self.values_layout)

    def get_text(self):
        return f"({self.input_le_x.text()}, {self.input_le_y.text()}, {self.input_le_z.text()})"

    def set_value(self, value):
        try:
            x, y, z = value.strip().strip("()").split(",")
        except ValueError:
            return
        self.input_le_x.setText(x)
        self.input_le_y.setText(y)
        self.input_le_z.setText(z)

    def get_value(self, brick_x: Brick):
        return vec.Vec3(
            self.input_le_x.value([ExpressionSymbol("x", lambda: brick_x.get_property(self.name).x, None)]),
            self.input_le_y.value([ExpressionSymbol("x", lambda: brick_x.get_property(self.name).y, None)]),
            self.input_le_z.value([ExpressionSymbol("x", lambda: brick_x.get_property(self.name).z, None)])
        )



class Integer8DynamicPropertyWidget(DynamicPropertyWidget):

    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)
        self.input_le = ExpressionWidget("x", ExpressionType.MATH_EXPR, clamps=(-128, 127))
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(str(value))

    def get_value(self, brick_x: Brick):
        value = self.input_le.value([
            ExpressionSymbol('x', lambda: brick_x.get_property(self.name), None)
        ])
        match value:
            case float('inf'):
                return 127
            case float('-inf'):
                return -128
            case float('nan'):
                return 0
            case _:
                return int(value)



class UnknownDynamicPropertyWidget(DynamicPropertyWidget):
    
    def __init__(self, name: str, display_name: str, parent=None):
        super().__init__(name, display_name, parent)

        self.input_le = QLineEdit()
        self.input_le.setText(f"Not Supported")
        self.input_le.setReadOnly(True)
        self.input_le.setEnabled(False)
        self.master_layout.addWidget(self.input_le, 100)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(f"NS: {str(value)}")

    def get_value(self, brick_x):
        raise ValueError("Cannot get value of unknown property")
