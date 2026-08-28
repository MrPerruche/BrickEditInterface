from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QToolButton, QSizePolicy
)
from PySide6.QtGui import QIcon

from menus.base import MenuInfo
from ui.theme import Theme, register_has_theme_and_apply
from utils import tint_icon


class Sidebar(QWidget):
    """Sidebar navigation for menu selection."""
    
    menu_changed = Signal(int)

    def __init__(self, menu_configs):
        """
        Initialize the sidebar with menu buttons.
        
        Args:
            menu_configs: List of dicts with 'name' and 'icon_path' keys.
        """
        super().__init__()
        
        # Default menu configurations if none provided

        self.setFixedWidth(50)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setObjectName("menuScroll")

        self.container = QWidget()
        self.container.setObjectName("sidebarContainer")
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(6, 6, 0, 0)
        layout.setSpacing(6)
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.container.setAttribute(Qt.WA_StyledBackground, True)

        self.buttons = []
        self.menu_configs = menu_configs

        for index, config in enumerate(menu_configs):
            btn = QToolButton()
            btn.setToolTip(config.get('name', f'Menu {index}'))
            menu_icon_info = config.get('icon_info', MenuInfo(QIcon(':/assets/icons/placeholder.png'), True))
            btn.setIcon(menu_icon_info.qicon)
            btn.setIconSize(QSize(24, 24))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setFixedSize(40, 40)

            btn.clicked.connect(
                lambda checked, i=index: self.menu_changed.emit(i)
            )

            self.buttons.append(btn)
            layout.addWidget(btn)

        if self.buttons:
            self.buttons[0].setChecked(True)

        layout.addStretch()
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

        register_has_theme_and_apply(self)


    def _apply_theme(self, theme: Theme) -> None:
        # Update styles
        self.setStyleSheet(f"""
            Sidebar {{
                background-color: {theme.sidebar.color};
            }}

            QWidget#sidebarContainer {{
                background-color: {theme.sidebar.color};
            }}

            QScrollArea#menuScroll {{
                background-color: {theme.sidebar.color};
                border: none;
            }}

            QToolButton {{
                border-radius: 6px;
                background-color: transparent;
                color: {theme.sidebar.color};
            }}

            QToolButton:hover {{
                background-color: {theme.surface.color_double};
            }}

            QToolButton:checked {{
                background-color: {theme.accent.color};
            }}
        """)

        # Update QIcons
        icon_col = theme.text.color_hex_argb
        for btn, menu_cfg in zip(self.buttons, self.menu_configs):
            og_icon_info = menu_cfg['icon_info']
            if not og_icon_info.can_be_colored:
                continue
            btn.setIcon(tint_icon(og_icon_info.qicon, icon_col))
