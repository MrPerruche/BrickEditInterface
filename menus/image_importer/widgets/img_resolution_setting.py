from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from ui.widgets import Widget, Surface, Label, StyledLabel, LabelStyle, Switcher, SwitcherEntry, NumberChannelEdit, ChannelMode, Separator, ToolButton

from utils import clamp

from PIL import Image

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.image.image_selector import ImageSelector


def make_stretching_message(old_resolution: tuple[int, int], new_resolution: tuple[int, int]):

        current_ratio = old_resolution[0] / old_resolution[1]
        new_ratio = new_resolution[0] / new_resolution[1]

        horizontal_stretching = current_ratio / new_ratio
        if abs(horizontal_stretching-1) > ImgResolutionSetting.STRETCHING_TOL:
            return (
                f"Stretching {horizontal_stretching*100-100:.2f}% horizontally" if horizontal_stretching > 1 else
                f"Stretching {(1/horizontal_stretching)*100-100:.2f}% vertically"
            )
        return "No stretching"


def round_value(value: int | float) -> int:
    return max(int(round(value)), 1)

def round_resolution(resolution: tuple[int | float, int | float]) -> tuple[int, int]:
    x, y = resolution[0], resolution[1]
    return round_value(x), round_value(y)


class ImgResolutionSetting(Widget):

    MODES = ["Do not change", "Percentage", "Manual"]
    # MODE_TO_IDX = {"Do not change": 0, "Percentage": 1, "Manual": 2, "Advanced": 3}
    DO_NOT_CHANGE_IDX = 0
    PERCENTAGE_IDX = 1
    MANUAL_IDX = 2
    ADVANCED_IDX = 3

    STRETCHING_TOL = 0.00_01  # 0.01%

    UNLOCKED_ICON = None
    LOCKED_ICON = None

    def __init__(self, image_loaded: bool = False, current_resolution: None | tuple[int, int] = None):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)

        self.image_loaded = image_loaded
        self.current_resolution = current_resolution

        # ICONS
        if ImgResolutionSetting.LOCKED_ICON is None:
            ImgResolutionSetting.LOCKED_ICON = QIcon(":/assets/icons/Locked.png")
            ImgResolutionSetting.UNLOCKED_ICON = QIcon(":/assets/icons/Unlocked.png")

        # SIGNALS
        self.ignore_on_ml_values_changed_signal = False

        # MASTER LAYOUT SETUP
        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        # Surface label
        self.title_layout = QHBoxLayout()
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.title_layout)

        self.title_label = Label("Image resolution")
        self.title_layout.addWidget(self.title_label, stretch=2)

        # Mode selection
        self.mode_switcher = Switcher(
            [SwitcherEntry(mode, layout=QVBoxLayout(), auto_add_layout=False) for mode in self.MODES]
        )
        
        # Mode selection menus
        for i in range(len(self.MODES)):
            layout = self.mode_switcher.get_layout(i)
            widget = self.mode_switcher.items[i].get_widget()
            assert layout is not None, "Layout is none -> ImgResolutionSetting.mode_switcher is poorly initialized"
            self.master_layout.addWidget(widget)
            layout.setContentsMargins(0, 0, 0, 0)
        self.mode_switcher.set_index(ImgResolutionSetting.PERCENTAGE_IDX)

        self.title_layout.addWidget(self.mode_switcher, stretch=3)

        # PERCENTAGE LAYOUT
        percentage_layout = self.mode_switcher.get_layout(ImgResolutionSetting.PERCENTAGE_IDX)

        # Percentage
        self.pl_input_layout = QHBoxLayout()
        percentage_layout.addLayout(self.pl_input_layout)
        self.pl_input_label = Label("Resize percentage")
        self.pl_input_layout.addWidget(self.pl_input_label)
        self.pl_input_number = NumberChannelEdit(ChannelMode.FLOAT64, minimum=0.1, maximum=1_000, allow_nan=False, allow_inf=False,)  # Allow 1/1000 - x10 scaling
        self.pl_input_number.setValue(100)
        self.pl_input_layout.addWidget(self.pl_input_number)
        self.pl_input_unit = Label("%")
        self.pl_input_layout.addWidget(self.pl_input_unit)

        # MANUAL LAYOUT
        manual_layout = self.mode_switcher.get_layout(ImgResolutionSetting.MANUAL_IDX)
        self.old_manual_values = (1, 1)
        
        # Manual button layout
        manual_row = QHBoxLayout()
        manual_row.setContentsMargins(0, 0, 0, 0)
        manual_layout.addLayout(manual_row)
        # Locking
        self.ml_lock_btn = ToolButton(ImgResolutionSetting.LOCKED_ICON, tint_icon=True)
        self.ml_lock_btn.set_checkable(True)
        self.ml_lock_btn.set_checked(True)
        self.ml_lock_btn.clicked.connect(self.on_ml_lock_modified)
        manual_row.addWidget(self.ml_lock_btn)
        # NCEs
        self.ml_size_x = NumberChannelEdit(ChannelMode.INT, minimum=1, maximum=32_767, allow_nan=False, allow_inf=False)  # 32k is probably a safe safeguard? ish.
        self.ml_size_x.setValue(self.old_manual_values[0])
        self.ml_size_x.value_changed.connect(lambda: self.on_ml_values_changed(0))
        manual_row.addWidget(self.ml_size_x, stretch=1)

        self.ml_size_y_label = Label("x")
        manual_row.addWidget(self.ml_size_y_label)

        self.ml_size_y = NumberChannelEdit(ChannelMode.INT, minimum=1, maximum=32_767, allow_nan=False, allow_inf=False)
        self.ml_size_y.setValue(self.old_manual_values[1])
        self.ml_size_y.value_changed.connect(lambda: self.on_ml_values_changed(1))
        manual_row.addWidget(self.ml_size_y, stretch=1)


        # INFORMATION
        # Setting up main local layout
        self.info_widget = Widget()
        self.info_widget.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addWidget(self.info_widget)
        self.info_layout = QVBoxLayout()
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.info_layout.setSpacing(0)
        # Separator
        # self.info_layout.addWidget(Separator())
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

            case ImgResolutionSetting.MANUAL_IDX:
                return round_resolution((self.ml_size_x.value(), self.ml_size_y.value()))

        raise NotImplementedError(f"Unknown resolution setting mode {self.mode_switcher.get_idx()}")


    def set_current_resolution(self, resolution: tuple[int, int] | None):
        old_resolution = self.current_resolution
        if resolution is None:
            self.image_loaded = False
            self.current_resolution = (1, 1)
        else:
            self.image_loaded = True
            self.current_resolution = resolution

        if old_resolution is None or old_resolution != self.current_resolution:
            self.ml_size_x.setValue(self.current_resolution[0])
            self.ml_size_y.setValue(self.current_resolution[1])



    def update_info_layout(self):

        self.info_widget.setVisible(self.image_loaded)
        if not self.image_loaded:
            return

        new_resolution = self.get_new_resolution()
        self.stretching_label.set_text(make_stretching_message(self.current_resolution, new_resolution))

        self.res_label.set_text(f"{new_resolution[0]} x {new_resolution[1]}")

    def update_all_widgets(self):
        self.update_info_layout()

    def on_ml_lock_modified(self):
        is_locked = self.ml_lock_btn.is_checked()
        self.ml_lock_btn.set_icon(ImgResolutionSetting.LOCKED_ICON if is_locked else ImgResolutionSetting.UNLOCKED_ICON)

    def on_ml_values_changed(self, who_changed: int):
        """who_changed = 0 -> x changed, must edit 1 if lock enabled. 1 -> y changed, must edit 0 if lock enabled."""
        if self.ignore_on_ml_values_changed_signal:
            return

        if self.ml_lock_btn.is_checked():

            self.ignore_on_ml_values_changed_signal = True
            try:
                aspect_ratio = (
                    self.current_resolution[1] / self.current_resolution[0] if self.image_loaded else
                    self.old_manual_values[1] / self.old_manual_values[0]
                )
                if who_changed == 0:
                    new_y = round_value(self.ml_size_x.value() * aspect_ratio)
                    self.ml_size_y.setValue(clamp(new_y, 1, 32_767))
                else:
                    new_x = round_value(self.ml_size_y.value() / aspect_ratio)
                    self.ml_size_x.setValue(clamp(new_x, 1, 32_767))
            finally:
                self.ignore_on_ml_values_changed_signal = False

        self.old_manual_values = (self.ml_size_x.value(), self.ml_size_y.value())
        self.update_info_layout()


    def on_image_loaded(self, image_selector: 'ImageSelector'):
        self.set_current_resolution(image_selector.pil_img.size)
        self.update_all_widgets()

    def apply_resize(self, img: Image.Image):
        return img.resize(self.get_new_resolution(), Image.Resampling.LANCZOS)  # LANCZOS - BICUBIC - HAMMING
