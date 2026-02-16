from PySide6.QtWidgets import QSlider, QHBoxLayout, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt

from typing import Any, Callable

class ListSlider(QWidget):

    def __init__(
        self,
        elements: list,
        default = 0,
        label_name_provider: Callable[[Any], str] = None,
        slider_spacing: int = 25,
        parent = None
    ):
        super().__init__(parent)
        assert len(elements) >= 2, "Not enough elements"

        self.elements = elements
        self.label_name_provider = label_name_provider if label_name_provider is not None else lambda x: "N/A"

        self.master_layout = QHBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, len(elements) - 1)
        self.slider.setValue(min(default, len(elements) - 1))
        self.master_layout.addWidget(self.slider, slider_spacing)

        self.label = QLabel(self.label_name_provider(elements[self.slider.value()]))
        self.label.setAlignment(Qt.AlignRight)
        self.label.setWordWrap(True)
        if label_name_provider is not None:
            self.master_layout.addWidget(self.label, 10)

        self.slider.valueChanged.connect(lambda idx: self.label.setText(self.label_name_provider(self.elements[idx])))


    def get_value(self):
        return self.elements[self.slider.value()]


    def set_idx(self, idx):
        self.slider.setValue(min(idx, len(self.elements) - 1))


    def set_parameters(self, elements: list, idx=None):

        current_element = self.elements[self.value()]
        self.elements = elements
        self.slider.setRange(0, len(elements) - 1)
        if idx is not None:
            self.slider.setValue(min(idx, len(elements) - 1))
        elif current_element in self.elements:
            self.slider.setValue(self.elements.index(current_element))
        self.label.setText(self.label_name_provider(self.elements[self.value()]))