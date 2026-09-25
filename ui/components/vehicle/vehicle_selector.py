from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QScrollArea, QSizePolicy, QFileDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, QTimer

import os
from enum import Enum

from ui.components import VehicleCard, VehicleCardData
from ui.widgets import Widget, Surface, LineEdit, ToolButton, ContentSizedScrollArea
from ui.theme import Theme, register_has_theme_and_apply

from utils import tint_icon, get_vehicles_path

import brickedit


class VehicleCardCreationFail(Enum):
    TOO_MANY = 0
    INCOMPATIBLE = 1
    ERROR_OCCURED = 2


class VehicleSelector(Widget):

    vehicle_selected = Signal(str)

    vehicles_loaded = 25

    brm_load_name_profile = brickedit.BRMDeserializationConfig(
        name=True
    )

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.true_master_layout = QVBoxLayout()
        self.true_master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.true_master_layout)
        self.surface = Surface(highlight=False)
        self.surface.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.true_master_layout.addWidget(self.surface)
        self.master_layout = self.surface.layout()

        self.vehicles_path = get_vehicles_path()

        self.vehicle_cards: list[VehicleCard] = []

        # -------- PREP

        placeholder = QIcon(':/assets/icons/placeholder.png')

        # -------- SEARCH / RELOAD / EXPLORE

        self.search_and_reload_layout = QHBoxLayout()
        self.master_layout.addLayout(self.search_and_reload_layout)

        self.search_box = LineEdit(placeholder="Search vehicle...")
        self.search_box.text_changed.connect(self.request_reload)
        self.search_and_reload_layout.addWidget(self.search_box)
        self.is_reloading = False
        self.pending_reload = False

        self.refresh_button = ToolButton(icon=placeholder)
        self.refresh_button.clicked.connect(lambda: self.request_reload(True))
        self.search_and_reload_layout.addWidget(self.refresh_button)

        self.folder_button = ToolButton(icon=placeholder)
        self.folder_button.clicked.connect(self.folder_btn_pressed)
        self.search_and_reload_layout.addWidget(self.folder_button)

        self.scroll_area = ContentSizedScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.viewport().setAttribute(Qt.WA_TranslucentBackground)
        self.scroll_area.viewport().setStyleSheet("background: transparent;")

        # BOTTOM TEXT AND STUFF
        self.master_layout.addWidget(self.scroll_area)
        self.master_layout.addStretch(1)
        # Scanning vehicles + building cards is slow: let the window show up first.
        QTimer.singleShot(100, self, self._reload)
        register_has_theme_and_apply(self)

    
    def folder_btn_pressed(self):
        default_path = get_vehicles_path()

        dialog = QFileDialog(self, caption="Select Vehicle", directory=default_path)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setDirectory(default_path)  # FORCE directory

        if dialog.exec():
            folder_path = dialog.selectedFiles()[0]
            self.vehicle_selected.emit(folder_path)


    def request_reload(self, *args, ignore_old: bool = False):
        """Ignore old ignores cached results and forces a reload"""
        if self.is_reloading:
            self.pending_reload = True
            if not self.is_reloading:  # Additional check just in case reloadin is done between check and request
                self._reload(ignore_old=ignore_old)
                self.pending_reload = False
        else:
            self._reload(ignore_old=ignore_old)


    def _reload(self, *args, ignore_old: bool = False):
        self.setUpdatesEnabled(False)
        try:
            self.is_reloading = True
            container = Widget()
            self.vehicle_cards_layout = QVBoxLayout(container)
            self.vehicle_cards_layout.setContentsMargins(0, 0, 0, 0)

            self.vehicle_cards.clear()

            filter: str = self.search_box.get_text()
            if filter:
                filter = filter.lower().strip()

            # get all post 1.0 vehicles
            entries = sorted(
                os.scandir(self.vehicles_path),
                key=lambda e: e.stat().st_mtime,
                reverse=True,
            )
            path_list = [os.path.join(self.vehicles_path, e.name) for e in entries if e.is_dir()]

            to_be_loaded_remaining = self.vehicles_loaded  # Creating widgets is super slow
            too_old = 0
            errors = 0
            too_many = 0

            # Add vehicle cards
            for path in path_list:

                # Get first byte of vehicle
                version = brickedit.FILE_MAIN_VERSION
                vehicle_path = os.path.join(path, "Vehicle.brv")
                if os.path.exists(vehicle_path):
                    with open(vehicle_path, "rb") as f:  # slightly cursed
                        version = int.from_bytes(f.read(1), "little")

                # Is vehicle valid checks?
                if version < brickedit.FILE_MIN_SUPPORTED_VERSION:
                    too_old += 1
                    continue
                if to_be_loaded_remaining <= 0:
                    too_many += 1
                    continue
                metadata_path = os.path.join(path, "MetaData.brm")  # Make sure theres metadata
                if not os.path.exists(metadata_path):
                    errors += 1
                    continue

                vehicle_card_data, e = VehicleCardData.load_path_silent(path)
                if e is not None:  # Exception occured, cannot be loaded
                    errors += 1
                    continue

                # Apply search filter
                if filter and (name if (name := vehicle_card_data.name.lower().strip()) else 'unnamed').find(filter) == -1:
                    continue

                # Build vehicle card
                vehicle_card = VehicleCard(path, False, vehicle_card_data=vehicle_card_data)
                vehicle_card.clicked.connect(self.on_vehicle_clicked)
                self.vehicle_cards.append(vehicle_card)
                self.vehicle_cards_layout.addWidget(vehicle_card)

                to_be_loaded_remaining -= 1

            # temp import
            # from PySide6.QtWidgets import QLayout, QApplication

            self.vehicle_cards_layout.setAlignment(Qt.AlignTop)
            # self.vehicle_cards_layout.setSizeConstraint(QLayout.SetMinimumSize)
            self.scroll_area.updateGeometry()
            self.scroll_area.setWidget(container)  # Show changes and delete old list

        finally:
            self.setUpdatesEnabled(True)

        # if another reload request has been submitted while busy reloading, reload again
        self.is_reloading = False
        if self.pending_reload:
            self.pending_reload = False
            self._reload(ignore_old=ignore_old)


    def set_accented_card(self, vehicle_path: str | None):
        for card in self.vehicle_cards:
            if card.vehicle_path == vehicle_path:
                card.set_active(True)
            elif card.is_active:
                card.set_active(False)


    def on_vehicle_clicked(self, path: str):
        self.vehicle_selected.emit(path)


    def _apply_theme(self, theme: Theme):
        self.setStyleSheet(f"""
            QWidget {{
                // background-color: #40ff0000;
            }}
        """)
        refresh_icon = QIcon.fromTheme("view-refresh")
        self.refresh_button.set_icon(tint_icon(refresh_icon, theme.text.color_hex_argb))
        folder_icon = QIcon.fromTheme("folder-open")
        self.folder_button.set_icon(tint_icon(folder_icon, theme.text.color_hex_argb))
