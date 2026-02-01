from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedLayout, QScrollArea, QMessageBox

from sidebar import Sidebar
from menus import *
from utils import VERSION, DEV_VERSION
from settings_manager import SettingsManager
from backup_system import BackupSystem
from update_checker import UpdateChecker


class BrickEditInterface(QMainWindow):
    """Main application window for the BrickEdit interface."""
    
    def __init__(self):
        super().__init__()
        
        # Edit the window
        self.resize(360, 720)
        self.setMinimumWidth(360)
        self.setWindowTitle("BrickEdit Interface")

        # Systems
        self.settings = SettingsManager()
        self.backups = BackupSystem(self)
        self.update_checker = UpdateChecker(
            "MrPerruche", "BrickEditInterface", VERSION
        )

        # Start systems
        self.update_checker.update_available.connect(self.report_new_update)
        self.update_checker.start()

        # Initialize menus
        self.menus = [
            HomeMenu(self),
            SettingsAndBackupsMenu(self),
            EditBrickMenu(self),
            GradientMaker(self),
            VehicleUpscalerMenu(self),
        ]
        self.in_dev_menus = [
        ]
        if DEV_VERSION:
            self.menus.extend(self.in_dev_menus)
        
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

    def report_new_update(self, version: str):
        dlg = QMessageBox()
        dlg.setWindowTitle("New version available")
        dlg.setText(f"""\
A new version of BrickEdit-Interface is available: Version {VERSION} → {version}.
We heavily recommend you keep this app up to date. Do not reports bug on outdated versions.""")
        dlg.setInformativeText("Open the download page?")
        dlg.setIcon(QMessageBox.Information)
        dlg.setModal(False)

        ok_button = dlg.addButton("Download", QMessageBox.AcceptRole)
        dlg.addButton(QMessageBox.Cancel)
        dlg.setDefaultButton(QMessageBox.Cancel)
        
        # Show (non blocking)
        ok_button.clicked.connect(self.update_checker.open_download_page)
        dlg.show()
        self._update_dlg = dlg  # Keep a ref
