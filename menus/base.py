from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ui.widgets import StyledLabel, LabelStyle
from ui.theme import Theme, register_has_theme_and_apply

if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


@dataclass(frozen=True)
class MenuIconInfo:
    qicon: QIcon
    can_be_colored: bool

class BaseMenu(QWidget):
    """Base class for all menu pages in the application."""

    def __init__(self, mw: "BrickEditInterface", header=True):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.main_window: "BrickEditInterface" = mw
        self.mw: "BrickEditInterface" = mw  # Alias for convenience
        self.master_layout = QVBoxLayout(self)
        if header:
            self.header_label = StyledLabel(self.get_menu_name(), LabelStyle.HEADER_2, margins_mult=0)
            self.master_layout.addWidget(self.header_label)
        self.setLayout(self.master_layout)

        register_has_theme_and_apply(self)

    def _apply_theme(self, theme: Theme) -> None:
        self.setStyleSheet(f"BaseMenu {{ background-color: {theme.background.color}; }}")

    def get_menu_name(self) -> str:
        """Return the display name of this menu."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement get_menu_name()")

    def get_icon(self) -> MenuIconInfo:
        """Return the icon for this menu."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement get_icon()")
