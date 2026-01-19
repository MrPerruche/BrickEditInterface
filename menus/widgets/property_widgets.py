from .square_widget import SquareWidget
from .float_line_edit import SafeMathLineEdit

from custom_validators import *

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import Qt
from brickedit.src.brickedit import p, vec


class PropertyWidget(SquareWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(parent)
        
        self.master_layout = QVBoxLayout(self)
        self.default_value = default_value
        self.setLayout(self.master_layout)
        
        self.name = name
        self.display_name = display_name
        self.display_name_label = QLabel(display_name)
        self.master_layout.addWidget(self.display_name_label)

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
        if isinstance(pmeta, type) and issubclass(pmeta, p.TextMeta):
            return TextPropertyWidget(prop, display_name, value)
        if isinstance(pmeta, type) and issubclass(pmeta, p.EnumMeta):
            return AsciiPropertyWidget(prop, display_name, value)
        if isinstance(pmeta, type) and issubclass(pmeta, p.Float32Meta):
            return FloatPropertyWidget(prop, display_name, value)
        if isinstance(pmeta, type) and issubclass(pmeta, p.Vec2Meta): pass
            # return Vec2PropertyWidget(prop, display_name, value)

        return UnknownPropertyWidget(prop, display_name, value)

    def get_dict_pair(self):
        return (self.name, self.get_value())


class TextPropertyWidget(PropertyWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.input_le = QLineEdit()
        self.input_le.setText(self.default_value)
        self.master_layout.addWidget(self.input_le)

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
        self.master_layout.addWidget(self.input_le)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(value)

    def get_value(self):
        return self.input_le.text()


class FloatPropertyWidget(PropertyWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.input_le = SafeMathLineEdit(float(default_value))
        self.master_layout.addWidget(self.input_le)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(str(value))

    def get_value(self):
        try:
            return float(self.input_le.text())
        except ValueError:
            return self.default_value


class Vec2PropertyWidget(PropertyWidget):
    def __init__(self, name: str, display_name: str, default_value: str, parent=None):
        super().__init__(name, display_name, default_value, parent)
        self.values_layout = QHBoxLayout()
        self.master_layout.addLayout(self.values_layout)

        x, y = default_value.strip().strip("()").split(",")

        self.input_le_x = SafeMathLineEdit(float(x))
        self.values_layout.addWidget(self.input_le_x)
        self.input_le_y = SafeMathLineEdit(float(y))
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





# -----

class UnknownPropertyWidget(PropertyWidget):
    
    def __init__(self, name: str, property_display_name: str, default_value: str, parent=None):
        super().__init__(name, property_display_name, default_value, parent)

        self.input_le = QLineEdit()
        self.input_le.setText(f"Unsupported: {str(self.default_value)}")
        self.input_le.setReadOnly(True)
        self.master_layout.addWidget(self.input_le)

    def get_text(self):
        return self.input_le.text()

    def set_value(self, value):
        self.input_le.setText(f"Unsupported: {str(value)}")

    def get_value(self):
        return self.input_le.text().strip("Unsupported: ")
