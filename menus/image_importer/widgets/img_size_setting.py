from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout

from ui.widgets import Widget, Label, NumberChannelEdit, ChannelMode


MAX_SIZE_CM = 100_000.0
MIN_PIXEL_SIZE_CM = 0.01
MIN_THICKNESS_CM = 0.01

# Same label : control ratio as the material / editor / weld rows of the image importer (LABEL_STRETCH / LONG_STRETCH)
LABEL_STRETCH = 4
FIELD_STRETCH = 11


class ImgSizeSetting(Widget):
    """Controls the size of the imported image in game units (cm): size of one pixel, size of the whole image
    (only usable once an image is loaded, as it depends on the resolution) and total thickness (Z)."""

    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)

        self.image_loaded = False
        self.resolution: tuple[int, int] = (1, 1)
        self._updating = False  # Guards the pixel size <-> image size feedback loop

        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        # Pixel size
        pixel_row = QHBoxLayout()
        pixel_row.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(pixel_row)
        pixel_row.addWidget(Label("Pixel size"), stretch=LABEL_STRETCH)
        pixel_fields = self._make_fields_layout(pixel_row)
        self.pixel_size = NumberChannelEdit(ChannelMode.FLOAT64, minimum=MIN_PIXEL_SIZE_CM, maximum=MAX_SIZE_CM,
                                            allow_nan=False, allow_inf=False)
        self.pixel_size.setValue(1.0)
        self.pixel_size.value_changed.connect(self._on_pixel_size_changed)
        pixel_fields.addWidget(self.pixel_size, stretch=1)
        pixel_fields.addWidget(Label("cm"))

        # Image size
        image_row = QHBoxLayout()
        image_row.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(image_row)
        self.image_size_label = Label("Image size")
        image_row.addWidget(self.image_size_label, stretch=LABEL_STRETCH)
        image_fields = self._make_fields_layout(image_row)
        self.image_size_x = NumberChannelEdit(ChannelMode.FLOAT64, minimum=MIN_PIXEL_SIZE_CM, maximum=MAX_SIZE_CM,
                                              allow_nan=False, allow_inf=False)
        self.image_size_x.value_changed.connect(lambda: self._on_image_size_changed(0))
        image_fields.addWidget(self.image_size_x, stretch=1)
        image_fields.addWidget(Label("x"))
        self.image_size_y = NumberChannelEdit(ChannelMode.FLOAT64, minimum=MIN_PIXEL_SIZE_CM, maximum=MAX_SIZE_CM,
                                              allow_nan=False, allow_inf=False)
        self.image_size_y.value_changed.connect(lambda: self._on_image_size_changed(1))
        image_fields.addWidget(self.image_size_y, stretch=1)
        image_fields.addWidget(Label("cm"))

        # Thickness
        thickness_row = QHBoxLayout()
        thickness_row.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(thickness_row)
        thickness_row.addWidget(Label("Thickness"), stretch=LABEL_STRETCH)
        thickness_fields = self._make_fields_layout(thickness_row)
        self.thickness = NumberChannelEdit(ChannelMode.FLOAT64, minimum=MIN_THICKNESS_CM, maximum=MAX_SIZE_CM,
                                           allow_nan=False, allow_inf=False)
        self.thickness.setValue(2.0)
        thickness_fields.addWidget(self.thickness, stretch=1)
        thickness_fields.addWidget(Label("cm"))

        self._refresh_image_size()


    @staticmethod
    def _make_fields_layout(row: QHBoxLayout) -> QHBoxLayout:
        """Right side of a row (field(s) + unit), taking FIELD_STRETCH against the label's LABEL_STRETCH."""
        fields = QHBoxLayout()
        fields.setContentsMargins(0, 0, 0, 0)
        row.addLayout(fields, stretch=FIELD_STRETCH)
        return fields


    def get_pixel_size(self) -> float:
        return float(self.pixel_size.value())

    def get_thickness(self) -> float:
        return float(self.thickness.value())


    def set_resolution(self, resolution: tuple[int, int], image_loaded: bool):
        self.resolution = resolution
        self.image_loaded = image_loaded
        self._refresh_image_size()

    def set_thickness_minimum(self, minimum: float):
        """Value must be raised BEFORE the minimum: setValue validates against the current minimum,
        and a value below the new minimum would otherwise be left invalid."""
        minimum = max(minimum, MIN_THICKNESS_CM)
        if self.thickness.value() < minimum:
            self.thickness.setValue(minimum)
        self.thickness.model.minimum = minimum


    def _refresh_image_size(self):
        self.image_size_x.setEnabled(self.image_loaded)
        self.image_size_y.setEnabled(self.image_loaded)
        self.image_size_label.setEnabled(self.image_loaded)

        self._updating = True
        try:
            pixel_size = self.get_pixel_size()
            # Clamp so a big resolution x pixel size can't fall out of the NCE's bounds
            self.image_size_x.setValue(min(max(self.resolution[0] * pixel_size, MIN_PIXEL_SIZE_CM), MAX_SIZE_CM))
            self.image_size_y.setValue(min(max(self.resolution[1] * pixel_size, MIN_PIXEL_SIZE_CM), MAX_SIZE_CM))
        finally:
            self._updating = False

    def _on_pixel_size_changed(self):
        if not self._updating:
            self._refresh_image_size()

    def _on_image_size_changed(self, who_changed: int):
        if self._updating or not self.image_loaded:
            return
        new_size = self.image_size_x.value() if who_changed == 0 else self.image_size_y.value()
        new_pixel_size = new_size / self.resolution[who_changed]

        self._updating = True
        try:
            self.pixel_size.setValue(min(max(new_pixel_size, MIN_PIXEL_SIZE_CM), MAX_SIZE_CM))
        finally:
            self._updating = False
        self._refresh_image_size()
