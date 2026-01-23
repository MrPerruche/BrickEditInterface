from PySide6.QtWidgets import QSlider
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

import shutil
from send2trash import send2trash

from . import base
from .widgets import *

from utils import repr_file_size, dir_size, get_vehicles_path


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
        
        self.master_layout.addStretch()


    def get_menu_name(self) -> str:
        return "Settings and backups"

    def get_icon(self) -> QIcon:
        return QIcon(":/assets/icons/placeholder.png")


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
