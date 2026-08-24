from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ui.widgets import Widget, Surface, Label, Button
from ui.dialogs import AnimatedImageError, UnexpectedError

from PIL import Image


def is_single_frame_image(image: Image.Image):
    return image.n_frames == 1

extensions = Image.registered_extensions().keys()
name_filter = "Images (" + " ".join(f"*{ext}" for ext in extensions) 


class ImageSelector(Widget):

    thumbnail_size = 96, 64

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

        self.image_selector_button = Button("Select image")
        self.image_selector_button.clicked.connect(self.on_selector_button_clicked)
        self.contents_layout.addWidget(self.image_selector_button)

        self.unset_icon()


    def on_selector_button_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            filter=name_filter
        )

        self.try_set_icon_from_path(file_path)



    def unset_icon(self):
        self.set_icon(QPixmap(":/assets/icons/not_found.png"), None)
        self.image_name_label.set_text("No image selected")

    def set_icon(self, qicon: QPixmap, pil_img: Image.Image | None):
        adjusted_icon = qicon.scaled(*self.thumbnail_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(adjusted_icon)
        self.pil_img = pil_img

    def try_set_icon_from_path(self, path: str | None, show_dialogs = True):
        success = False

        try:
            if path is None:
                raise Exception('skip')

            qicon = QPixmap(path)
            pil_img = Image.open(path)

            if not is_single_frame_image(pil_img):
                AnimatedImageError.create().exec()
                raise Exception('skip')

            self.set_icon(qicon, pil_img)
            success = True

        except Exception as e:
            if str(e) != 'skip':
                UnexpectedError.create(None, e).exec()
        if not success:
            self.set_icon(QPixmap(":/assets/icons/not_found.png"), None)


    def is_loaded(self) -> bool:
        return self.pil_img is not None

    def get_qpixmap_copy(self) -> QPixmap | None:
        return self.icon_label.pixmap() if self.is_loaded() else None

    def get_pil_copy(self) -> Image.Image | None:
        return self.pil_img
