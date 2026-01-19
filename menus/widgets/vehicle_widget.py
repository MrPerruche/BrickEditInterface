from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QSize, QTimer, QDateTime
from PySide6.QtGui import QColor, QIcon, QPixmap

from typing import Final, Optional, Callable
from datetime import datetime
import os
import traceback

from utils import str_time_since
from brickedit.src.brickedit import *  # TODO
from .square_widget import SquareWidget


class VehicleWidget(SquareWidget):
    """Custom widget for vehicle selection with rounded borders."""
    
    def __init__(self, call_on_reload: list[Callable] | Callable | None = None, parent=None):
        super().__init__(parent)

        # --- LOGIC
        if call_on_reload is None:
            self.call_on_reload = []
        elif isinstance(call_on_reload, list):
            self.call_on_reload = call_on_reload
        else:
            # Single callable passed, wrap it in a list
            self.call_on_reload = [call_on_reload]

        self.brv_file: Optional[str] = None
        self.brm_file: Optional[str] = None
        self.icon_file: Optional[str] = None

        self.brv = None
        
        # General purpose update timer
        self.last_loaded_time = QDateTime.currentDateTime()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.on_update_timer)
        self.update_timer.start(100)  # Update every second

        # --- RENDER

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
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.master_layout.addLayout(self.layout, 1)
        
        # Select a vehicle label
        self.vehicle_name = QLabel("Please select a vehicle.")
        self.vehicle_name.setWordWrap(True)
        self.layout.addWidget(self.vehicle_name)

        # Seconds since initialization label
        self.seconds_label = QLabel("Label not initialized!")
        self.seconds_label.setWordWrap(True)
        self.layout.addWidget(self.seconds_label)

        # Button layout
        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)

        self.select_vehicle = QPushButton("Select")
        self.select_vehicle.clicked.connect(self.on_select_vehicle)
        self.button_layout.addWidget(self.select_vehicle)

        self.reload_vehicle = QPushButton("Reload")
        self.reload_vehicle.clicked.connect(self.on_reload_vehicle)
        self.button_layout.addWidget(self.reload_vehicle)




    def set_icon(self, icon: QPixmap):
        adjusted_icon = icon.scaled(*self.thumbnail_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.icon_label.setPixmap(adjusted_icon)



    def on_update_timer(self):
        """General purpose timer callback. Add your update logic here. Updated every 100ms."""
        self.update_seconds_display()



    def on_select_vehicle(self):
        """Open file explorer to select a vehicle folder."""
        default_path = os.path.expanduser("~\\AppData\\Local\\BrickRigs\\SavedRemastered\\Vehicles")
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Vehicle Folder",
            default_path,  # Default directory (empty = user's home)
            QFileDialog.ShowDirsOnly
        )

        if folder_path:  # User didn't cancel
            self.load_vehicle(folder_path)



    def on_reload_vehicle(self):
        if self.brv_file is not None:
            self.load_vehicle(os.path.dirname(self.brv_file))



    def load_vehicle(self, folder_path):
        
        # Before accepting it, make sure the BRV exists and is deserilizable
        brv_file = os.path.join(folder_path, "Vehicle.brv")
        if not os.path.exists(brv_file):
            QMessageBox.warning(self, "File not found", "Vehicle.brv file not found in selected folder.")
            return

        try:
            version = -1
            with open(brv_file, "rb") as f:
                file = bytearray(f.read())

                # Is empty?
                if file == b'':
                    raise Exception("empty")
                version = file[0]

                # Valid version? 
                if version < FILE_MIN_SUPPORTED_VERSION:
                    raise Exception("too old")
                elif version > FILE_MAX_SUPPORTED_VERSION:
                    raise Exception("too new")
                # Load
                brv = BRVFile(version)
                brv.deserialize(file)

        # Oh no, something went wrong
        except BrickError:
            QMessageBox.critical(self, "Deserialization failed",
                f"Failed to select/reload the vehicle file because it contains modded bricks BrickEdit Interface do not support:\n{str(e)}"
            )
            return
        except BaseException as e:
            if str(e) == "empty":
                QMessageBox.critical(self, "Invalid file", "Vehicle.brv file is empty.")
            elif str(e) == "too old":
                QMessageBox.critical(self, "Invalid file", f"BrickEdit Interface do not support vehicles made in this version ({version}). Please open, edit, undo change, then re-save the vehicle.")
            elif str(e) == "too new":
                QMessageBox.critical(self, "Invalid file", f"BrickEdit Interface do not support vehicles made in this version ({version}). Please update BrickEdit-Interface.")
            else:
                QMessageBox.critical(self, "Deserialization failed",
                    f"Failed to select/reload the vehicle file! Please send the following information to the developer @perru_ on discord:\n\n{traceback.format_exc()}"
                )
            return

        # From now on, everything is fine. We can store variables and update everything
        self.brv_file = brv_file
        self.brv = brv
        
        # Metadata
        self.brm_file = None
        metadata_file = os.path.join(folder_path, "Metadata.brm")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "rb") as f:
                    file = bytearray(f.read())
                    self.brm_file = metadata_file
                    self.name, = BRMFile(0).deserialize(file, config=BRMDeserializationConfig(name=True), auto_version=True)
            except BaseException as e:
                QMessageBox.warning(self, "Failed to load metadata", f"Failed to load metadata file. Reason:\n{type(e).__name__}: {str(e)}")
                self.name = "No metadata found."
        
        self.vehicle_name.setText(self.name)
        
        # Set thumbnail
        icon_file = os.path.join(folder_path, "Preview.png")
        if os.path.exists(icon_file):
            self.icon_file = icon_file
            self.set_icon(QPixmap(icon_file))
        else:
            self.icon_file = None
            self.set_icon(QPixmap(":/assets/icons/missing_thumbnail.png"))  # Not not_found, this is if there is a file but no thumbnail
        
        # Update seconds display
        self.last_loaded_time = QDateTime.currentDateTime()
        self.update_seconds_display()
        for f in self.call_on_reload:
            f()


    def update_seconds_display(self):
        """Update the seconds display label."""
        # Loaded time
        last_loaded_time_seconds = self.last_loaded_time.secsTo(QDateTime.currentDateTime())
        last_loaded_time_rendered = str_time_since(last_loaded_time_seconds)

        # Last save detection
        last_modified_time_seconds = 1e99
        last_modified_time_rendered = "N/A"
        if self.brv_file is not None:
            if os.path.exists(self.brv_file):
                last_modified_time_os = os.path.getmtime(self.brv_file)
                last_modified_time = QDateTime.fromSecsSinceEpoch(int(last_modified_time_os))
                last_modified_time_seconds = last_modified_time.secsTo(QDateTime.currentDateTime())
                last_modified_time_rendered = str_time_since(last_modified_time_seconds)

        # Vehicle saved
        select_line = "No vehicle selected."
        if self.brv_file is not None:
            select_line = f"Last saved {last_modified_time_rendered} ago"
        # Vehicle loaded
        load_line = "No vehicle loaded."
        if self.brv_file is not None:
            load_line = f"Last loaded {last_loaded_time_rendered} ago"
        self.seconds_label.setText(f"{select_line}\n{load_line}")

        # Red highlight if severe
        if last_modified_time_seconds < last_loaded_time_seconds:
            self.set_severity(True)
        else:
            self.set_severity(False)
