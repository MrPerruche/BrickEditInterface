from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel, QComboBox
from PySide6.QtGui import QIcon

from menus import base
from ..shared_widgets import LargeLabel, ListSlider, ExpressionWidget, ExpressionType
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
        self.compression_ll = LargeLabel("Brick optimization", 4)
        self.master_layout.addWidget(self.compression_ll)

        # FUSION METHOD
        # Fusion label / layout
        self.fusion_method_lay = QHBoxLayout()
        self.fusion_method_l = QLabel("Optimization method")
        self.fusion_method_lay.addWidget(self.fusion_method_l, _LABEL_SIZE)
        # Fusion method
        self.fusion_method_combo = QComboBox()
        self.fusion_method_combo_opts = ["No optimizations", "2D Merging", "3D Greedy stacking", "3D Stacking (slow)"]
        self.fusion_method_combo.addItems(self.fusion_method_combo_opts)
        self.fusion_method_combo.setCurrentIndex(1)
        self.fusion_method_combo.currentIndexChanged.connect(self.update_fusion_info)
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

        # 3D Fusion step
        self.f3d_step_info_l = QLabel("No information...")
        self.f3d_step_info_l.setWordWrap(True)
        self.f3d_settings_lay.addWidget(self.f3d_step_info_l)
        self.f3d_step_ls = ListSlider(list(_LIST_SLIDER_OPTIONS.keys()), _LS_NEG//2, lambda x: f"{_LIST_SLIDER_OPTIONS[x]} cm")
        self.f3d_step_ls.slider.valueChanged.connect(self.update_fusion_info)
        self.f3d_settings_lay.addWidget(self.f3d_step_ls)

        # 3D Fusion layers
        # Information widget
        # Laoyut
        self.f3d_layers_lay = QHBoxLayout()
        self.f3d_settings_lay.addLayout(self.f3d_layers_lay)
        # Label
        self.f3d_layers_l = QLabel("Max layers")
        self.f3d_layers_lay.addWidget(self.f3d_layers_l, _LABEL_SIZE)
        # Expression
        self.f3d_layers_ew = ExpressionWidget("16", ExpressionType.INTEGER, (2, 100))
        self.f3d_layers_ew.editingFinished.connect(self.update_fusion_info)
        self.f3d_layers_lay.addWidget(self.f3d_layers_ew, 25)


        # Note: This will be included in every brick instead.
        """
        self.f3d_layers_info_l = QLabel("No information...")
        self.f3d_layers_info_l.setWordWrap(True)
        self.f3d_settings_lay.addWidget(self.f3d_layers_info_l)

        ...

        # IMAGE WIDTH
        # Layout and label
        self.image_width_lay = QHBoxLayout()
        self.master_layout.addLayout(self.image_width_lay)
        self.image_width_l = QLabel("Image plate width")
        self.image_width_lay.addWidget(self.image_width_l, _LABEL_SIZE)
        # Expression Widget
        self.image_width_ew = ExpressionWidget("1.0", ExpressionType.FLOAT, (0, None))
        self.image_width_ew.editingFinished.connect(self.update_fusion_info)
        self.image_width_lay.addWidget(self.image_width_ew, 25)
        # Unit
        self.image_width_unit_l = QLabel("cm")
        self.image_width_lay.addWidget(self.image_width_unit_l, 0)
        """



        # Update fusion
        self.update_fusion_info()
        # Other
        self.master_layout.addStretch()

    # -------------

    def update_fusion_info(self):

        # Set enabled?
        index = self.fusion_method_combo.currentIndex()
        self.f3d_settings_widget.setEnabled(index in (2, 3))

        # Set distance info label
        raw_value = self.f3d_step_ls.get_value()
        value = raw_value * 0.000_1  # cm → km
        tol = max_float32_for_tolerance(value)
        text = f"The image will Z-fight if you go further than {tol:.1f} km from origin."
        self.f3d_step_info_l.setText(text)

    # -------------

    def get_menu_name(self):
        return "Image Importer"

    def get_icon(self):
        return QIcon(":/assets/icons/ImageIcon.png")
