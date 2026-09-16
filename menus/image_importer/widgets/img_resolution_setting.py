from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt

from ui.widgets import Widget, Surface, Label, StyledLabel, LabelStyle, Switcher, SwitcherEntry, NumberChannelEdit, ChannelMode, Separator
from ui.components.brick.property_widgets import Vec2PropertyWidget

from utils import wipe_layout

from PIL import Image

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.image.image_selector import ImageSelector


def make_stretching_message(self, old_resolution: tuple[int, int], new_resolution: tuple[int, int]):

        current_ratio = self.current_resolution[0] / self.current_resolution[1]
        new_ratio = new_resolution[0] / new_resolution[1]

        horizontal_stretching = current_ratio / new_ratio
        if abs(horizontal_stretching-1) > ImgResolutionSetting.STRETCHING_TOL:
            return (
                f"Stretching {horizontal_stretching*100-100:.2f}% horizontally" if horizontal_stretching > 1 else
                f"Stretching {(1/horizontal_stretching)*100-100:.2f}% vertically"
            )
        return "No stretching"


def round_resolution(resolution: tuple[int, int]):
    x, y = resolution[0], resolution[1]
    return max(round(x), 1), max(round(y), 1)


class ImgResolutionSetting(Widget):

    MODES = ["Do not change", "Percentage", "Manual", "Advanced"]
    # MODE_TO_IDX = {"Do not change": 0, "Percentage": 1, "Manual": 2, "Advanced": 3}
    DO_NOT_CHANGE_IDX = 0
    PERCENTAGE_IDX = 1
    MANUAL_IDX = 2
    ADVANCED_IDX = 3

    STRETCHING_TOL = 0.00_01  # 0.01%

    def __init__(self, image_loaded: bool = False, current_resolution: None | tuple[int, int] = None):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)

        self.image_loaded = image_loaded
        self.current_resolution = current_resolution

        # MASTER LAYOUT SETUP
        self.true_master_layout = QVBoxLayout()
        self.true_master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.true_master_layout)

        self.surface = Surface()
        self.true_master_layout.addWidget(self.surface)
        self.master_layout = self.surface.layout()

        # Surface label
        self.title_label = StyledLabel("Image resolution", style=LabelStyle.LARGE_5)
        self.master_layout.addWidget(self.title_label)

        # Mode selection
        self.mode_switcher = Switcher(
            [SwitcherEntry(mode, layout=QVBoxLayout()) for mode in self.MODES]
        )
        for i in range(len(self.MODES)):
            layout = self.mode_switcher.get_layout(i)
            assert layout is not None, "Layout is none -> ImgResolutionSetting.mode_switcher is poorly initialized"
            layout.setContentsMargins(0, 0, 0, 0)
        self.mode_switcher.set_index(ImgResolutionSetting.PERCENTAGE_IDX)
        self.master_layout.addWidget(self.mode_switcher)

        # PERCENTAGE LAYOUT
        percentage_layout = self.mode_switcher.get_layout(ImgResolutionSetting.PERCENTAGE_IDX)

        # Percentage
        self.pl_input_layout = QHBoxLayout()
        percentage_layout.addLayout(self.pl_input_layout)
        self.pl_input_label = Label("Resize percentage:")
        self.pl_input_layout.addWidget(self.pl_input_label)
        self.pl_input_number = NumberChannelEdit(ChannelMode.FLOAT64, minimum=0.1, maximum=1_000, allow_nan=False, allow_inf=False,)  # Allow 1/1000 - x10 scaling
        self.pl_input_number.setValue(100)
        self.pl_input_layout.addWidget(self.pl_input_number)
        self.pl_input_unit = Label("%")
        self.pl_input_layout.addWidget(self.pl_input_unit)

        # INFORMATION
        # Setting up main local layout
        self.info_widget = Widget()
        self.info_widget.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addWidget(self.info_widget)
        self.info_layout = QVBoxLayout()
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_layout.setSpacing(0)
        # Separator
        self.info_layout.addWidget(Separator())
        # Stuff on same line
        self.info_data_layout = QHBoxLayout()
        self.info_layout.addLayout(self.info_data_layout)
        self.info_widget.setLayout(self.info_layout)
        # Stretching Label
        self.stretching_label = Label("stretching_label")
        self.info_data_layout.addWidget(self.stretching_label, stretch=1)
        # resoluton label
        self.res_label = Label("res_label")
        self.res_label.set_alignment(Qt.AlignRight)
        self.res_label.setMinimumWidth(75)
        self.info_data_layout.addWidget(self.res_label)


        # FINAL
        # Connect update_info_layout to everything
        self.mode_switcher.index_changed.connect(self.update_info_layout)
        self.pl_input_number.value_changed.connect(self.update_info_layout)

        self.update_all_widgets()



    def get_new_resolution(self):
        # /!\ MAKE SURE YOU CANNOT RETURN X < 1 OR Y < 1! OR ZERO DIVISION ERRORS
        match self.mode_switcher.get_idx():

            case ImgResolutionSetting.DO_NOT_CHANGE_IDX:
                return round_resolution(self.current_resolution)

            case ImgResolutionSetting.PERCENTAGE_IDX:
                ratio = self.pl_input_number.value() / 100
                x, y = self.current_resolution[0], self.current_resolution[1]
                return round_resolution((x*ratio, y*ratio))

        return 123, 456  # Placeholder


    def update_info_layout(self):

        self.info_widget.setVisible(self.image_loaded)
        if not self.image_loaded:
            return

        percentage = self.pl_input_number.value()
        new_resolution = self.get_new_resolution()
        self.stretching_label.set_text(make_stretching_message(self, self.current_resolution, new_resolution))

        self.res_label.set_text(f"{new_resolution[0]} x {new_resolution[1]}")

    def update_all_widgets(self):
        self.update_info_layout()


    def on_image_loaded(self, image_selector: 'ImageSelector'):
        self.set_current_resolution(image_selector.pil_img.size)
        self.update_all_widgets()


    def set_current_resolution(self, resolution: tuple[int, int] | None):
        if resolution is None:
            self.image_loaded = False
            self.current_resolution = (1, 1)
        else:
            self.image_loaded = True
            self.current_resolution = resolution
        


    def apply_resize(self, img: Image.Image):
        return img.resize(self.get_new_resolution(), Image.Resampling.LANCZOS)  # LANCZOS - BICUBIC - HAMMING
