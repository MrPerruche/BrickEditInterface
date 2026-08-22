from PySide6.QtGui import QIcon

from PIL import Image

from menus import base

from .widgets import ImageSelector
from ui.widgets import Button, ComboBox, StyledLabel, LabelStyle, Slider
from ui.components.brick.property_widgets import FloatPropertyWidget
from ui.models import TooltipContents

from utils import max_float32_for_tolerance, get_vehicles_path
from . import image_utils

from enum import Enum
import os

_LABEL_SIZE = 10

_LS_SIZE = 15
_LS_NEG = 10
_LIST_SLIDER_OPTIONS = {2**(i-_LS_NEG): (f"1/{2**(_LS_NEG-i)}" if i < _LS_NEG else f"{2**(i-_LS_NEG)}") for i in range(_LS_SIZE)}


class Quantization(Enum):
    NO = 0
    MEDIAN_CUT = 1
    KMEANSPP_LAB = 2

    @staticmethod
    def get_names():
        return [
            "No quantization",
            "Median cut",
            "K-means++ in OKLAB"
        ]

    def get_name(self):
        return Quantization.get_names()[self.value]



class ImageImporter(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)


        # ----- IMAGE SELECTION -----

        self.image_selector = ImageSelector(store_pil_img=True)
        self.image = None
        #self.image_selector.new_image_selected.connect(self.on_image_reload)
        self.master_layout.addWidget(self.image_selector)

        # Optimization
        self.optimization_methods: tuple[str] = (
            "No optimizations",
            "2D merging",
            "3D greedy stacking",
            "3D stacking (slow)"
        )

        self.optimization_label = StyledLabel("Brick optimization", LabelStyle.HEADER_5)
        self.master_layout.addWidget(self.optimization_label)

        self.optimization_method_label = StyledLabel("OPTIMIZATION METHOD", LabelStyle.SUBTEXT_1)
        self.master_layout.addWidget(self.optimization_method_label)

        self.optimization_method: ComboBox = ComboBox()
        for method in self.optimization_methods:
            self.optimization_method.add_item(method)
        self.master_layout.addWidget(self.optimization_method)
        self.optimization_method.item_changed.connect(self.update_fpe_info_visible)

        self.fpe_info = StyledLabel("The image will Z-fight if you go further than x km from world center.", LabelStyle.SUBTEXT_0)
        self.master_layout.addWidget(self.fpe_info)
        self.fpe_info.hide()
        #self.fpe_slider = Slider(range)

        # Max layers
        self.max_layers: int = 24
        self.max_layers_label = StyledLabel("MAX LAYERS", LabelStyle.SUBTEXT_1)
        self.master_layout.addWidget(self.max_layers_label)
        self.max_layers_slider = Slider(range(2, 100), 24)
        self.master_layout.addWidget(self.max_layers_slider)
        self.update_max_layers()
        self.max_layers_slider.value_changed.connect(self.update_max_layers)

        # Quantization
        self.quantization_label = StyledLabel("QUANTIZATON ALGORITHM", LabelStyle.SUBTEXT_1)
        self.master_layout.addWidget(self.quantization_label)
        self.quantization_algorithm = ComboBox()
        for algorithm in Quantization.get_names():
            self.quantization_algorithm.add_item(algorithm)
        self.master_layout.addWidget(self.quantization_algorithm)
        self.quantization_algorithm.item_changed.connect(self.update_colors_option_visible)

        self.color_count: int = 24
        self.colors_label = StyledLabel("COLOR COUNT", LabelStyle.SUBTEXT_1)
        self.master_layout.addWidget(self.colors_label)
        self.colors_slider = Slider(range(2, 255), 24)
        self.master_layout.addWidget(self.colors_slider)
        self.colors_slider.value_changed.connect(self.update_color_count)
        self.colors_slider.hide()
        self.colors_label.hide()
        self.update_color_count()

        self.master_layout.addStretch()

    def update_max_layers(self):
        self.max_layers = self.max_layers_slider.get_value()
        self.max_layers_slider.set_text(f"{self.max_layers}", 25)

    def update_fpe_info_visible(self):
        self.fpe_info.setVisible(self.optimization_method.get_current_idx() not in (0, 1))

    def update_colors_option_visible(self):
        self.colors_slider.setVisible(self.quantization_algorithm.get_current_idx() != 0)
        self.colors_label.setVisible(self.quantization_algorithm.get_current_idx() != 0)

    def update_color_count(self):
        self.color_count = self.colors_slider.get_value()
        self.colors_slider.set_text(f"{self.color_count}", 25)

    def get_menu_name(self):
        return "Image Importer"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/ImageIcon.png"), True)
