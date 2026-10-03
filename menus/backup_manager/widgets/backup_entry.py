from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from os import path
import subprocess
import sys

from systems.backup import BackupInfo, MetadataState

from ui.widgets import Surface, SurfaceStyle, Label, ToolButton
from ui.theme import Theme, register_has_theme_and_apply
from ui.models import TooltipContents

from utils import tint_icon

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

NO_METADATA_TOOLTIP = TooltipContents(
    "No metadata found",
    "BrickEdit-Interface saves the date and description of its backups in a separate metadata file.\n"
    "The Steam Cloud only saves .brv files: this file is lost when a vehicle is transferred using it.\n"
    "Backups made by older versions of BrickEdit-Interface don't have one either."
)
UNREADABLE_METADATA_TOOLTIP = TooltipContents(
    "Unreadable metadata",
    "The metadata file of this backup, which stores its date and description, is corrupt or was modified.\n"
    "The backup itself may still be fine."
)
BRICK_RIGS_TOOLTIP = TooltipContents(
    "Brick Rigs backup",
    "Backup.brv is made by Brick Rigs to avoid losing the vehicle if its main file gets corrupted.\n"
    "Autosave.brv is often made when you exit without saving.\n"
    "Brick Rigs keeps at most one of each, and may overwrite them at any time."
)


def describe_backup(main_window: "BrickEditInterface", backup: BackupInfo) -> str:
    """Short, single line description of a backup for dialogs. Never includes user-editable text."""
    if backup.is_brick_rigs:
        text = path.basename(backup.path)
    else:
        text = f"{main_window.backups.get_backup_name(backup.kind)} backup"
    if backup.time is not None:
        text += f" from {backup.time.astimezone().strftime('%Y-%m-%d %H:%M:%S')}"
    return text


class BackupEntry(Surface):
    def __init__(self, mw: "BrickEditInterface", backup: BackupInfo,
        on_recover: Callable[[BackupInfo], None],
        on_delete: Callable[[BackupInfo, bool], None],
        parent=None
    ):
        super().__init__(parent=parent)  # Not positional: Surface's first parameter is surface_style

        self.master_layout = self.layout()

        self.main_window = mw

        self.backup = backup
        self.on_recover = on_recover
        self.on_delete = on_delete

        # Prepare variables
        if backup.is_brick_rigs:
            backup_type = f"{mw.backups.get_backup_name(backup.kind)} backup ({path.basename(backup.path)})"
        else:
            backup_type = f"{mw.backups.get_backup_name(backup.kind)} backup"

        if backup.time is not None:
            backup_dt_text = backup.time.astimezone().strftime('%y-%m-%d\n%H:%M:%S')  # Shown in local time
        else:
            backup_dt_text = "Unknown date"

        if backup.kind == "ug":
            self.set_surface_style(SurfaceStyle.ACCENT)

        # DATE AND BUTTONS
        # Layout
        self.info_and_buttons_layout = QHBoxLayout()
        self.master_layout.addLayout(self.info_and_buttons_layout)

        # dt
        self.info_layout = QVBoxLayout()
        self.dt_text_label = Label(backup_dt_text, font_weight=1000, muted=backup.time is None)
        self.info_layout.addWidget(self.dt_text_label)
        self.info_and_buttons_layout.addLayout(self.info_layout, stretch=1)

        # Buttons layout
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.info_and_buttons_layout.addLayout(self.buttons_layout)

        # Open directory button
        self.open_dir_button = ToolButton(icon=OPEN_DIR_BTN_ICON, tint_icon=True)
        self.open_dir_button.set_tooltip(TooltipContents("Open backup directory"))
        self.open_dir_button.clicked.connect(self.open_dir_btn)
        self.buttons_layout.addWidget(self.open_dir_button)

        # Recover backup button
        self.recover_button = ToolButton(icon=RECOVER_BTN_ICON, tint_icon=True)
        if path.isfile(backup.brv_path):
            self.recover_button.set_tooltip(TooltipContents("Recover backup"))
        else:
            self.recover_button.set_tooltip(TooltipContents("Cannot recover", "This backup has no Vehicle.brv."))
            self.recover_button.set_enabled(False)
        self.recover_button.clicked.connect(lambda: self.on_recover(self.backup))
        self.buttons_layout.addWidget(self.recover_button)

        # Send to trash bin button
        self.bin_button = ToolButton(icon=BIN_BTN_ICON, tint_icon=True)
        self.bin_button.set_tooltip(TooltipContents("Send to recycle bin"))
        self.bin_button.clicked.connect(lambda: self.on_delete(self.backup, True))
        self.buttons_layout.addWidget(self.bin_button)

        # Delete button
        self.delete_button = ToolButton(icon=DELETE_BTN_ICON, tint_icon=False)
        self.delete_button.set_tooltip(TooltipContents("Delete permanently"))
        self.delete_button.clicked.connect(lambda: self.on_delete(self.backup, False))
        self.buttons_layout.addWidget(self.delete_button)


        # THE REST
        self.backup_type_label = Label(backup_type)
        self.master_layout.addWidget(self.backup_type_label)

        self.backup_desc_label = Label()
        # Descriptions can be edited by the user: never interpret them as rich text
        self.backup_desc_label.qt_widget.setTextFormat(Qt.TextFormat.PlainText)
        match backup.metadata:
            case MetadataState.NOT_APPLICABLE:
                self.backup_desc_label.set_text("Managed by Brick Rigs.")
                self.backup_desc_label.set_muted(True)
                self.backup_desc_label.set_tooltip(BRICK_RIGS_TOOLTIP)
            case MetadataState.MISSING:
                self.backup_desc_label.set_text("No metadata found")
                self.backup_desc_label.set_muted(True)
                self.backup_desc_label.set_tooltip(NO_METADATA_TOOLTIP)
            case MetadataState.UNREADABLE:
                self.backup_desc_label.set_text("Unreadable metadata")
                self.backup_desc_label.set_muted(True)
                self.backup_desc_label.set_tooltip(UNREADABLE_METADATA_TOOLTIP)
            case _:
                if backup.description is None:
                    self.backup_desc_label.set_text("No description provided.")
                    self.backup_desc_label.set_muted(True)
                else:
                    self.backup_desc_label.set_text(backup.description)
        self.master_layout.addWidget(self.backup_desc_label)


        register_has_theme_and_apply(self)


    def open_dir_btn(self):
        # Opening a .brv file directly would launch whatever program is associated with it: open its folder
        open_path(path.dirname(self.backup.path) if self.backup.is_file else self.backup.path)


    def _apply_theme(self, theme: Theme):

        if hasattr(self, "delete_button"):
            self.delete_button.set_icon(
                tint_icon(DELETE_BTN_ICON, theme.danger.color_hex_argb)
            )
