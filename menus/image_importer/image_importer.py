from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QLabel, QComboBox, QRadioButton, QButtonGroup, QStackedWidget
from PySide6.QtGui import QIcon

from PIL import Image

from menus import base
from ..shared_widgets import LargeLabel, ListSlider, ExpressionWidget, ExpressionType, VehicleWidget, VehicleWidgetMode
from .widgets import ImageSelector

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
        self.image_selector.new_image_selected.connect(self.on_image_reload)
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

        # QUANTIZATION ALGORITHM
        # Layout
        self.quant_alg_lay = QHBoxLayout()
        self.master_layout.addLayout(self.quant_alg_lay)
        # Label
        self.quant_alg_l = QLabel("Quantization algorithm")
        self.quant_alg_lay.addWidget(self.quant_alg_l, _LABEL_SIZE)
        # Method checkbox
        self.quant_alg_cb = QComboBox()
        self.quant_alg_cb_opts = Quantization.get_names()
        self.quant_alg_cb.addItems(self.quant_alg_cb_opts)
        self.quant_alg_cb.setCurrentIndex(2)
        self.quant_alg_cb.currentIndexChanged.connect(self.update_quantization_info)
        self.quant_alg_lay.addWidget(self.quant_alg_cb, 25)

        # QUANTIZATION METHOD SETTINGS
        self.quant_no_lay = self.make_quant_no_layout()
        self.quant_no = QWidget()
        self.quant_no.setLayout(self.quant_no_lay)
        self.master_layout.addWidget(self.quant_no)

        self.quant_mc_lay = self.make_quant_mc_layout()
        self.quant_mc = QWidget()
        self.quant_mc.setLayout(self.quant_mc_lay)
        self.master_layout.addWidget(self.quant_mc)

        self.quant_km_lay = self.make_quant_km_layout()
        self.quant_km = QWidget()
        self.quant_km.setLayout(self.quant_km_lay)
        self.master_layout.addWidget(self.quant_km)

        self.quant_settings = [
            self.quant_no,
            self.quant_mc,
            self.quant_km
        ]


        # ----- IMPORT -----
        self.import_ll = LargeLabel("Import image", 4)
        self.master_layout.addWidget(self.import_ll)

        # METHOD SELECTION
        # Layout and label
        self.import_method_lay = QHBoxLayout()
        self.master_layout.addLayout(self.import_method_lay)
        # self.import_method_l = QLabel("Import method")
        # self.import_method_lay.addWidget(self.import_method_l, _LABEL_SIZE)

        self.import_method_lay.addStretch(1)

        # Radio buttons
        self.import_method_new_rb = QRadioButton("Create new")
        self.import_method_new_rb.setChecked(True)
        self.import_method_lay.addWidget(self.import_method_new_rb)

        self.import_method_lay.addStretch(1)

        self.import_method_load_rb = QRadioButton("Replace bricks")
        self.import_method_lay.addWidget(self.import_method_load_rb)

        self.import_method_lay.addStretch(1)

        # Make them mutually exclusive
        self.import_method_group = QButtonGroup()
        self.import_method_group.addButton(self.import_method_new_rb, id=0)
        self.import_method_group.addButton(self.import_method_load_rb, id=1)
        self.import_method_group.idClicked.connect(self.on_import_method_changed)
        self.import_method_group.setExclusive(True)


        # ----- NEW IMPORT -----
        # CREATE NEW LAYOUT
        self.nim_lay = QVBoxLayout()
        self.nim_lay.setContentsMargins(0, 0, 0, 0)
        self.nim_widget = QWidget()
        self.nim_widget.setLayout(self.nim_lay)

        self.nim_vehicle_selector = VehicleWidget(
            VehicleWidgetMode.CREATION,
            must_deserialize=False,
            vehicle_name="bei-image"
        )
        self.nim_vehicle_selector.vehicle_name.editingFinished.connect(self.on_new_nim_vehicle)
        self.nim_lay.addWidget(self.nim_vehicle_selector)

        # ----- EDIT IMPORT -----
        self.cim_lay = QVBoxLayout()
        self.cim_lay.setContentsMargins(0, 0, 0, 0)
        self.cim_widget = QWidget()
        self.cim_widget.setLayout(self.cim_lay)

        self.cim_vehicle_selector = VehicleWidget(
            VehicleWidgetMode.SELECT_ONLY
        )
        self.cim_lay.addWidget(self.cim_vehicle_selector)

        # ----- IMPORT SETTINGS -----
        self.import_settings_sw = QStackedWidget()
        self.import_settings_sw.addWidget(self.nim_widget)
        self.import_settings_sw.addWidget(self.cim_widget)
        self.master_layout.addWidget(self.import_settings_sw)

        # Update fusion / run load logic
        self.update_fusion_info()
        self.update_quantization_info()
        self.on_image_reload()
        self.on_import_method_changed(self.import_method_group.checkedId())
        # Other
        self.master_layout.addStretch()



    def make_quant_no_layout(self):
        self.quant_no_lay = QVBoxLayout()
        self.quant_no_lay.setContentsMargins(0, 0, 0, 0)
        self.quant_no_l = QLabel("No quantization settings.")
        self.quant_no_l.setEnabled(False)
        self.quant_no_lay.addWidget(self.quant_no_l)
        return self.quant_no_lay

    def make_quant_mc_layout(self):
        # Layout
        self.quant_mc_lay = QHBoxLayout()
        self.quant_mc_lay.setContentsMargins(0, 0, 0, 0)
        # Label
        self.quant_mc_l = QLabel("Colors")
        self.quant_mc_lay.addWidget(self.quant_mc_l, _LABEL_SIZE)
        # Input
        MIN, DEF, MAX = 2, 16, 255
        self.quant_mc_ew = ExpressionWidget(str(DEF), ExpressionType.INTEGER, (MIN, MAX))
        self.quant_mc_lay.addWidget(self.quant_mc_ew, 25)
        return self.quant_mc_lay

    def make_quant_km_layout(self):
        # Layout
        self.quant_km_lay = QHBoxLayout()
        self.quant_km_lay.setContentsMargins(0, 0, 0, 0)
        # Label
        self.quant_km_l = QLabel("Colors")
        self.quant_km_lay.addWidget(self.quant_km_l, _LABEL_SIZE)
        # Input
        MIN, DEF, MAX = 2, 16, 255
        self.quant_km_ew = ExpressionWidget(str(DEF), ExpressionType.INTEGER, (MIN, MAX))
        self.quant_km_lay.addWidget(self.quant_km_ew, 25)
        return self.quant_km_lay
        

    # -------------

    def update_fusion_info(self):

        # Set enabled?
        index = self.fusion_method_combo.currentIndex()
        self.f3d_settings_widget.setEnabled(index in (2, 3))

        # Set distance info label
        raw_value = self.f3d_step_ls.get_value()
        value = raw_value * 0.000_1  # cm → km
        tol = max_float32_for_tolerance(value)
        text = f"The image will Z-fight if you go further than {tol:.1f} km from world center."
        self.f3d_step_info_l.setText(text)


    def update_quantization_info(self):

        # Show the right settings layout
        current_mode_idx = self.quant_alg_cb.currentIndex()
        for i, widget in enumerate(self.quant_settings):
            widget.setVisible(i == current_mode_idx)


    def on_image_reload(self):
        
        img_path = self.image_selector.img_path
        if img_path is None:
            return
        if self.image is None:
            self.image = Image.open(img_path)


    def on_import_method_changed(self, idx: int):
        self.import_settings_sw.setCurrentIndex(idx)


    def on_new_nim_vehicle(self):
        name = self.nim_vehicle_selector.vehicle_name.text()
        self.nim_vehicle_selector.load_vehicle(
            os.path.join(get_vehicles_path(), name),
            silent=True
        )


    # -------------

    def recover_og_image(self):
        pil_img = self.image_selector.pil_img
        if pil_img is None:
            img_path = self.image_selector.img_path
            if img_path is None:
                return
            self.image = Image.open(img_path)
        else:
            self.image = pil_img.copy()


    # -------------

    def get_menu_name(self):
        return "Image Importer"

    def get_icon(self):
        return QIcon(":/assets/icons/ImageIcon.png")
