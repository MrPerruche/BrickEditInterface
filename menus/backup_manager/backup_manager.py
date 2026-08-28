from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import QUrl, QSize, Qt
from PySide6.QtGui import QDesktopServices, QIcon

import os.path as path
import shutil
from send2trash import send2trash
from pathlib import Path

from menus import base

from ui.widgets import Label, StyledLabel, LabelStyle, Button, Surface, SurfaceStyle, Slider, LineEdit, ToolButton
from ui.models import TooltipContents

from utils import repr_file_size, dir_size, get_vehicles_path, wipe_layout
from menus.backup_manager.widgets.backup_entry import BackupEntry

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class SettingsAndBackupsMenu(base.BaseMenu):

    MAX_BACKUP_COUNT = 20
    MAX_BACKUP_SIZE_KB = 32768
    BACKUP_SIZE_STEP_KB = 256

    def __init__(self, mw: 'BrickEditInterface'):
        super().__init__(mw)
        
        # ---------------
        # Backup manager
        # ---------------

        # Warning
        self.warning_widget = Surface(surface_style=SurfaceStyle.ACCENT)
        self.warning_widget_layout = self.warning_widget.layout()
        self.warning_widget_label = Label("BrickEdit-Interface backups are here to help you experiment with your creations and recover from mistakes made using this software.\nDeleting a vehicle will also delete its backups.")
        self.warning_widget_layout.addWidget(self.warning_widget_label)
        self.master_layout.addWidget(self.warning_widget)

        # Recovery label
        # self.recover_label = LargeLabel("Backup manager", 4)
        # self.master_layout.addWidget(self.recover_label)
        
        # Delete excess backups
        self.excess_label = Label("No excess backups found.")
        self.master_layout.addWidget(self.excess_label)
        
        self.delete_layout = QHBoxLayout()
        self.master_layout.addLayout(self.delete_layout)

        self.bin_excess_button = Button("Send to recycle bin")
        self.bin_excess_button.setEnabled(False)
        self.bin_excess_button.clicked.connect(lambda: self.delete_excess_backups(True))
        self.delete_layout.addWidget(self.bin_excess_button)

        self.del_excess_button = Button("Delete permanantly")
        self.del_excess_button.setEnabled(False)
        self.del_excess_button.clicked.connect(lambda: self.delete_excess_backups(False))
        self.delete_layout.addWidget(self.del_excess_button)
        
        self.update_excess_label()


        # Backup entries for that vehicle
        self.backup_entries = Surface()
        self.backup_entries_layout = self.backup_entries.layout()
        self.master_layout.addWidget(self.backup_entries)


        # ---------------
        # Backup Settings
        # ---------------
        
        
        self.backups_part_header = StyledLabel("Backup settings", LabelStyle.HEADER_4)
        self.master_layout.addWidget(self.backups_part_header)
        
        # Contron settings
        
        self.control_layout = QHBoxLayout()
        self.master_layout.addLayout(self.control_layout)
        
        # Reset settings
        self.reset_settings_button = Button("Reset settings")
        self.reset_settings_button.clicked.connect(self.reset_settings)
        self.control_layout.addWidget(self.reset_settings_button)
        
        # Open settings file in file explorer
        self.open_settings_file_button = Button("Reveal in file explorer")
        self.open_settings_file_button.clicked.connect(self.open_settings_file)
        self.control_layout.addWidget(self.open_settings_file_button)

        self.main_window.settings.st_backup_count_limit

        # Short term
        self.st_label = Label(f"Short term backups limit, per vehicle")
        self.st_label.set_tooltip(TooltipContents(
            "Short term backups are created when you modify a vehicle with BrickEdit-Interface.\n" +
            f"They are considered old after {self.main_window.backups.SHORT_TERM_BACKUP_MAX_DAYS} days, and will be deleted if the vehicle is modified again.\n" +
            f"Old short term backups can also be deleted manually by clearing excess backups."
        ))
        self.master_layout.addWidget(self.st_label)

        # Short term count
        self.st_backup_count_layout = QHBoxLayout()
        self.master_layout.addLayout(self.st_backup_count_layout)

        self.st_count_limit_slider = Slider(
            values = range(0, self.MAX_BACKUP_COUNT),
            default_value = self.main_window.settings.st_backup_count_limit
        )
        self.st_count_limit_slider.value_changed.connect(lambda value: self.slider_updated(value, 'st_count'))
        self.st_backup_count_layout.addWidget(self.st_count_limit_slider, 10)

        self.st_count_limit_label = Label("Backups")
        self.st_count_limit_label.qt_widget.setAlignment(Qt.AlignRight)
        self.st_backup_count_layout.addWidget(self.st_count_limit_label, 3)


        # Short term KB
        self.st_backup_size_layout = QHBoxLayout()
        self.master_layout.addLayout(self.st_backup_size_layout)
    
        self.st_size_limit_slider = Slider(
            values = range(0, self.MAX_BACKUP_SIZE_KB // self.BACKUP_SIZE_STEP_KB),
            default_value = self.main_window.settings.st_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB
        )
        self.st_size_limit_slider.value_changed.connect(lambda value: self.slider_updated(value, 'st_size'))
        self.st_backup_size_layout.addWidget(self.st_size_limit_slider, 10)

        self.st_size_limit_label = Label("KB")
        self.st_size_limit_label.set_alignment(Qt.AlignRight)
        self.st_backup_size_layout.addWidget(self.st_size_limit_label, 3)


        # Long term
        self.lt_label = Label("Long term backups limit, per vehicle")
        self.lt_label.set_tooltip(TooltipContents(
            "Long term backups are created when a vehicle is modified for the first time in the current BrickEdit-Interface session.\n" +
            "They cannot be deleted automatically."
        ))
        self.master_layout.addWidget(self.lt_label)

        # Long term count
        self.lt_count_limit_layout = QHBoxLayout()
        self.master_layout.addLayout(self.lt_count_limit_layout)

        self.lt_count_limit_slider = Slider(
            values = range(0, self.MAX_BACKUP_COUNT),
            default_value = self.main_window.settings.lt_backup_count_limit
        )
        self.lt_count_limit_slider.value_changed.connect(lambda value: self.slider_updated(value, 'lt_count'))
        self.lt_count_limit_layout.addWidget(self.lt_count_limit_slider, 10)

        self.lt_count_limit_label = Label("Backups")
        self.lt_count_limit_label.set_alignment(Qt.AlignRight)
        self.lt_count_limit_layout.addWidget(self.lt_count_limit_label, 3)


        # Long term KB
        self.lt_size_limit_layout = QHBoxLayout()
        self.master_layout.addLayout(self.lt_size_limit_layout)

        self.lt_size_limit_slider = Slider(
            values = range(0, self.MAX_BACKUP_SIZE_KB // self.BACKUP_SIZE_STEP_KB),
            default_value = self.main_window.settings.lt_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB
        )
        self.lt_size_limit_slider.value_changed.connect(lambda value: self.slider_updated(value, 'lt_size'))
        self.lt_size_limit_layout.addWidget(self.lt_size_limit_slider, 10)

        self.lt_size_limit_label = Label("KB")
        self.lt_size_limit_label.set_alignment(Qt.AlignRight)
        self.lt_size_limit_layout.addWidget(self.lt_size_limit_label, 3)

        self.main_window.vehicle_selector_banner.vehicle_loaded.connect(self.update_backup_recovery_entries)

        self.update_slider_labels()
        self.update_backup_recovery_entries()
        self.master_layout.addStretch()


    def get_menu_name(self) -> str:
        return "Backup Manager"

    def _make_menu_info(self) -> base.MenuInfo:
        return base.MenuInfo(QIcon(":/assets/icons/BackupIcon.png"), True)


    def update_backup_recovery_entries(self):
        # Make sure it is a blank slate
        wipe_layout(self.backup_entries_layout)

        # MANUAL USER INPUTS
        # Label
        self.create_backup_label = Label("Create a backup manually:")
        self.backup_entries_layout.addWidget(self.create_backup_label)
        # Description and add button layout
        self.create_backup_desc_btn_layout = QHBoxLayout()
        self.backup_entries_layout.addLayout(self.create_backup_desc_btn_layout)
        # Description
        self.create_backup_desc = LineEdit()
        self.create_backup_desc.set_placeholder("My manual backup description")
        self.create_backup_desc_btn_layout.addWidget(self.create_backup_desc)
        # Add button
        create_backup_btn_icon = QIcon.fromTheme("document-save")
        self.create_backup_btn = ToolButton(icon=create_backup_btn_icon, tint_icon=True)
        self.create_backup_btn.clicked.connect(self.create_manual_backup)
        self.create_backup_desc_btn_layout.addWidget(self.create_backup_btn)

        # Gray out manual input if no vehicle is selected
        vehicle_not_selected = not self.main_window.vehicle_selector_banner.is_vehicle_loaded()
        self.create_backup_label.setDisabled(vehicle_not_selected)
        self.create_backup_desc.setDisabled(vehicle_not_selected)
        self.create_backup_btn.setDisabled(vehicle_not_selected)
        
        # Get the backups. If no vehicle is loaded, pretend one is loaded and we got an empty list
        result = []
        brv_file = self.main_window.vehicle_selector_banner.get_brvfile_loc()
        if brv_file is not None:
            vehicle_file = path.dirname(brv_file)
            result = self.main_window.backups.find_backups(vehicle_file)
        result.sort(reverse=True)

        # If no backup is found, leave a label.
        if not result:
            self.backup_entries_layout.addWidget(Label("No backups found."))
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
        description = self.create_backup_desc.get_text()
        if description == "":
            description = "My manual backup description"
        self.main_window.backups.create_backup(
            self.main_window.vehicle_selector_banner.get_vehicle_loc(),  # Vehicle directory
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
        self.excess_label.set_text(f"Found {len(excess)} excess backups - total size: {repr_file_size(excess_size)}")
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
        self.st_count_limit_label.set_text(f"{self.main_window.settings.st_backup_count_limit} Backups")

        st_text = repr_file_size(self.main_window.settings.st_backup_size_limit_kb * 1024, 2, 10_000)
        self.st_size_limit_label.set_text(st_text)

        self.lt_count_limit_label.set_text(f"{self.main_window.settings.lt_backup_count_limit} Backups")

        lt_text = repr_file_size(self.main_window.settings.lt_backup_size_limit_kb * 1024, 2, 10_000)
        self.lt_size_limit_label.set_text(lt_text)

    def update_slider_values(self):
        self.st_count_limit_slider.set_value(self.main_window.settings.st_backup_count_limit)
        self.st_size_limit_slider.set_value(self.main_window.settings.st_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB)
        self.lt_count_limit_slider.set_value(self.main_window.settings.lt_backup_count_limit)
        self.lt_size_limit_slider.set_value(self.main_window.settings.lt_backup_size_limit_kb // self.BACKUP_SIZE_STEP_KB)
