from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ui.widgets import StyledLabel, LabelStyle, ToolButton
from ui.theme import Theme, register_has_theme_and_apply
from ui.components.tutorial import Tutorial

if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


@dataclass(frozen=True)
class MenuInfo:
    qicon: QIcon
    can_be_colored: bool
    tutorial: Tutorial | None = None




class BaseMenu(QWidget):
    """Base class for all menu pages in the application."""


    _INFORMATION_ICON = None
    _TUTORIAL_BTN_SIZE = (32, 32)


    def __init__(self, mw: "BrickEditInterface", header=True):
        super().__init__()

        if BaseMenu._INFORMATION_ICON is None:
            BaseMenu._INFORMATION_ICON = QIcon(":/assets/icons/Information.png")

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.main_window: "BrickEditInterface" = mw
        self.mw: "BrickEditInterface" = mw  # Alias for convenience
        self.menu_info = None
        self.master_layout = QVBoxLayout(self)

        # HEADER:
        if header:
            # HEADER
            self.header_layout = QHBoxLayout()
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.master_layout.addLayout(self.header_layout)

            self.header_label = StyledLabel(self.get_menu_name(), LabelStyle.HEADER_2, margins_mult=0)
            self.header_layout.addWidget(self.header_label)

            # TUTORIAL BUTTON
            menu_info = self.get_menu_info()
            if menu_info.tutorial:
                self.header_layout.addStretch()
                self.tutorial_button = ToolButton(BaseMenu._INFORMATION_ICON, True)
                self.tutorial_button.setFixedSize(*BaseMenu._TUTORIAL_BTN_SIZE)
                self.tutorial_button.clicked.connect(menu_info.tutorial.summon)
                self.header_layout.addWidget(self.tutorial_button)

        # END DEFINITION
        self.setLayout(self.master_layout)
        register_has_theme_and_apply(self)


    def _apply_theme(self, theme: Theme) -> None:
        self.setStyleSheet(f"BaseMenu {{ background-color: {theme.background.color}; }}")

    def get_menu_name(self) -> str:
        """Return the display name of this menu."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement get_menu_name()")

    def get_menu_info(self) -> MenuInfo:
        if self.menu_info is None:
            self.menu_info = self._make_menu_info()
        return self.menu_info

    def _make_menu_info(self) -> MenuInfo:
        """Return the icon for this menu."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement _make_menu_info()")
