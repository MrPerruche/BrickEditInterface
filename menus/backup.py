from . import base

from .widgets import *


class BackupMenu(base.BaseMenu):
    def __init__(self):
        super().__init__()

        self.back_recovery_header = LargeLabel("Backup Recovery", 4)
        self.master_layout.addWidget(self.back_recovery_header)

        self.master_layout.addStretch()

    def get_menu_name(self) -> str:
        return "Backup Manager"

    def get_icon_path(self) -> str:
        return ":/assets/icons/placeholder.png"
