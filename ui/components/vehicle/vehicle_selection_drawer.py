from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QSizePolicy, QMessageBox
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QSize, QDateTime, QTimer, Signal

import os
from copy import deepcopy
import struct
from traceback import format_exc

from ui.components import VehicleSelector, VehicleData
from ui.widgets import Widget, Button, ToolButton, Label, LineEdit
from ui.theme import Theme, register_has_theme_and_apply
from ui.dialogs import VehicleSavedDialog, NothingEverHappensDialog

from pathlib import Path
from utils import tint_icon, str_time_since, get_vehicles_path
import logging

import brickedit


def lowest_available_number(path: Path | str):
    if isinstance(path, str):
        path = Path(path)

    numbers = {
        int(p.name)
        for p in Path(path).iterdir()
        if p.is_dir() and p.name.isdigit() and int(p.name) >= 1
    }

    n = 1
    while n in numbers:
        n += 1

    return n


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface

_logger = logging.getLogger(__name__)


struct_u16 = struct.Struct('<H')

class VehicleSelectionDrawer(Widget):
    
    vehicle_loaded = Signal(str)

    small_thumbnail_size = 26, 26
    large_thumbnail_size = 73, 73

    brm_name_deserialization_profile = brickedit.BRMDeserializationConfig(
        name=True
    )

    def __init__(self, mw: 'BrickEditInterface', parent=None):
        super().__init__(parent)
        self.mw = mw
        self.is_expanded = True
        self.setObjectName("vehicleSelectionDrawer")
        
        self.master_layout = QVBoxLayout()
        self.setLayout(self.master_layout)
        # self.master_layout.setContentsMargins(0, 0, 0, 0)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.c_page = Widget()
        self.c_layout = QHBoxLayout(self.c_page)
        self.c_layout.setContentsMargins(0, 0, 0, 0)

        self.e_page = Widget()
        self.e_layout = QVBoxLayout(self.e_page)
        self.e_layout.setContentsMargins(0, 0, 0, 0)

        self.master_layout.addWidget(self.c_page)
        self.master_layout.addWidget(self.e_page)
        self.set_expanded(True)

        # ==================== NON RENDER

        self.loaded_vehicle_path: str | None = None
        self.loaded_brvfile: brickedit.BRVFile | None = None
        self.loaded_brvfile_data: VehicleData | None = None
        self.last_loaded: QDateTime | None = QDateTime.currentDateTime()

        # ==================== PREP

        placeholder = QIcon(":/assets/icons/placeholder.png")
        no_thumbnail = QIcon(":/assets/icons/missing_thumbnail_v2.png")
        
        # ==================== COLLAPSED

        # Layouts (Left: 2/3, Right 1/3, Expand button) to ~match with Expanded layout button row
        self.c_layout_left = QHBoxLayout()
        self.c_layout.addLayout(self.c_layout_left, stretch=2)
        self.c_layout_right = QHBoxLayout()
        self.c_layout.addLayout(self.c_layout_right, stretch=1)

        # Thumbnail
        self.c_thumbnail = Label()
        self.c_layout_left.addWidget(self.c_thumbnail)
        # self.set_icon call later because it also affects self.e_layout which is defined later

        # Vehicle title
        self.c_vehicle_name = Label("Unnamed", overflow=Label.Overflow.ELIDE_MIDDLE, muted=True)
        self.c_layout_left.addWidget(self.c_vehicle_name, stretch=1)

        # Reload button
        reload_icon = QIcon.fromTheme("view-refresh")
        self.c_btn_reload = Button("Reload", reload_icon, tint_icon=True)
        self.c_btn_reload.clicked.connect(self.reload_btn_pressed)
        self.c_layout_right.addWidget(self.c_btn_reload)

        # Expand button
        self.c_btn_expand = ToolButton(placeholder)
        self.c_layout.addWidget(self.c_btn_expand)
        self.c_btn_expand.clicked.connect(self.toggle_collapsed)


        # ==================== EXPANDED

        # Layout thumb
        self.e_header_layout = QHBoxLayout()
        self.e_layout.addLayout(self.e_header_layout)

        # Thumbnail
        self.e_thumbnail = Label()
        self.e_header_layout.addWidget(self.e_thumbnail)

        # Next to thumbnail
        self.e_title_layout = QVBoxLayout()
        self.e_title_layout.setSpacing(0)
        self.e_header_layout.addLayout(self.e_title_layout, stretch=1)
        self.set_icon(
            no_thumbnail.pixmap(QSize(*self.small_thumbnail_size)),
            no_thumbnail.pixmap(QSize(*self.large_thumbnail_size))
        )

        # Vehicle title
        self.e_vehicle_te = LineEdit(placeholder="Unnamed")
        self.e_vehicle_te.set_max_length(100)
        self.e_vehicle_te.text_changed.connect(self.set_vehicle_name)
        self.e_title_layout.addWidget(self.e_vehicle_te)

        # Vehicle info
        self.e_info_label = Label("No info", muted=True)
        self.e_info_label.set_font_size(11)
        self.e_info_label.qt_widget.setAlignment(Qt.AlignTop)
        self.e_title_layout.addWidget(self.e_info_label)

        # ----- BOTTOM ROW ------
        self.e_btn_row_layout = QHBoxLayout()
        self.e_layout.addLayout(self.e_btn_row_layout)

        # Load button
        load_icon = QIcon.fromTheme("go-up")
        self.e_btn_load = Button("Load", load_icon, tint_icon=True)
        self.e_btn_load.toggled.connect(self.load_btn_toggled)
        self.e_btn_load.set_checkable(True)
        self.e_btn_row_layout.addWidget(self.e_btn_load, stretch=1)

        # Unload button
        unload_icon = QIcon.fromTheme("document-revert")
        self.e_btn_unload = Button("Unload", unload_icon, tint_icon=True)
        self.e_btn_unload.clicked.connect(self.unload_btn_pressed)
        self.e_btn_row_layout.addWidget(self.e_btn_unload, stretch=1)

        # Reload button
        # reload_icon = QIcon.fromTheme("view-refresh") DONE PREVIOUSLY
        self.e_btn_reload = Button("Reload", reload_icon, tint_icon=True)
        self.e_btn_reload.clicked.connect(self.reload_btn_pressed)
        self.e_btn_row_layout.addWidget(self.e_btn_reload, stretch=1)

        # Collapse button
        self.e_btn_collapse = ToolButton(placeholder)
        self.e_btn_row_layout.addWidget(self.e_btn_collapse)
        self.e_btn_collapse.clicked.connect(self.toggle_collapsed)

        # Vehicle selector
        self.e_vehicle_selector = VehicleSelector()
        self.e_vehicle_selector.vehicle_selected.connect(self.load_vehicle)
        self.e_layout.addWidget(self.e_vehicle_selector)
        self.e_vehicle_selector.hide()

        # ====================

        self.update_info_timer = QTimer(self)
        self.update_info_timer.timeout.connect(self.update_info)
        self.update_info_timer.start(1000)


        self.load_vehicle('')  # Set everything to unloaded state
        register_has_theme_and_apply(self)


    # Public stuff
    def get_vehicle_loc(self) -> str | None:
        return self.loaded_vehicle_path

    def get_brvfile_loc(self) -> str | None:
        if self.loaded_vehicle_path is not None:
            return os.path.join(self.loaded_vehicle_path, 'Vehicle.brv')

    def get_brvfile_ref(self) -> brickedit.BRVFile | None:
        """None if no vehicle is loaded. DO NOT EDIT!"""
        return self.loaded_brvfile

    def get_brvfile_ref_data(self) -> VehicleData | None:
        """None if no vehicle is loaded. DO NOT EDIT!"""
        return self.loaded_brvfile_data

    def get_brvfile_copy(self) -> brickedit.BRVFile | None:
        return deepcopy(self.loaded_brvfile)

    def _reset_brvfile_ref(self):
        """Sets loaded brvfile to None and removes all other data related to this vehicle."""
        self.loaded_brvfile = None
        self.loaded_brvfile_data = None

    def _set_brvfile_ref(self, brvfile):
        """Sets brvfile ref and creates other data"""
        self.loaded_brvfile = brvfile
        self.loaded_brvfile_data = VehicleData(brvfile)

    def unload_vehicle(self, restore_text: bool = True):
        old_name = self.e_vehicle_te.get_text()
        self.load_vehicle('')  # Unload vehicle
        if restore_text:
            self.e_vehicle_te.set_text(old_name)


    def save_brv(self, brv: brickedit.BRVFile, show_dialogs: bool = True, description: str | None = None, nothing_happened: bool = False) -> bool:
        # First, serialize
        is_new_vehicle = not self.is_vehicle_loaded()
        try:
            assert brv is not None, "brv is None!"
            assert brv.bricks is not None, "brv.bricks is None!"
            assert isinstance(brv, brickedit.BRVFile), "brv is not a BRVFile instance!"

            if len(brv.bricks) > 50000:
                raise Exception('too long')
            brvf = brv.serialize()

            # Make sure it exists
            if is_new_vehicle:
                success = self._save_new_vehicle_prep(brv=brv, show_dialogs=show_dialogs)
                if not success:
                    raise Exception('skip')

            # Make missing dirs
            os.makedirs(os.path.dirname(self.loaded_vehicle_path), exist_ok=True)

            # Make backup if not new
            if not is_new_vehicle:
                if description is not None:
                    self.mw.backups.full_backup_procedure(self.loaded_vehicle_path, description)
                else:
                    self.mw.backups.full_backup_procedure(self.loaded_vehicle_path)

            # Then save
            with open(os.path.join(self.loaded_vehicle_path, 'Vehicle.brv'), 'wb') as f:
                f.write(brvf)

            # If it's a new vehicle we load it right after to avoid issues
            if is_new_vehicle:
                self.load_vehicle(self.loaded_vehicle_path)

            if show_dialogs:
                if nothing_happened:
                    NothingEverHappensDialog.create(self.mw, saved=True).exec(blocking=False)
                else:
                    VehicleSavedDialog.create(self.mw).exec(blocking=False)

            return True

        except PermissionError as e:
            QMessageBox.critical(self, "Failed to save vehicle", f"BrickEdit-Interface was denied permission to save this vehicle.")

        except OSError as e:
            QMessageBox.critical(self, "Failed to save vehicle", f"BrickEdit-Interface could not save this vehicle. Do you have sufficient storage?")

        except Exception as e:

            if show_dialogs:
                if str(e) == 'too long':
                    QMessageBox.critical(self, "Failed to save vehicle", f"A vehicle can only contain up to 50,000 bricks.")
                elif str(e) == 'skip':
                    pass
                else:
                    QMessageBox.critical(self, "Failed to save vehicle", f"""\
BrickEdit-Interface failed to save this vehicle for unknown reasons. Please report this issue on the BrickEdit discord.

ERROR: {format_exc()}""",)

        # Only reached here in case of error. Reset vehicle state if it was semi-created
        if is_new_vehicle:
            self.loaded_vehicle_path = None



    def _save_new_vehicle_prep(self, brv: brickedit.BRVFile, show_dialogs: bool = True) -> bool:
        """Will create what .save_brv won't create in order to be able to save new vehicles!
        A vehicle MUST be created while calling this or it'll enter a corrupt state."""
        # Get pathes
        vehicles_path = get_vehicles_path()
        vehicle_inner_name = str(lowest_available_number(vehicles_path))
        self.loaded_vehicle_path = os.path.join(vehicles_path, vehicle_inner_name)

        # Retrieve data
        name = self.e_vehicle_te.get_text()

        # Save
        try:
            brmfile = brickedit.BRMFile(brickedit.FILE_EXP_VERSION)
            binary = brmfile.serialize(
                file_name=name,
                description="Generated by BrickEdit-Interface.",
                brick_count=len(brv.bricks)
            )

            logging.info(f"Saving new vehicle metadata, named '{name}' at {self.loaded_vehicle_path}")
            os.makedirs(self.loaded_vehicle_path, exist_ok=True)
            with open(os.path.join(self.loaded_vehicle_path, 'MetaData.brm'), 'wb') as f:
                f.write(binary)

            return True

        except PermissionError as e:
            if not show_dialogs:
                return False
            QMessageBox.critical(self, "Failed to save metadata", f"BrickEdit-Interface was denied permission to save metadata of this vehicle.")
            return False

        except OSError as e:
            if not show_dialogs:
                return False
            if isinstance(e, FileNotFoundError):
                raise e from e
            QMessageBox.critical(self, "Failed to save metadata", f"BrickEdit-Interface could not save metadata of this vehicle. Do you have sufficient storage?")
            return False

        except Exception as e:
            if not show_dialogs:
                return False
            QMessageBox.critical(self, "Failed to save metadata", f"""\
BrickEdit-Interface failed to save metadata of this vehicle for unknown reasons. Please report this issue on the BrickEdit discord.

ERROR: {format_exc()}""")
            return False


    # 'Private' stuff

    def load_btn_toggled(self, state: bool):
        if state:
            self.e_vehicle_selector.show()
        else:
            self.e_vehicle_selector.hide()

    def unload_btn_pressed(self):
        self.load_vehicle('')

    def reload_btn_pressed(self):
        self.e_vehicle_selector.request_reload(ignore_old=True)
        self.load_vehicle(self.loaded_vehicle_path)


    def load_vehicle(self, vehicle_path: str | None):
        if vehicle_path == '':
            vehicle_path = None
        vehicle_path_strictstr = vehicle_path if vehicle_path is not None else ''
        _logger.info('Loading vehicle: %s', repr(vehicle_path))
        self.loaded_vehicle_path = vehicle_path

        # Prep
        no_thumbnail = QIcon(":/assets/icons/missing_thumbnail_v2.png")

        # Update thumbnail
        thumbnail_path = os.path.join(vehicle_path_strictstr, 'Preview.png')
        if vehicle_path is not None and os.path.exists(thumbnail_path):
            thumbnail_icon = QIcon(thumbnail_path)
        else:
            thumbnail_icon = no_thumbnail

        self.set_icon(
            thumbnail_icon.pixmap(QSize(*self.small_thumbnail_size)),
            thumbnail_icon.pixmap(QSize(*self.large_thumbnail_size))
        )

        # Load metadata to get name
        metadata_file = os.path.join(vehicle_path_strictstr, 'MetaData.brm')

        # Update name. If not loaded or no metadata, set blank (unnamed)
        if vehicle_path is None or not os.path.exists(metadata_file):
            self.set_vehicle_name('', edit_file=False)
        else:
            with open(metadata_file, 'rb') as f:
                metadata = bytearray(f.read())
            brmfile = brickedit.BRMFile(brickedit.FILE_MIN_SUPPORTED_VERSION)
            name, = brmfile.deserialize(metadata, config=self.brm_name_deserialization_profile, auto_version=True)
            self.set_vehicle_name(name, edit_file=False)

        # Load brv
        self._reset_brvfile_ref()
        brv_path = os.path.join(vehicle_path_strictstr, 'Vehicle.brv')
        if vehicle_path is not None and os.path.exists(brv_path):
            with open(brv_path, 'rb') as f:
                file = bytearray(f.read())

            version = file[0]
            brvfile = brickedit.BRVFile(version)
            brvfile.deserialize(file)
            self._set_brvfile_ref(brvfile)

        self.last_loaded = QDateTime.currentDateTime()

        # Change accented card
        self.e_vehicle_selector.set_accented_card(vehicle_path)

        # Update last saved / last loaded
        self.update_info()

        # Close vehicle selector and update buttons that can and cannot be enabled
        self.e_btn_load.set_checked(False)
        is_vehicle_loaded = self.is_vehicle_loaded()
        self.e_btn_reload.set_enabled(is_vehicle_loaded)
        self.c_btn_reload.set_enabled(is_vehicle_loaded)
        self.e_btn_unload.set_enabled(is_vehicle_loaded)

        self.vehicle_loaded.emit(vehicle_path)
        _logger.info('Loading vehicle complete')


    def update_info(self):

        vehicle_path = self.loaded_vehicle_path
        if vehicle_path is None:
            self.e_info_label.set_text("No vehicle is loaded. A new vehicle may be created.")
            return

        # Loaded time
        now = QDateTime.currentDateTime()
        last_loaded_time_seconds = self.last_loaded.secsTo(now)
        last_loaded_time_rendered = str_time_since(last_loaded_time_seconds)

        # Last save
        brv_path = os.path.join(vehicle_path, 'Vehicle.brv')
        last_modified_time_seconds = 1e99

        danger_should_be_enabled = False  # For later
        if vehicle_path is not None and os.path.exists(brv_path):
            last_modified_time_os = os.path.getmtime(brv_path)
            last_modified_time = QDateTime.fromSecsSinceEpoch(int(last_modified_time_os))
            last_modified_time_seconds = last_modified_time.secsTo(now)

            danger_should_be_enabled = last_modified_time_seconds < last_loaded_time_seconds  # For later.

        last_modified_time_rendered = str_time_since(last_modified_time_seconds)

        self.e_info_label.set_text(f"Last saved {last_modified_time_rendered} ago\nLast loaded {last_loaded_time_rendered} ago")

        # Update danger styling
        danger_enabled = self.e_btn_reload.get_danger()
        if danger_enabled != danger_should_be_enabled:
            self.e_btn_reload.set_danger(danger_should_be_enabled)
            self.c_btn_reload.set_danger(danger_should_be_enabled)



    def is_vehicle_loaded(self):
        return self.loaded_vehicle_path is not None

    def set_vehicle_name(self, name: str, edit_file: bool = True):
        self.c_vehicle_name.qt_widget.setText(name if name else 'Unnamed')
        self.c_vehicle_name.set_muted(name == '')
        self.e_vehicle_te.qt_widget.setText(name)

        if not edit_file or self.loaded_vehicle_path is None:
            return

        # Custom metadata editing logic is safer here
        metadata_file = os.path.join(self.loaded_vehicle_path, 'MetaData.brm')
        if os.path.exists(metadata_file):
            with open(metadata_file, 'rb') as f:

                version: int = int.from_bytes(f.read(1), 'little')
                name_len: int = int.from_bytes(f.read(2), 'little')
                f.read(name_len)  # Clear out name

                new = bytearray()
                new.extend(version.to_bytes(1, 'little'))
                new.extend(brickedit.p.TextMeta.serialize(name, version, {}))
                new.extend(f.read())  # Everything else we don't really care about

            with open(metadata_file, 'wb') as f:
                f.write(new)

        # Do not do anything if theres no brm yet, it's unloaded
        

    def toggle_collapsed(self):
        self.set_expanded(not self.is_expanded)

    def set_icon(self, pixmap_small: QPixmap, pixmap_large: QPixmap):
        c_new_pixmap = pixmap_small.scaled(*self.small_thumbnail_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.c_thumbnail.qt_widget.setPixmap(c_new_pixmap)
        e_new_pixmap = pixmap_large.scaled(*self.large_thumbnail_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.e_thumbnail.qt_widget.setPixmap(e_new_pixmap)

    def set_expanded(self, expanded: bool):
        if expanded:
            self.c_page.hide()
            self.e_page.show()
        else:
            self.e_page.hide()
            self.c_page.show()
            self.e_btn_load.set_checked(False)
        self.is_expanded = expanded

    def _apply_theme(self, theme: Theme):
        self.setStyleSheet(f"""
            #vehicleSelectionDrawer {{
                border-bottom: 2px solid {theme.border.color};
            }}
        """)

        # --------------- COLLAPSED

        self.c_btn_expand.set_icon(tint_icon(QIcon(":/assets/icons/ExpandSmallIcon.png"), theme.text.color_hex_argb))
        
        # --------------- EXPANDED
        
        self.e_btn_collapse.set_icon(tint_icon(QIcon(":/assets/icons/CollapseSmallIcon.png"), theme.text.color_hex_argb))
