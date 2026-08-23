from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ui.widgets import Widget, Surface, LineEdit, Label, Button

from PIL.Image import Image


class ImageSelector(Widget):

    thumbnail_size = 144, 96

    def __init__(self):
        super().__init__()

        self.true_master_layout = QVBoxLayout()
        self.true_master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.true_master_layout)

        self.surface = Surface(inner_layout_cls=QHBoxLayout)
        self.true_master_layout.addWidget(self.surface)
        self.master_layout: QHBoxLayout = self.surface.layout()

        # DATA
        self.pil_img = None

        # ICON
        self.icon_label = QLabel()  # Explicitly don't want custom Label class
        self.icon_label.setContentsMargins(0, 0, 0, 0)
        # self.icon_label.setScaledContents(True)
        self.icon_label.setMaximumSize(*self.thumbnail_size)
        self.master_layout.addWidget(self.icon_label)

        # CONTENTS LAYOUT
        self.contents_layout = QVBoxLayout()
        self.contents_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.contents_layout, stretch=1)

        self.image_name_label = Label("No image selected")
        self.contents_layout.addWidget(self.image_name_label)


        self.unset_icon()


    def unset_icon(self):
        self.set_icon(QPixmap(":/assets/icons/not_found.png"), None)
        self.image_name_label.set_text("No image selected")

    def set_icon(self, qicon: QPixmap, pil_img: Image | None):
        adjusted_icon = qicon.scaled(*self.thumbnail_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(adjusted_icon)
        self.pil_img = pil_img

    def try_set_icon_from_path(self, path: str | None):
        success = False
        try:
            if path is not None:
                qicon = QPixmap(path)
                pil_img = Image.open(path)  # Errors will automatically be raised if the path is wrong, and handled by try block
                self.set_icon(qicon, pil_img)
                success = True
        except Exception:  # i have sinned
            pass
        if not success:
            self.set_icon(QPixmap(":/assets/icons/not_found.png"), None)


    def is_loaded(self) -> bool:
        return self.pil_img is not None

    def get_qpixmap_copy(self) -> QPixmap | None:
        return self.icon_label.pixmap() if self.is_loaded() else None

    def get_pil_copy(self) -> Image | None:
        return self.pil_img
