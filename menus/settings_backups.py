from PySide6.QtWidgets import QSlider

from . import base
from .widgets import *


class SettingsAndBackupsMenu(base.BaseMenu):

    MAX_BACKUP_COUNT = 20
    MAX_BACKUP_SIZE_KB = 65536
    BACKUP_SIZE_STEP_KB = 256

    def __init__(self, mw):
        super().__init__(mw)
        
        
        # ---------------
        # Backup Settings
        # ---------------
        
        
        self.backups_part_header = LargeLabel("Backups", 4)
        self.master_layout.addWidget(self.backups_part_header)

        # Warning
        self.warning_widget = SquareWidget()
        self.warning_widget.set_severity(True)
        self.warning_widget_layout = QHBoxLayout(self.warning_widget)
        self.warning_widget_label = QLabel("BrickEdit-Interface backups are meant to help recover from data losses caused by this software.\nBackups are stored in the same directory as vehicles. Deleting vehicles will also delete backups.")
        self.warning_widget_label.setWordWrap(True)
        self.warning_widget_layout.addWidget(self.warning_widget_label)
        self.master_layout.addWidget(self.warning_widget)

        self.main_window.settings.st_backup_count_limit
        
        # Short term
        self.st_label = QLabel("Short term backups limit (created when a vehicle is modified) / creation")
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
        self.lt_label = QLabel("Long term backups limit (created once per session when a vehicle is modified) / creation")
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
        
        self.master_layout.addStretch()


    def get_menu_name(self) -> str:
        return "Settings and backups"

    def get_icon(self) -> QIcon:
        return QIcon(":/assets/icons/placeholder.png")


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


    def update_slider_labels(self):
        self.st_count_limit_label.setText(f"{self.main_window.settings.st_backup_count_limit} Backups")

        if self.main_window.settings.st_backup_size_limit_kb < 10_000:
            st_text = f"{self.main_window.settings.st_backup_size_limit_kb:,} KB"
        else:
            st_text = f"{self.main_window.settings.st_backup_size_limit_kb / 1024:,} MB"
        self.st_size_limit_label.setText(st_text)

        self.lt_count_limit_label.setText(f"{self.main_window.settings.lt_backup_count_limit} Backups")

        if self.main_window.settings.lt_backup_size_limit_kb < 10_000:
            lt_text = f"{self.main_window.settings.lt_backup_size_limit_kb:,} KB"
        else:
            lt_text = f"{self.main_window.settings.lt_backup_size_limit_kb / 1024:,} MB"
        self.lt_size_limit_label.setText(lt_text)
