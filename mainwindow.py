from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedLayout, QScrollArea
from PySide6.QtGui import QIcon

from sidebar import Sidebar
from menus import *
from settings_manager import SettingsManager


class BrickEditInterface(QMainWindow):
    """Main application window for the BrickEdit interface."""
    
    def __init__(self):
        super().__init__()
        
        self.resize(360, 720)
        self.setMinimumWidth(360)
        self.setWindowTitle("BrickEdit Interface")

        self.settings = SettingsManager()

        # Initialize menus
        self.menus = [
            HomeMenu(self),
            SettingsAndBackupsMenu(self),
            EditBrickMenu(self),
            VehicleUpscalerMenu(self),
        ]
        
        # Build menu configurations for sidebar
        menu_configs = [
            {
                'name': menu.get_menu_name(),
                'icon': menu.get_icon(),
            }
            for menu in self.menus
        ]

        # Set up central widget and layout
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create and connect sidebar
        self.sidebar = Sidebar(menu_configs=menu_configs)
        layout.addWidget(self.sidebar)

        # Create menu stack
        self.menu_stack = QStackedLayout()
        layout.addLayout(self.menu_stack)

        # Add menus to stack
        for menu in self.menus:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setFrameShape(QScrollArea.NoFrame)

            scroll.setWidget(menu)
            self.menu_stack.addWidget(scroll)

        # Connect sidebar menu changes to stack
        self.sidebar.menu_changed.connect(self.menu_stack.setCurrentIndex)
