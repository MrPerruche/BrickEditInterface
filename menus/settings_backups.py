from PySide6.QtWidgets import QSlider
from PySide6.QtCore import QUrl, QSize
from PySide6.QtGui import QDesktopServices

import shutil
from send2trash import send2trash
from pathlib import Path

from . import base
from .widgets import *

from utils import repr_file_size, dir_size, get_vehicles_path, clear_layout


class SettingsAndBackupsMenu(base.BaseMenu):

    MAX_BACKUP_COUNT = 20
    MAX_BACKUP_SIZE_KB = 65536
    BACKUP_SIZE_STEP_KB = 256

    def __init__(self, mw):
        super().__init__(mw)
        
        # ----------------
        # Contron settings
        # ----------------
        
        self.control_layout = QHBoxLayout()
        self.master_layout.addLayout(self.control_layout)
        
        # Reset settings
        self.reset_settings_button = QPushButton("Reset settings")
        self.reset_settings_button.clicked.connect(self.reset_settings)
        self.control_layout.addWidget(self.reset_settings_button)
        
        # Open settings file in file explorer
        self.open_settings_file_button = QPushButton("Reveal in file explorer")
        self.open_settings_file_button.clicked.connect(self.open_settings_file)
        self.control_layout.addWidget(self.open_settings_file_button)
        
        
        
        # ---------------
        # Backup Settings
        # ---------------
        
        
        self.backups_part_header = LargeLabel("Backups", 4)
        self.master_layout.addWidget(self.backups_part_header)

        # Warning
        self.warning_widget = SquareWidget()
        self.warning_widget.set_state(SquareState.HIGHLIGHT)
        self.warning_widget_layout = QHBoxLayout(self.warning_widget)
        self.warning_widget_label = QLabel("BrickEdit-Interface backups are meant to help recover from mistakes made using this software.\nBackups are stored in the same directory as vehicles. Deleting vehicles will also delete backups.")
        self.warning_widget_label.setWordWrap(True)
        self.warning_widget_layout.addWidget(self.warning_widget_label)
        self.master_layout.addWidget(self.warning_widget)

        self.main_window.settings.st_backup_count_limit
        
        # Short term
        self.st_label = QLabel("Short term backups limit / Vehicle\n→ Created when a vehicle is modified")
        self.st_label.setWordWrap(True)
        self.master_layout.addWidget(self.st_label)

        # Short term count
        self.st_backup_count_layout = QHBoxLayout()
        self.master_layout.addLayout(self.st_backup_count_layout)

        self.st_count_limit_slider = QSlider(Qt.Horizontal)
        self.st_count_limit_slider.setValue(self.main_window.settings.st_backup_count_limit)
        self.st_count_limit_slider.setRange(0, self.MAX_BACKUP_COUNT)
        self.st_count_limit_slider.valueChanged.connect(lambda value: self.slider_updated(value, 'st_count'))
        self.st_backup_count_layout.addWidget(self.st_count_limit_slider, 10)

        self.st_count_limit_label = QLabel("Backups")
        self.st_count_limit_label.setAlignment(Qt.AlignRight)
        self.st_backup_count_layout.addWidget(self.st_count_limit_label, 3)


        # Short term KB
        self.st_backup_size_layout = QHBoxLayout()
        self.master_layout.addLayout(self.st_backup_size_layout)
    
        self.st_size_limit_slider = QSlider(Qt.Horizontal)
        self.st_size_limit_slider.setValue(self.main_window.settings.st_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB)
        self.st_size_limit_slider.setRange(0, self.MAX_BACKUP_SIZE_KB // self.BACKUP_SIZE_STEP_KB)
        self.st_size_limit_slider.valueChanged.connect(lambda value: self.slider_updated(value, 'st_size'))
        self.st_backup_size_layout.addWidget(self.st_size_limit_slider, 10)

        self.st_size_limit_label = QLabel("KB")
        self.st_size_limit_label.setAlignment(Qt.AlignRight)
        self.st_backup_size_layout.addWidget(self.st_size_limit_label, 3)


        # Long term
        self.lt_label = QLabel("Long term backups limit / Vehicle\n→ Created once per session when a vehicle is modified")
        self.lt_label.setWordWrap(True)
        self.master_layout.addWidget(self.lt_label)

        # Long term count
        self.lt_count_limit_layout = QHBoxLayout()
        self.master_layout.addLayout(self.lt_count_limit_layout)

        self.lt_count_limit_slider = QSlider(Qt.Horizontal)
        self.lt_count_limit_slider.setValue(self.main_window.settings.lt_backup_count_limit)
        self.lt_count_limit_slider.setRange(0, self.MAX_BACKUP_COUNT)
        self.lt_count_limit_slider.valueChanged.connect(lambda value: self.slider_updated(value, 'lt_count'))
        self.lt_count_limit_layout.addWidget(self.lt_count_limit_slider, 10)

        self.lt_count_limit_label = QLabel("Backups")
        self.lt_count_limit_label.setAlignment(Qt.AlignRight)
        self.lt_count_limit_layout.addWidget(self.lt_count_limit_label, 3)


        # Long term KB
        self.lt_size_limit_layout = QHBoxLayout()
        self.master_layout.addLayout(self.lt_size_limit_layout)

        self.lt_size_limit_slider = QSlider(Qt.Horizontal)
        self.lt_size_limit_slider.setValue(self.main_window.settings.lt_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB)
        self.lt_size_limit_slider.setRange(0, self.MAX_BACKUP_SIZE_KB // self.BACKUP_SIZE_STEP_KB)
        self.lt_size_limit_slider.valueChanged.connect(lambda value: self.slider_updated(value, 'lt_size'))
        self.lt_size_limit_layout.addWidget(self.lt_size_limit_slider, 10)

        self.lt_size_limit_label = QLabel("KB")
        self.lt_size_limit_label.setAlignment(Qt.AlignRight)
        self.lt_size_limit_layout.addWidget(self.lt_size_limit_label, 3)

        self.update_slider_labels()
        
        
        # ---------------
        # Backup manager
        # ---------------

        # Recovery label
        self.recover_label = LargeLabel("Backup manager", 4)
        self.master_layout.addWidget(self.recover_label)
        
        # Delete excess backups
        self.excess_label = QLabel("No excess backups found.")
        self.master_layout.addWidget(self.excess_label)
        
        self.delete_layout = QHBoxLayout()
        self.master_layout.addLayout(self.delete_layout)

        self.bin_excess_button = QPushButton("Send to recycle bin")
        self.bin_excess_button.setEnabled(False)
        self.bin_excess_button.clicked.connect(lambda: self.delete_excess_backups(True))
        self.delete_layout.addWidget(self.bin_excess_button)

        self.del_excess_button = QPushButton("Delete permanantly")
        self.del_excess_button.setEnabled(False)
        self.del_excess_button.clicked.connect(lambda: self.delete_excess_backups(False))
        self.delete_layout.addWidget(self.del_excess_button)
        
        self.update_excess_label()
        
        
        # Vehicle selector
        self.vehicle_selector = VehicleWidget(VehicleWidgetMode.SELECT_AND_RELOAD, [self.update_backup_recovery_entries], must_deserialize=False)
        self.master_layout.addWidget(self.vehicle_selector)
        
        # Backup entries for that vehicle
        self.backup_entries = SquareWidget()
        self.backup_entries_layout = QVBoxLayout(self.backup_entries)
        self.master_layout.addWidget(self.backup_entries)
        
        
        
        self.update_backup_recovery_entries()
        
        self.master_layout.addStretch()


    def get_menu_name(self) -> str:
        return "Settings and backups"

    def get_icon(self) -> QIcon:
        return QIcon(":/assets/icons/placeholder.png")


    def update_backup_recovery_entries(self):
        # Make sure it is a blank slate
        clear_layout(self.backup_entries_layout)

        # MANUAL USER INPUTS
        # Label
        self.create_backup_label = QLabel("Create a backup manually:")
        self.backup_entries_layout.addWidget(self.create_backup_label)
        # Description and add button layout
        self.create_backup_desc_btn_layout = QHBoxLayout()
        self.backup_entries_layout.addLayout(self.create_backup_desc_btn_layout)
        # Description
        self.create_backup_desc = QLineEdit()
        self.create_backup_desc.setPlaceholderText("My manual backup description")
        self.create_backup_desc_btn_layout.addWidget(self.create_backup_desc)
        # Add button
        self.create_backup_btn = QPushButton()
        self.create_backup_btn_icon = QIcon.fromTheme("document-save")
        self.create_backup_btn.setIcon(self.create_backup_btn_icon)
        self.create_backup_btn.setFixedSize(QSize(32, 32))
        self.create_backup_btn.clicked.connect(self.create_manual_backup)
        self.create_backup_desc_btn_layout.addWidget(self.create_backup_btn)

        # Gray out manual input if no vehicle is selected
        self.create_backup_label.setDisabled(self.vehicle_selector.brv_file is None)
        self.create_backup_desc.setDisabled(self.vehicle_selector.brv_file is None)
        self.create_backup_btn.setDisabled(self.vehicle_selector.brv_file is None)
        
        # Get the backups. If no vehicle is loaded, pretend one is loaded and we got an empty list
        result = []
        brv_file = self.vehicle_selector.brv_file
        if brv_file is not None:
            vehicle_file = os.path.dirname(brv_file)
            result = self.main_window.backups.find_backups(vehicle_file)
        result.sort(reverse=True)

        # If no backup is found, leave a label.
        if not result:
            self.backup_entries_layout.addWidget(QLabel("No backups found."))
            self.update_excess_label()
            return

        for backup_path in result:
            backup_entry = BackupEntry(
                self.main_window, self.delete_backup,
                str(Path(vehicle_file).resolve()),
                str(Path(backup_path).resolve()))
            self.backup_entries_layout.addWidget(backup_entry)

        self.update_excess_label()


    def create_manual_backup(self):
        description = self.create_backup_desc.text()
        if description == "":
            description = "My manual backup description"
        self.main_window.backups.create_backup(
            os.path.dirname(self.vehicle_selector.brv_file),  # Vehicle directory
            description, True  # Force long-term backup
        )
        self.update_backup_recovery_entries()


    def delete_backup(self, recycle_bin: bool, backup_path: str):
        if recycle_bin:
            send2trash(backup_path)
        else:
            shutil.rmtree(backup_path)
        self.update_backup_recovery_entries()


    def update_excess_label(self):
        excess = self.main_window.backups.find_all_excess(get_vehicles_path())
        excess_size = 0
        for excess_dir in excess:
            excess_size += dir_size(excess_dir)
        self.excess_label.setText(f"Found {len(excess)} excess backups - total size: {repr_file_size(excess_size)}")
        self.excess_label.setWordWrap(True)
        if len(excess) > 0:
            self.bin_excess_button.setEnabled(True)
            self.del_excess_button.setEnabled(True)
        else:
            self.bin_excess_button.setEnabled(False)
            self.del_excess_button.setEnabled(False)


    def delete_excess_backups(self, recycle_bin):
        excess = self.main_window.backups.find_all_excess(get_vehicles_path())
        for excess_dir in excess:
            if recycle_bin:
                send2trash(excess_dir)
            else:
                shutil.rmtree(excess_dir)
        self.update_excess_label()


    def open_settings_file(self):
        target = self.main_window.settings.get_settings_file_path().parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(target))


    def reset_settings(self):
        self.main_window.settings.create_default_settings()
        self.update_slider_labels()
        self.update_slider_values()


    def slider_updated(self, value, type: str):
        match type:
            case 'st_count':
                self.main_window.settings.st_backup_count_limit = value
            case 'st_size':
                self.main_window.settings.st_backup_size_limit_kb = value * self.BACKUP_SIZE_STEP_KB
            case 'lt_count':
                self.main_window.settings.lt_backup_count_limit = value
            case 'lt_size':
                self.main_window.settings.lt_backup_size_limit_kb = value * self.BACKUP_SIZE_STEP_KB
            case _: pass

        self.update_slider_labels()
        self.main_window.settings.save()


    def update_slider_labels(self):
        self.st_count_limit_label.setText(f"{self.main_window.settings.st_backup_count_limit} Backups")

        st_text = repr_file_size(self.main_window.settings.st_backup_size_limit_kb * 1024, 2, 10_000)
        self.st_size_limit_label.setText(st_text)

        self.lt_count_limit_label.setText(f"{self.main_window.settings.lt_backup_count_limit} Backups")

        lt_text = repr_file_size(self.main_window.settings.lt_backup_size_limit_kb * 1024, 2, 10_000)
        self.lt_size_limit_label.setText(lt_text)

    def update_slider_values(self):
        self.st_count_limit_slider.setValue(self.main_window.settings.st_backup_count_limit)
        self.st_size_limit_slider.setValue(self.main_window.settings.st_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB)
        self.lt_count_limit_slider.setValue(self.main_window.settings.lt_backup_count_limit)
        self.lt_size_limit_slider.setValue(self.main_window.settings.lt_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB)
