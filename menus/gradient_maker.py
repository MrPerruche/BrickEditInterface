import os
from PySide6.QtWidgets import QRadioButton, QButtonGroup
from PySide6.QtGui import QIcon

from . import base
from .widgets import *

from enum import Enum
from dataclasses import dataclass

@dataclass(frozen=True)
class ColorSpace:
    name: str
    extended_name: str
    info: str | None
    code: str

class ColorSpaces(Enum):
    OKLAB = ColorSpace("Oklab", "Lightness Green-Red Blue-Yellow", "perceptual, recommended", "oklab")
    OKLCH = ColorSpace("Oklch", "Lightness Chroma Hue", "perceptual, most recommended", "oklch")
    LINEAR_RGB = ColorSpace("Linear RGB", "Red Green Blue", None, "linear_rgb")
    SRGB = ColorSpace("sRGB", "Red Green Blue", "produce dull colors", "srgb")
    HSV = ColorSpace("HSV", "Hue Saturation Value", "used by Brick Rigs", "hsv")
    # HSL = ColorSpace("HSL", "Hue Saturation Lightness", None)
    # CMYK = ColorSpace("CMYK", "Cyan Magenta Yellow Black / Key", None)

ID_TO_COLORSPACE = [ColorSpaces.OKLAB, ColorSpaces.OKLCH, ColorSpaces.LINEAR_RGB, ColorSpaces.SRGB, ColorSpaces.HSV]
COLORSPACE_TO_ID = {colorspace: i for i, colorspace in enumerate(ID_TO_COLORSPACE)}



class GradientMaker(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)
        
        # Values
        self.color_space = COLORSPACE_TO_ID[ColorSpaces.OKLCH]


        # Color selector
        self.col_sel_widget = MultiColorSelectorWidget()
        self.master_layout.addWidget(self.col_sel_widget)


        # Settings:
        # Layout
        self.settings_widget = SquareWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        self.master_layout.addWidget(self.settings_widget)
        
        # Num bricks
        self.bricks_layout = QHBoxLayout()
        self.settings_layout.addLayout(self.bricks_layout)
        self.num_bricks_label = QLabel("Bricks:")
        self.bricks_layout.addWidget(self.num_bricks_label)
        self.num_bricks_spin = SafeMathLineEdit(12, min_val=2, max_val=5_000, integer=True)
        self.bricks_layout.addWidget(self.num_bricks_spin)
        
        
        # Colorspace label & buttons
        self.colorspace_label = QLabel("Interpolation color space")
        self.colorspace_label.setWordWrap(True)
        self.settings_layout.addWidget(self.colorspace_label)
        
        self.colorspace_buttons = []
        self.colorspace_sel_group = QButtonGroup()
        self.colorspace_sel_group.setExclusive(True)

        for i, colorspace in enumerate(ID_TO_COLORSPACE):
            radio_button = QRadioButton(f"{colorspace.value.name}" + (f" ({colorspace.value.info})" if colorspace.value.info else ""))
            self.colorspace_sel_group.addButton(radio_button, i)
            if i == self.color_space:
                radio_button.setChecked(True)
            self.colorspace_buttons.append(radio_button)
            self.settings_layout.addWidget(radio_button)

        self.lerp_settings_label = QLabel("Interpolation settings")
        self.lerp_settings_label.setWordWrap(True)
        self.settings_layout.addWidget(self.lerp_settings_label)

        self.longer_hue = QRadioButton("Longer Hue (HSV and Oklch only)")
        self.longer_hue.setChecked(False)
        self.settings_layout.addWidget(self.longer_hue)

        self.colorspace_sel_group.buttonClicked.connect(self.update_colorspace)



        # Display vehicle
        self.vehicle_selector = VehicleWidget(VehicleWidgetMode.DISPLAY_ONLY, must_deserialize=False)
        self.vehicle_path = os.path.join(get_vehicles_path(), "bei-gradient")
        self.vehicle_selector.load_vehicle(self.vehicle_path, silent=True)
        self.master_layout.addWidget(self.vehicle_selector)


        self.update_colorspace()
        self.master_layout.addStretch()


    def update_colorspace(self):
        self.color_space = self.colorspace_sel_group.checkedId()
        if self.color_space in (COLORSPACE_TO_ID[ColorSpaces.HSV], COLORSPACE_TO_ID[ColorSpaces.OKLCH]):
            self.longer_hue.setEnabled(True)
        else:
            self.longer_hue.setChecked(False)
            self.longer_hue.setEnabled(False)

    def get_menu_name(self):
        return "Gradient Maker"

    def get_icon(self):
        return QIcon(":/assets/icons/GradientIcon.png")


    def create_vehicle(self):
        pass