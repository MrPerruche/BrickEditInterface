from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon

from PIL import Image

from menus import base

from ui.widgets import Button, ComboBox, StyledLabel, LabelStyle, Label, Slider, Surface
from ui.components.image.image_selector import ImageSelector
from ui.models import TooltipContents

from utils import max_float32_for_tolerance

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

    @staticmethod
    def from_idx(self, idx):
        return [
            Quantization.NO,
            Quantization.MEDIAN_CUT,
            Quantization.KMEANSPP_LAB
        ][idx]



WHAT_IS_ZFIGHTING = TooltipContents(
    "What is Z-fighting?",
    "When objects are too far from world center, the game can't tell "
    "which one is in front. This issue causes visual glitches (flickering)."
)
STACKING_3D_OPTIMIZATION = TooltipContents(
    "3D Stacking consist in dividing the image into layers which are "
    "stacked on top of each other. Doing this may reduce brick count "
    "very significantly but has cons."
)
WHAT_IS_QUANTIZATION = TooltipContents(
    "What is quantization?",
    "Quantization reduces the number of color in an image. "
    "Having less colors makes optimizations MUCH more efficient (if any is selected).\n"
    "Tip: K-means++ in OKLAB will typically give the best results."    
)


class ImageImporter(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)


        # ----- IMAGE SELECTION -----

        self.image_selector = ImageSelector()
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

        self.optimization_label = StyledLabel("Optimization settings", LabelStyle.HEADER_3)
        self.master_layout.addWidget(self.optimization_label)

        # OPTIMIZATION METHOD
        self.optimization_method_layout = QHBoxLayout()
        self.optimization_method_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.optimization_method_layout)

        self.optimization_method_label = Label("Optimization method")
        self.optimization_method_layout.addWidget(self.optimization_method_label)

        self.optimization_method: ComboBox = ComboBox()
        for method in self.optimization_methods:
            self.optimization_method.add_item(method)
        self.optimization_method.item_changed.connect(self.on_optimization_method_changed)
        self.optimization_method_layout.addWidget(self.optimization_method)



        # OPTIMIZATION METHOD SETTINGS
        self.oms3d_widget = Surface()
        self.master_layout.addWidget(self.oms3d_widget)
        self.oms3d_widget.hide()
        self.oms3d_layout = self.oms3d_widget.layout()
        self.oms3d_title = StyledLabel("Optimization method settings", LabelStyle.LARGE_5)
        self.oms3d_layout.addWidget(self.oms3d_title)


        # Max layers
        self.max_layers: int = 24
        self.max_layers_label = Label("Max layers")
        self.max_layers_label.set_tooltip(STACKING_3D_OPTIMIZATION)
        self.oms3d_layout.addWidget(self.max_layers_label)

        self.max_layers_slider = Slider(range(2, 100), 24)
        self.oms3d_layout.addWidget(self.max_layers_slider)
        self.max_layers_slider.value_changed.connect(self.update_max_layers)
        self.update_max_layers()

        # Layer thickness
        self.layer_thicknes_label = Label("Layer thickness")
        self.layer_thicknes_label.set_tooltip(STACKING_3D_OPTIMIZATION)
        self.oms3d_layout.addWidget(self.layer_thicknes_label)

        self.layer_thickness_slider = Slider(list(_LIST_SLIDER_OPTIONS.keys()), _LS_NEG//2+1)
        self.layer_thickness_slider.value_changed.connect(self.update_layer_thickness)
        self.oms3d_layout.addWidget(self.layer_thickness_slider)
        self.update_layer_thickness()


        # Z-fighting notice
        self.fpe_info = Label("The image will Z-fight if you go further than x km from world center.")
        self.fpe_info.set_tooltip(WHAT_IS_ZFIGHTING)
        self.oms3d_layout.addWidget(self.fpe_info)
        #self.fpe_slider = Slider(range)



        # QUANTIZATION SETTINGS
        self.quantization_layout = QHBoxLayout()
        self.quantization_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.quantization_layout)

        self.quantization_label = Label("Quantization")
        self.quantization_label.set_tooltip(WHAT_IS_QUANTIZATION)
        self.quantization_layout.addWidget(self.quantization_label)

        self.quantization_algorithm = ComboBox()
        for algorithm in Quantization.get_names():
            self.quantization_algorithm.add_item(algorithm)
        self.quantization_algorithm.item_changed.connect(self.on_quantization_algorithm_changed)
        self.quantization_layout.addWidget(self.quantization_algorithm)



        # QUANTIZATION METHOD SETTINGS
        self.quantization_settings_widget = Surface()
        self.master_layout.addWidget(self.quantization_settings_widget)
        self.quantization_settings_layout = self.quantization_settings_widget.layout()
        self.quantization_settings_title = StyledLabel("Quantization settings", LabelStyle.LARGE_5)
        self.quantization_settings_layout.addWidget(self.quantization_settings_title)

        self.color_count: int = 24
        self.colors_slider = Slider(range(2, 255), 24)
        self.quantization_settings_layout.addWidget(self.colors_slider)
        self.colors_slider.value_changed.connect(self.update_color_count)
        self.update_color_count()


        # CHANGE SETTINGS
        self.optimization_method.set_current_idx(1)
        self.quantization_algorithm.set_current_idx(2)


        self.master_layout.addStretch()



    def on_optimization_method_changed(self):
        idx = self.optimization_method.get_current_idx()
        self.oms3d_widget.setHidden(idx in (0, 1))


    def on_quantization_algorithm_changed(self):
        idx = self.quantization_algorithm.get_current_idx()
        self.quantization_settings_widget.setVisible(idx != 0)



    def update_max_layers(self):
        self.max_layers = self.max_layers_slider.get_value()
        self.max_layers_slider.set_text(f"{self.max_layers} layers", 60)

    def update_layer_thickness(self):
        self.layer_thickness_slider.set_text(f"{_LIST_SLIDER_OPTIONS[self.layer_thickness_slider.get_value()]} cm", 62)

    def update_color_count(self):
        self.color_count = self.colors_slider.get_value()
        self.colors_slider.set_text(f"{self.color_count} colors", 61)

    def get_menu_name(self):
        return "Image Importer"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/ImageIcon.png"), True)
