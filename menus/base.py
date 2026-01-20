from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QIcon
from .widgets import LargeLabel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mainwindow import BrickEditInterface

class BaseMenu(QWidget):
    """Base class for all menu pages in the application."""

    def __init__(self, mw: "BrickEditInterface", header=True):
        super().__init__()
        self.main_window: "BrickEditInterface" = mw
        self.master_layout = QVBoxLayout(self)
        if header:
            self.header_label = LargeLabel(self.get_menu_name(), 2)
            self.master_layout.addWidget(self.header_label)
        self.setLayout(self.master_layout)

    def get_menu_name(self) -> str:
        """Return the display name of this menu."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement get_menu_name()")

    def get_icon(self) -> QIcon:
        """Return the icon for this menu."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement get_icon()")
