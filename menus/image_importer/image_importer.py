from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtGui import QIcon

from menus import base
from ..shared_widgets import LargeLabel, ListSlider
from .widgets import ImageSelector

from utils import max_float32_for_tolerance

_LABEL_SIZE = 10

_LS_SIZE = 15
_LS_NEG = 10
_LIST_SLIDER_OPTIONS = {2**(i-_LS_NEG): (f"1/{2**(_LS_NEG-i)}" if i < _LS_NEG else f"{2**(i-_LS_NEG)}") for i in range(_LS_SIZE)}



class ImageImporter(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)


        # ----- IMAGE SELECTION -----

        self.image_selector = ImageSelector()
        self.master_layout.addWidget(self.image_selector)


        # ----- COMPRESSION SETTINGS -----
        # LABEL
        self.compression_ll = LargeLabel("Compression", 4)
        self.master_layout.addWidget(self.compression_ll)

        # FUSION METHOD
        # Fusion label / layout
        self.fusion_method_lay = QHBoxLayout()
        self.fusion_method_l = QLabel("Import method")
        self.fusion_method_lay.addWidget(self.fusion_method_l, _LABEL_SIZE)
        # Fusion method
        self.fusion_method_combo = QComboBox()
        self.fusion_method_combo_opts = ["No optimizations", "Flat optimizations", "3D Greedy stacking", "3D Stacking (slow)"]
        self.fusion_method_combo.addItems(self.fusion_method_combo_opts)
        self.fusion_method_combo.setCurrentIndex(1)
        self.fusion_method_combo.currentIndexChanged.connect(self.fusion_method_changed)
        self.fusion_method_lay.addWidget(self.fusion_method_combo, 25)
        self.master_layout.addLayout(self.fusion_method_lay)

        # 3D FUSION SETTINGS
        # f3d = Fusion 3D

        # 3D Fusion layout
        self.f3d_settings_lay = QVBoxLayout()
        self.f3d_settings_lay.setContentsMargins(0, 0, 0, 0)
        self.f3d_settings_widget = QWidget()
        self.f3d_settings_widget.setLayout(self.f3d_settings_lay)
        self.master_layout.addWidget(self.f3d_settings_widget)

        # 3D Fusion direction label
        self.f3d_direction_lay = QHBoxLayout()
        self.f3d_settings_lay.addLayout(self.f3d_direction_lay)
        self.f3d_direction_l = QLabel("Compromized direction")
        self.f3d_direction_lay.addWidget(self.f3d_direction_l, _LABEL_SIZE)
        # 3D Fusion direction selector
        self.f3d_direction_combo = QComboBox()
        self.f3d_direction_combo_opts = ["Inwards", "Outwards"]
        self.f3d_direction_combo.addItems(self.f3d_direction_combo_opts)
        self.f3d_direction_combo.setCurrentIndex(0)
        self.f3d_direction_lay.addWidget(self.f3d_direction_combo, 25)

        # 3D Fusion step
        self.f3d_step_info_l = QLabel("No information...")
        self.f3d_step_info_l.setWordWrap(True)
        self.f3d_settings_lay.addWidget(self.f3d_step_info_l)
        self.f3d_step_ls = ListSlider(list(_LIST_SLIDER_OPTIONS.keys()), _LS_NEG//2, lambda x: f"{_LIST_SLIDER_OPTIONS[x]} cm")
        self.f3d_step_ls.slider.valueChanged.connect(self.set_distance_info_label)
        self.f3d_settings_lay.addWidget(self.f3d_step_ls)

        # Update fusion
        self.fusion_method_changed(self.fusion_method_combo.currentIndex())
        self.set_distance_info_label()

        self.master_layout.addStretch()

    # -------------

    def fusion_method_changed(self, index):
        self.f3d_settings_widget.setEnabled(index in (2, 3))

    def set_distance_info_label(self):
        value = self.f3d_step_ls.get_value() * 0.000_1  # cm → km
        tol = max_float32_for_tolerance(value)
        text = f"The image will Z-fight if you go further than {tol:.1f} km from origin."
        self.f3d_step_info_l.setText(text)

    # -------------

    def get_menu_name(self):
        return "Image Importer"

    def get_icon(self):
        return QIcon(":/assets/icons/ImageIcon.png")
