import os
import shutil

from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtGui import QIcon, QColor, QPainter, QFont
from PySide6.QtCore import QSize

from backup_system import BackupSystem

from .square_widget import SquareWidget, SquareState

from brickedit import vhelper

from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface

class BackupEntry(SquareWidget):
    def __init__(self, mw: "BrickEditInterface", call_on_backup_deleted: Callable[[bool, str], None], vehicle_path, backup_path, parent=None):
        super().__init__(parent)
        
        self.master_layout = QVBoxLayout(self)
        self.setLayout(self.master_layout)

        self.main_window = mw

        self.call_on_backup_deleted = call_on_backup_deleted
        self.vehicle_path = vehicle_path
        self.backup_path = backup_path

        # Prepare variables
        backup_metadata = self.main_window.backups.fetch_backup_metadata(self.backup_path)
        self.backup_desc = backup_metadata.get(BackupSystem.TOML_DESCRIPTION_TAG, "No description provided.")
        self.backup_dt = vhelper.from_net_ticks(backup_metadata.get(BackupSystem.TOML_TIME_TAG, 0))

        backup_folder_name = os.path.basename(self.backup_path)
        backup_folder_short_type = backup_folder_name[ :2]
        backup_type = f"{self.main_window.backups.get_backup_name(backup_folder_short_type)} backup"
        backup_dt_text = f"{self.backup_dt.strftime('%y-%m-%d\n%H:%M:%S')}"

        if backup_folder_short_type == "ug":
            self.set_state(SquareState.HIGHLIGHT)

        # DATE AND BUTTONS
        # Layout
        self.info_and_buttons_layout = QHBoxLayout()
        self.master_layout.addLayout(self.info_and_buttons_layout)

        # dt
        self.info_layout = QVBoxLayout()
        self.dt_text_label = QLabel(backup_dt_text)
        self.dt_text_label.setWordWrap(True)
        dt_text_label_font = QFont()
        dt_text_label_font.setBold(True)
        dt_text_label_font.setFamily("Consolas")
        self.dt_text_label.setFont(dt_text_label_font)
        self.info_layout.addWidget(self.dt_text_label)
        self.info_and_buttons_layout.addLayout(self.info_layout)

        # Buttons layout
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.info_and_buttons_layout.addLayout(self.buttons_layout)

        # Open directory button
        self.open_dir_button = QPushButton()
        self.open_dir_button.setToolTip("Open backup directory")
        self.open_dir_button_icon = QIcon.fromTheme("folder-open")
        self.open_dir_button.setFixedSize(32, 32)
        self.open_dir_button.setIcon(self.open_dir_button_icon)
        self.open_dir_button.clicked.connect(lambda: os.startfile(self.backup_path))
        self.buttons_layout.addWidget(self.open_dir_button)

        # Recover backup button
        self.recover_button = QPushButton()
        self.recover_button.setToolTip("Recover backup")
        self.recover_button_icon = QIcon.fromTheme("edit-undo")
        self.recover_button.setFixedSize(32, 32)
        self.recover_button.setIcon(self.recover_button_icon)
        self.recover_button.clicked.connect(self.recover_backup_btn)
        self.buttons_layout.addWidget(self.recover_button)

        # Send to trash bin button
        self.bin_button = QPushButton()
        self.bin_button.setToolTip("Send to recycle bin")
        self.bin_button_icon = QIcon.fromTheme("user-trash")
        self.bin_button.setFixedSize(32, 32)
        self.bin_button.setIcon(self.bin_button_icon)
        self.bin_button.clicked.connect(self.bin_backup_btn)
        self.buttons_layout.addWidget(self.bin_button)

        # Delete button
        self.delete_button = QPushButton()
        self.delete_button.setToolTip("Permanantly delete")
        self.delete_button_icon = colored_icon("window-close", QColor(255, 64, 80))
        self.delete_button.setFixedSize(32, 32)
        self.delete_button.setIcon(self.delete_button_icon)
        self.delete_button.clicked.connect(self.delete_backup_btn)
        self.buttons_layout.addWidget(self.delete_button)


        # THE REST
        self.backup_type_label = QLabel(backup_type)
        self.backup_type_label.setWordWrap(True)
        self.master_layout.addWidget(self.backup_type_label)

        self.backup_desc_label = QLabel(self.backup_desc)
        self.backup_desc_label.setWordWrap(True)
        self.master_layout.addWidget(self.backup_desc_label)



    def recover_backup_btn(self):
        dlg = QMessageBox()
        dlg.setWindowTitle("Recover backup")
        dlg.setText("Are you sure you want to recover this backup? This will overwrite the current vehicle.")
        dlg.setIcon(QMessageBox.Warning)
        dlg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        dlg.setDefaultButton(QMessageBox.Ok)
        result = dlg.exec()

        if result == QMessageBox.Ok:
            brv_file = os.path.join(self.vehicle_path, "Vehicle.brv")
            # if not os.path.exists(brv_file):
            #     return
            backup_brv_file = os.path.join(self.backup_path, "Vehicle.brv")
            if not os.path.exists(backup_brv_file):
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



def colored_icon(theme_name: str, color: QColor, size=QSize(32, 32)) -> QIcon:
    icon = QIcon.fromTheme(theme_name)
    pixmap = icon.pixmap(size)

    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()

    return QIcon(pixmap)
