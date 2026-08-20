from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedLayout, QScrollArea, QMessageBox

from sidebar import Sidebar
from menus import *
from utils import VERSION, DEV_VERSION
from systems.settings import settings_manager
from systems.backup import BackupSystem
from systems.update import UpdateChecker
from ui.theme import Theme, register_has_theme_and_apply
from ui.components import VehicleSelectionDrawer

class BrickEditInterface(QMainWindow):
    """Main application window for the BrickEdit interface."""
    
    def __init__(self):
        super().__init__()
        
        # Edit the window
        self.resize(360, 720)
        self.setMinimumWidth(360)
        self.setWindowTitle("BrickEdit Interface")

        # Systems
        self.settings = settings_manager
        self.backups = BackupSystem(self)
        self.update_checker = UpdateChecker(
            "MrPerruche", "BrickEditInterface", VERSION
        )

        # Start systems
        self.update_checker.update_available.connect(self.report_new_update)
        self.update_checker.start()

        # Set up central widget and layout
        central = QWidget()
        central.setObjectName("appCentral")
        central.setAttribute(Qt.WA_StyledBackground, True)
        self.setCentralWidget(central)

        master_layout = QVBoxLayout(central)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)
        self.vehicle_selector_banner = VehicleSelectionDrawer(self)
        master_layout.addWidget(self.vehicle_selector_banner)

        layout = QHBoxLayout()
        master_layout.addLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Initialize menus
        self.menus: list[BaseMenu] = [
            HomeMenu(self),
            SettingsAndBackupsMenu(self),
            EditBrickMenu(self),
            GradientMaker(self),
            VehicleUpscalerMenu(self),
            DowngradeVehicleMenu(self),
        ]
        self.in_dev_menus = [
            ImageImporter(self),
            DeveloperTestMenu(self),
        ]
        if DEV_VERSION:
            self.menus.extend(self.in_dev_menus)
        
        # Build menu configurations for sidebar
        menu_configs = [
            {
                'name': menu.get_menu_name(),
                'icon_info': menu.get_icon()
            }
            for menu in self.menus
        ]

        # Create and connect sidebar
        self.sidebar = Sidebar(menu_configs=menu_configs)
        layout.addWidget(self.sidebar)

        # Create menu stack
        self.menu_stack = QStackedLayout()
        layout.addLayout(self.menu_stack)

        # Add menus to stack
        for menu in self.menus:
            scroll = QScrollArea()
            scroll.setObjectName("menuContentScroll")
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setFrameShape(QScrollArea.NoFrame)

            scroll.setWidget(menu)
            self.menu_stack.addWidget(scroll)

        # Connect sidebar menu changes to stack
        self.sidebar.menu_changed.connect(self.menu_stack.setCurrentIndex)

        register_has_theme_and_apply(self)

    def _apply_theme(self, theme: Theme) -> None:
        self.centralWidget().setStyleSheet(f"""
            QWidget#appCentral {{
                background-color: {theme.background.color};
            }}
        """)

        for i in range(self.menu_stack.count()):
            scroll = self.menu_stack.widget(i)
            if isinstance(scroll, QScrollArea):
                scroll.setStyleSheet("QScrollArea { border: none; }")

        self.setStyleSheet(f"""
            QToolTip {{
                background-color: {theme.background.color};
                color: {theme.text.color};

                border: 2px solid {theme.border.color};
                border-radius: 4px;

                font-size: 13pt;
            }}""")
        

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
