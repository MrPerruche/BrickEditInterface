from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedLayout, QScrollArea

from packaging.version import Version

from systems.settings import settings_manager
from systems.backup import BackupSystem
from systems.update import UpdateChecker

from ui.theme import Theme, register_has_theme_and_apply
from ui.components import VehicleSelectionDrawer
from ui.dialogs import UpdateFoundDialog, UpToDateDialog, UpdateCheckFailedDialog

from sidebar import Sidebar
from menus import *
from var import VERSION_NUMBER, IS_PRIVATE_VERSION

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
        self.settings.load()
        self.backups = BackupSystem(self)
        self.update_checker = UpdateChecker(
            "MrPerruche", "BrickEditInterface", VERSION_NUMBER  # Early access crashes if VERSION
        )

        # Start systems
        self.update_checker.update_available.connect(self.maybe_report_new_update)
        self.update_checker.start()

        # Set up central widget and layout
        central = QWidget()
        central.setObjectName("appCentral")
        central.setAutoFillBackground(True)  # Background is a palette color, not a stylesheet (repolishes the whole tree)
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
            ImageImporter(self),
            SettingsMenu(self),
        ]
        self.in_dev_menus = [
            DeveloperTestMenu(self),
        ]
        if IS_PRIVATE_VERSION:
            self.menus.extend(self.in_dev_menus)
        
        # Build menu configurations for sidebar
        menu_configs = [
            {
                'name': menu.get_menu_name(),
                'icon_info': menu.get_menu_info(),
                'bottom': False,
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
            scroll.setStyleSheet("QScrollArea { border: none; }")  # Theme independent: set once

            scroll.setWidget(menu)
            self.menu_stack.addWidget(scroll)

        # Connect sidebar menu changes to stack
        self.sidebar.menu_changed.connect(self.menu_stack.setCurrentIndex)

        register_has_theme_and_apply(self)

    def _apply_theme(self, theme: Theme) -> None:
        # Tooltips are styled through the *hovered widget's* ancestors, so this has to live on the window
        #  (app-level is ~4x slower to re-apply, central-level would skip dialogs). It is the priciest
        #  remaining part of a theme change since it re-polishes every widget.
        self.setStyleSheet(f"""
            QToolTip {{
                background-color: {theme.background.color};
                color: {theme.text.color};

                border: 2px solid {theme.border.color};
                border-radius: 4px;

                font-size: 13pt;
            }}""")

        # Palettes, not stylesheets: a stylesheet on an ancestor re-polishes every descendant.
        #  Must come AFTER the setStyleSheet above: re-polishing restores widgets' previous palette.
        pal = self.centralWidget().palette()
        pal.setColor(QPalette.ColorRole.Window, theme.background.color_qcolor)
        self.centralWidget().setPalette(pal)


    def maybe_report_new_update(self, new_version: str):

        remind_updates_after = Version(self.settings.get("remind_updates_after", "0.0.0"))
        if Version(new_version) <= remind_updates_after:
            return

        dlg = UpdateFoundDialog.create(self, VERSION_NUMBER, new_version)
        dlg.outcome_3_selected.connect(self.update_checker.open_download_page)
        dlg.exec()

    def check_for_updates(self):
        """Manually check for updates, always showing a result popup (found/up to date/failed)."""
        if getattr(self, "_manual_update_checker", None) is not None and self._manual_update_checker.isRunning():
            return

        checker = UpdateChecker("MrPerruche", "BrickEditInterface", VERSION_NUMBER)
        self._manual_update_checker = checker

        def on_finished():
            if checker.error_reason is not None:
                UpdateCheckFailedDialog.create(self, checker.error_reason).exec()
            elif checker.has_known_update():
                dlg = UpdateFoundDialog.create(self, VERSION_NUMBER, checker.latest_version)
                dlg.outcome_3_selected.connect(checker.open_download_page)
                dlg.exec()
            else:
                UpToDateDialog.create(self).exec()

        checker.finished.connect(on_finished)
        checker.start()
