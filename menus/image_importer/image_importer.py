from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon

from PIL import ImageFilter

from menus import base

from ui.widgets import Button, ComboBox, StyledLabel, LabelStyle, Label, Slider, Surface, Separator, BoolSwitch
from ui.components.image.image_selector import ImageSelector
from ui.components import Tutorial
from ui.models import TooltipContents
from ui.dialogs import VehicleLoadingIssueDialog, CannotSaveOverLimit

from menus.image_importer.dialogs.import_progress import ImportProgressDialog
from menus.image_importer.img_conversion.decompose_worker import DecomposeWorker, DecomposeResult, launch_with_threading
from menus.image_importer.img_conversion.image_layers import decompose_image
from menus.image_importer.img_conversion.quantize import quantize_image
from menus.image_importer.img_conversion.image_misc_utils import srgb_to_linear
from menus.image_importer.widgets.img_resolution_setting import ImgResolutionSetting
from utils import max_float32_for_tolerance

from enum import Enum
import os

import brickedit


_LABEL_SIZE = 10

_LS_SIZE = 15
_LS_NEG = 10
_LIST_SLIDER_OPTIONS = {2**(i-_LS_NEG): (f"1/{2**(_LS_NEG-i)}" if i < _LS_NEG else f"{2**(i-_LS_NEG)}") for i in range(_LS_SIZE)}
_INV_LIST_SLIDER_OPTIONS = {v: k for k, v in _LIST_SLIDER_OPTIONS.items()}

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
    def from_idx(idx) -> 'Quantization':
        return [
            Quantization.NO,
            Quantization.MEDIAN_CUT,
            Quantization.KMEANSPP_LAB
        ][idx]


BLUR_LEVELS = (
    [i/100 for i in range(0, 30, 2)] +
    [i/100 for i in range(30, 2_00, 10)] +
    [i/100 for i in range(2_00, 4_00, 20)] +
    [i/100 for i in range(4_00, 10_00, 50)] +
    [i/100 for i in range(10_00, 20_00, 200)] +
    [i/100 for i in range(20_00, 50_00+1, 500)]
)

COLOR_LEVELS = (
    [i for i in range(2, 65)] +
    [i for i in range(65, 255+1, 5)]
)


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
WHY_BLUR = TooltipContents(
    "Why blur?",
    "Noisy images can make fuzzy edges when images are quantized. These fuzzy edges defeat the "
    "purpose of using quantization to make optimizations more efficient. Very slighly blurring "
    "the image can help against fuzzy edges. BEI uses gausian blur.\n"
    "We recommend 0.1 - 0.3 px blur for slightly noisy images, and 0.3 - 1.5 px blur for complex images. "
)


FPE_INFO_TEXT = "The image will Z-fight if you go further than {:.1f} km from world center."


class ImageImporter(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)


        # ----- IMAGE SELECTION -----

        self.image_selector = ImageSelector(self.mw)
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
        self.max_layers = 24
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
        # Layer thickness updated at the end


        # Z-fighting notice
        self.fpe_info = Label("fpe_info")
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
        self.colors_slider = Slider(COLOR_LEVELS, COLOR_LEVELS.index(self.color_count))
        self.quantization_settings_layout.addWidget(self.colors_slider)
        self.colors_slider.value_changed.connect(self.update_color_count)
        self.update_color_count()



        # BLUR
        self.blur_layout = QHBoxLayout()
        self.blur_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.blur_layout)

        self.blur_label = Label("Blur")
        self.blur_label.set_tooltip(WHY_BLUR)
        self.blur_layout.addWidget(self.blur_label)

        self.blur_slider = Slider(BLUR_LEVELS, 0)
        self.blur_slider.value_changed.connect(self.update_blur_label)
        self.blur_layout.addWidget(self.blur_slider)



        # IMPORT SETTINGS
        self.import_settings_title = StyledLabel("Import settings", LabelStyle.HEADER_3)
        self.master_layout.addWidget(self.import_settings_title)

        self.resolution_settings = ImgResolutionSetting(False, (1 ,1))
        self.image_selector.on_new_image_selected.connect(self.resolution_settings.on_image_loaded)
        self.master_layout.addWidget(self.resolution_settings)

        self.color_correction_lay = QHBoxLayout()
        self.color_correction_lay.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.color_correction_lay)

        self.color_correction_label = Label("Color correction")
        self.color_correction_lay.addWidget(self.color_correction_label)

        self.color_correction_bs = BoolSwitch(True)
        self.color_correction_lay.addWidget(self.color_correction_bs)

        # Separator
        self.master_layout.addWidget(Separator())

        # FINAL BUTTON
        self.import_image_btn = Button("Import image")
        self.import_image_btn.clicked.connect(self.on_import_image_btn_clicked)
        self.master_layout.addWidget(self.import_image_btn)

        # CHANGE SETTINGS
        self.update_blur_label()
        self.update_layer_thickness()
        self.optimization_method.set_current_idx(1)
        self.quantization_algorithm.set_current_idx(2)


        self.master_layout.addStretch()



    def on_optimization_method_changed(self):
        idx = self.optimization_method.get_current_idx()
        self.oms3d_widget.setHidden(idx in (0, 1))


    def on_quantization_algorithm_changed(self):
        idx = self.quantization_algorithm.get_current_idx()
        self.quantization_settings_widget.setVisible(idx != 0)



    def on_import_image_btn_clicked(self):

        # Nothing loaded check
        if self.main_window.vehicle_selector_banner.is_vehicle_loaded():
            VehicleLoadingIssueDialog.create(self.mw, False).exec()
            return

        # Get data
        grp_format = ["none", "2d", "3d_greedy", "3d_slow"][self.optimization_method.get_current_idx()]
        quantization = self.quantization_algorithm.get_current_idx()
        color_count = self.colors_slider.get_value()
        resolution = self.resolution_settings.get_new_resolution()

        img = self.image_selector.get_pil_copy(resolution)

        # Blur image
        blur = self.blur_slider.get_value()
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur))

        # Apply color correction (Linear RGB -> sRGB 2.2)
        if self.color_correction_bs.get_value():
            img = srgb_to_linear(img)

        # Quantize image
        if quantization:
            quantization_str = ["_", "median_cut", "kmeans_oklab"][quantization]
            img = quantize_image(img, color_count, quantization_str)

        # If slow 3D: Prepare dialog widget and worker
        if grp_format == "3d_slow":

            self.decompose_worker = DecomposeWorker(
                image=img,
                mode=grp_format,
                max_layers=self.max_layers,
                max_restarts=None
            )
            import_progress_dialog = ImportProgressDialog(self.mw, self.max_layers, self.decompose_worker)

            def on_progress(best_total_rects, best_layer_count, restarts_done):
                import_progress_dialog.set_progress(best_total_rects, best_layer_count, restarts_done)

            def on_finished(result: DecomposeResult):
                self.handle_decompose_result(result)
                import_progress_dialog.close()

            def on_cancelled():
                self.decompose_worker.finished.disconnect(on_finished)  # don't build anything
                self.decompose_worker.cancel()
                import_progress_dialog.close()

            def on_end_now():
                self.decompose_worker.cancel()
                import_progress_dialog.close()

            self.decompose_worker.progress.connect(on_progress)
            self.decompose_worker.finished.connect(on_finished)
            import_progress_dialog.finished.connect(on_end_now)
            import_progress_dialog.cancelled.connect(on_cancelled)

            launch_with_threading(self.decompose_worker)

            import_progress_dialog.exec(blocking=True)
            return

        # else:
        result = decompose_image(
            image=img,
            mode=grp_format,
            max_layers=self.max_layers,
            max_restarts=None
        )
        self.handle_decompose_result(result)



    def handle_decompose_result(self, result: DecomposeResult):

        # Nothing loaded check (just in case)
        if self.main_window.vehicle_selector_banner.is_vehicle_loaded():
            VehicleLoadingIssueDialog.create(self.mw, False).exec()
            return

        # Get data
        layer_width = self.layer_thickness_slider.get_value()

        # Build vehicle
        brvfile = brickedit.BRVFile(brickedit.FILE_MAIN_VERSION)
        vhelper = brickedit.vhelper.ValueHelper(brickedit.FILE_MAIN_VERSION)
        color_id_to_br = [vhelper.rgba(*col) for col in result.palette]
        i = 0

        for layer_index, layer in enumerate(result.layers):
            for (r0, c0, r1, c1, color_id) in layer:
                # TODO: Adjust positions for scaling
                x, y = c0, r0
                width, height = c1 - c0 + 1, r1 - r0 + 1
                color = color_id_to_br[color_id]
                z = (layer_index + .5) * layer_width

                size_vec = brickedit.Vec3(float(width), float(height), float(layer_width))
                pos_vec = brickedit.Vec3(float(x), float(y), float(z)) + size_vec * 0.5

                # TODO: Add controls over properties such as materials, welding etc. & Control if we use Scalable bricks or floats.
                brvfile.add(brickedit.Brick(
                    ref=brickedit.ID(str(i), editor='img', weld='img'),
                    meta=brickedit.bt.SCALABLE_BRICK,
                    pos=pos_vec,
                    ppatch={
                        brickedit.p.BRICK_SIZE: size_vec,
                        brickedit.p.BRICK_COLOR: color,
                        brickedit.p.BRICK_MATERIAL: brickedit.p.BrickMaterial.CONCRETE
                    }
                ))
                #▲ print(brvfile.bricks[-1])
                i += 1

        # Make sure brick count is okay
        if len(brvfile.bricks) > 50_000:
            CannotSaveOverLimit.create(len(brvfile.bricks)).exec()
            return

        # Make description and save BRV
        img_path = self.image_selector.get_img_path()
        self.main_window.vehicle_selector_banner.save_brv(brvfile,
            description=f"Imported {img_path} in {len(brvfile.bricks)} brick(s) using the {self.get_menu_name()}."
        )


    def update_blur_label(self):
        blur = self.blur_slider.get_value()
        self.blur_slider.set_text(f"{blur} px", 44)

    def update_max_layers(self):
        self.max_layers = self.max_layers_slider.get_value()
        self.max_layers_slider.set_text(f"{self.max_layers} layers", 60)

    def update_layer_thickness(self):
        value = self.layer_thickness_slider.get_value()
        # Update slider
        self.layer_thickness_slider.set_text(f"{_LIST_SLIDER_OPTIONS[value]} cm", 62)
        # Update FPE Info
        zfight_distance = max_float32_for_tolerance(value) / 100_000  # cm -> km
        self.fpe_info.set_text(str.format(FPE_INFO_TEXT, zfight_distance))

    def update_color_count(self):
        self.color_count = self.colors_slider.get_value()
        self.colors_slider.set_text(f"{self.color_count} colors", 61)

    def get_menu_name(self):
        return "Image Importer"

    def _make_menu_info(self) -> base.MenuInfo:
        return base.MenuInfo(QIcon(":/assets/icons/ImageIcon.png"), True,
            tutorial=Tutorial(self.get_menu_name(), self.mw)
                .add_text("Test!")
                .add_collection("Some collection",
                    "Collection test 1!",
                    "Collection test 2 ??",
                    "Collection test 3.",
                    "Some very\nlong text with spaces and random stuff"
                )
        )
