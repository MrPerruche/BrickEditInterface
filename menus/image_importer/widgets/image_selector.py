from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QTimer, QDateTime, Signal
from PySide6.QtGui import QPixmap

from PIL import Image

from os import path

from utils import str_time_since
from brickedit import *

from menus.shared_widgets.square_widget import SquareWidget, SquareState


from logging import getLogger
_logger = getLogger(__name__)





class ImageSelector(SquareWidget):
    """Custom widget for image selection."""

    new_image_selected = Signal()

    def __init__(self, store_pil_img=True, parent=None):
        super().__init__(parent)

        self.img_path = None
        self.store_pil_img = store_pil_img
        self.pil_img = None
        
        # General purpose update timer
        self.last_loaded_time = QDateTime.currentDateTime()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.on_update_timer)
        self.update_timer.start(100)

        # Constants
        self.thumbnail_size = 92, 92
        
        self.setMinimumHeight(50)
        
        # Add layout and widgets
        self.master_layout = QHBoxLayout(self)
        self.master_layout.setContentsMargins(12, 12, 12, 12)
        self.master_layout.setSpacing(8)
        
        # Vehicle Icon
        self.icon_label = QLabel()
        icon_pixmap = QPixmap(":/assets/icons/not_found.png")
        self.set_icon(icon_pixmap)
        self.master_layout.addWidget(self.icon_label)
        
        # Side layout
        self.side_layout = QVBoxLayout()
        self.side_layout.setAlignment(Qt.AlignTop)
        self.master_layout.addLayout(self.side_layout, 1)
        
        # Select a vehicle label
        self.image_name_label = QLabel("No image selected.")
        self.image_name_label.setWordWrap(True)
        self.side_layout.addWidget(self.image_name_label)

        # Seconds since initialization label
        self.seconds_label = QLabel("Label not initialized!")
        self.seconds_label.setWordWrap(True)
        self.side_layout.addWidget(self.seconds_label)

        # Button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        self.side_layout.addLayout(self.button_layout)

        self.select_image = QPushButton("Select")
        self.select_image.clicked.connect(self.on_select_image)
        self.button_layout.addWidget(self.select_image)

        self.reload_image = QPushButton("Reload")
        self.reload_image.clicked.connect(self.on_reload_image)
        self.button_layout.addWidget(self.reload_image)





    def set_icon(self, icon: QPixmap):
        adjusted_icon = icon.scaled(*self.thumbnail_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(adjusted_icon)



    def on_update_timer(self):
        """General purpose timer callback. Add your update logic here. Updated every 100ms."""
        self.update_seconds_display()



    def on_select_image(self):
        """Open file explorer to select an image."""
        formats = Image.registered_extensions().copy()
        if '.gif' in formats:
            del formats['.gif']
        else:
            _logger.warning(f"GIF is not registered as an image format, and as such could not be banned from ImageSelector. Registered: {formats}")
        formats_str = " ".join(f"*{ext}" for ext in formats)

        folder_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            f"Image Files ({formats_str})"
        )

        if folder_path:  # User didn't cancel
            self.load_image(folder_path)



    def on_reload_image(self):
        if self.img_path is not None:
            self.load_image(self.img_path, silent=True)



    def load_image(self, img_path, silent=False):
        
        img_path = path.abspath(img_path)
        try:
            if self.store_pil_img:
                self.pil_img = Image.open(img_path)
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Failed to load image", f"Failed to load image: {str(e)}")
            return

        self.img_path = img_path
        self.image_name_label.setText(path.split(img_path)[-1])
        self.set_icon(QPixmap(img_path))

        self.new_image_selected.emit()


    def update_seconds_display(self):
        """Update the seconds display label."""
        # Loaded time
        last_loaded_time_seconds = self.last_loaded_time.secsTo(QDateTime.currentDateTime())
        last_loaded_time_rendered = str_time_since(last_loaded_time_seconds)

        # Last save detection
        last_modified_time_seconds = 1e99
        last_modified_time_rendered = "N/A"
        if self.img_path is not None:
            if path.exists(self.img_path):
                last_modified_time_os = path.getmtime(self.img_path)
                last_modified_time = QDateTime.fromSecsSinceEpoch(int(last_modified_time_os))
                last_modified_time_seconds = last_modified_time.secsTo(QDateTime.currentDateTime())
                last_modified_time_rendered = str_time_since(last_modified_time_seconds)

        # Image saved
        select_line = "No image selected."
        if self.img_path is not None:
            select_line = f"Last saved {last_modified_time_rendered} ago"
        # Image loaded
        load_line = "No image loaded."
        if self.img_path is not None:
            load_line = f"Last loaded {last_loaded_time_rendered} ago"
        self.seconds_label.setText(f"{select_line}\n{load_line}")

        # Red highlight if severe
        if last_modified_time_seconds < last_loaded_time_seconds:
            self.set_state(SquareState.SEVERE)
        else:
            self.set_state(SquareState.NORMAL)
