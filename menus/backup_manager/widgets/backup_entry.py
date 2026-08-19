from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QMessageBox
from PySide6.QtGui import QIcon, QColor

from os import path
import subprocess
import sys
import shutil

from systems.backup import BackupSystem

from ui.widgets import Surface, SurfaceStyle, Label, Button, ToolButton
from ui.theme import Theme, register_has_theme_and_apply
from ui.models import TooltipContents

from utils import tint_icon

from brickedit import vhelper

from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


def open_path(path):
    if sys.platform.startswith("win"):
        from os import startfile
        startfile(path)
        
    if sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", path])


RECOVER_BTN_ICON = QIcon.fromTheme("edit-undo")
OPEN_DIR_BTN_ICON = QIcon.fromTheme("folder-open")
BIN_BTN_ICON = QIcon.fromTheme("user-trash")
DELETE_BTN_ICON = QIcon.fromTheme("window-close")


class BackupEntry(Surface):
    def __init__(self, mw: "BrickEditInterface", call_on_backup_deleted: Callable[[bool, str], None], vehicle_path, backup_path, parent=None):
        super().__init__(parent)

        self.master_layout = self.layout()

        self.main_window = mw

        self.call_on_backup_deleted = call_on_backup_deleted
        self.vehicle_path = vehicle_path
        self.backup_path = backup_path

        # Prepare variables
        backup_metadata = self.main_window.backups.fetch_backup_metadata(self.backup_path)
        self.backup_desc = backup_metadata.get(BackupSystem.TOML_DESCRIPTION_TAG, "No description provided.")
        self.backup_dt = vhelper.from_net_ticks(backup_metadata.get(BackupSystem.TOML_TIME_TAG, 0))

        backup_folder_name = path.basename(self.backup_path)
        backup_folder_short_type = backup_folder_name[ :2]
        backup_type = f"{self.main_window.backups.get_backup_name(backup_folder_short_type)} backup"
        if self.backup_dt.year > 2000:
            backup_dt_text = self.backup_dt.strftime('%y-%m-%d\n%H:%M:%S')
        else:
            backup_dt_text = self.backup_dt.strftime('%Y-%m-%d\n%H:%M:%S') + "(?)"

        if backup_folder_short_type == "ug":
            self.set_surface_style(SurfaceStyle.ACCENT)

        # DATE AND BUTTONS
        # Layout
        self.info_and_buttons_layout = QHBoxLayout()
        self.master_layout.addLayout(self.info_and_buttons_layout)

        # dt
        self.info_layout = QVBoxLayout()
        self.dt_text_label = Label(backup_dt_text, font_weight=1000)
        self.info_layout.addWidget(self.dt_text_label)
        self.info_and_buttons_layout.addLayout(self.info_layout, stretch=1)

        # Buttons layout
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.info_and_buttons_layout.addLayout(self.buttons_layout)

        # Open directory button
        self.open_dir_button = ToolButton(icon=OPEN_DIR_BTN_ICON, tint_icon=True)
        self.open_dir_button.set_tooltip(TooltipContents("Open backup directory"))
        self.open_dir_button.clicked.connect(lambda: open_path(self.backup_path))
        self.buttons_layout.addWidget(self.open_dir_button)

        # Recover backup button
        self.recover_button = ToolButton(icon=RECOVER_BTN_ICON, tint_icon=True)
        self.recover_button.set_tooltip(TooltipContents("Recover backup"))
        self.recover_button.clicked.connect(self.recover_backup_btn)
        self.buttons_layout.addWidget(self.recover_button)

        # Send to trash bin button
        self.bin_button = ToolButton(icon=BIN_BTN_ICON, tint_icon=True)
        self.bin_button.set_tooltip(TooltipContents("Send to recycle bin"))
        self.bin_button.clicked.connect(self.bin_backup_btn)
        self.buttons_layout.addWidget(self.bin_button)

        # Delete button
        self.delete_button = ToolButton(icon=DELETE_BTN_ICON, tint_icon=False)
        self.delete_button.set_tooltip(TooltipContents("Delete permanantly"))
        self.delete_button.clicked.connect(self.delete_backup_btn)
        self.buttons_layout.addWidget(self.delete_button)


        # THE REST
        self.backup_type_label = Label(backup_type)
        self.master_layout.addWidget(self.backup_type_label)

        self.backup_desc_label = Label(self.backup_desc)
        self.master_layout.addWidget(self.backup_desc_label)


        register_has_theme_and_apply(self)



    def recover_backup_btn(self):
        dlg = QMessageBox()
        dlg.setWindowTitle("Recover backup")
        dlg.setText("Are you sure you want to recover this backup? This will overwrite the current vehicle.")
        dlg.setIcon(QMessageBox.Warning)
        dlg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        dlg.setDefaultButton(QMessageBox.Ok)
        result = dlg.exec()

        if result == QMessageBox.Ok:
            brv_file = path.join(self.vehicle_path, "Vehicle.brv")
            # if not os.path.exists(brv_file):
            #     return
            backup_brv_file = path.join(self.backup_path, "Vehicle.brv")
            if not path.exists(backup_brv_file):
                return
            shutil.copy2(backup_brv_file, brv_file)

    def delete_backup_btn(self):
        dlg = QMessageBox()
        dlg.setWindowTitle("Delete backup")
        dlg.setText(f"Are you sure you want to delete {self.backup_path}? This action cannot be undone.")
        dlg.setIcon(QMessageBox.Warning)
        dlg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        dlg.setDefaultButton(QMessageBox.Cancel)
        result = dlg.exec()
        if result == QMessageBox.Ok:
            self.call_on_backup_deleted(False, self.backup_path)

    def bin_backup_btn(self):
        self.call_on_backup_deleted(True, self.backup_path)


    def _apply_theme(self, theme: Theme):

        if hasattr(self, "delete_button"):
            self.delete_button.set_icon(
                tint_icon(DELETE_BTN_ICON, theme.danger.color_hex_argb)
            )
