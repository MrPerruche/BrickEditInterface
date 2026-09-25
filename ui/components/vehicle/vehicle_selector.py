from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QSizePolicy, QFileDialog, QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, QTimer

from ui.widgets import Widget, Surface, LineEdit, ToolButton
from ui.theme import Theme, register_has_theme_and_apply
from ui.components.vehicle.vehicle_list import (
    VehicleListModel, VehicleFilterProxy, VehicleListView, VehicleLoader
)

from utils import tint_icon, get_vehicles_path

import brickedit


class VehicleSelector(Widget):
    """Searchable list of the vehicles in the Brick Rigs vehicles folder.

    Vehicles are read by a background thread (VehicleLoader) and shown by a virtualized list
    (VehicleListView), so there is no limit on how many are listed and searching only filters what is
    already loaded. See vehicle_list.py."""

    vehicle_selected = Signal(str)

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

        # -------- LIST

        self._vehicle_model = VehicleListModel(self)
        self._filter_proxy = VehicleFilterProxy(self)
        self._filter_proxy.setSourceModel(self._vehicle_model)

        self._cache: dict = {}  # Shared with the loaders: path -> (file stamps, entry)
        self._generation = 0
        self._first_batch_pending = False
        self._loaders: set[VehicleLoader] = set()  # Every running loader, kept alive until it stops
        QApplication.instance().aboutToQuit.connect(self._shutdown_loaders)

        # -------- PREP

        placeholder = QIcon(':/assets/icons/placeholder.png')

        # -------- SEARCH / RELOAD / EXPLORE

        self.search_and_reload_layout = QHBoxLayout()
        self.master_layout.addLayout(self.search_and_reload_layout)

        self.search_box = LineEdit(placeholder="Search vehicle...")
        self.search_box.text_changed.connect(self._search_changed)
        self.search_and_reload_layout.addWidget(self.search_box)

        self.refresh_button = ToolButton(icon=placeholder)
        self.refresh_button.clicked.connect(lambda: self.request_reload(True))
        self.search_and_reload_layout.addWidget(self.refresh_button)

        self.folder_button = ToolButton(icon=placeholder)
        self.folder_button.clicked.connect(self.folder_btn_pressed)
        self.search_and_reload_layout.addWidget(self.folder_button)

        self.list_view = VehicleListView()
        self.list_view.setModel(self._filter_proxy)
        self.list_view.clicked.connect(self._card_clicked)

        # BOTTOM TEXT AND STUFF
        self.master_layout.addWidget(self.list_view)
        self.master_layout.addStretch(1)
        # Listing and reading vehicles is done off the UI thread, but still: let the window show up first.
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
        """Rescans the vehicles folder. Ignore old ignores cached results and forces re-reading every vehicle
        (and thumbnail); otherwise only vehicles whose files changed are read again."""
        self._reload(ignore_old=ignore_old)


    def _search_changed(self, *args):
        self._filter_proxy.set_query(self.search_box.get_text())


    def _reload(self, *args, ignore_old: bool = False):
        if ignore_old:
            self._cache.clear()
            self.list_view.itemDelegate().clear_thumbnails()

        self._stop_loaders()
        self._generation += 1
        # The old list stays on screen until the first new batch arrives, so a reload doesn't flicker
        self._first_batch_pending = True

        loader = VehicleLoader(self._generation, self.vehicles_path, self._cache)
        loader.batch_ready.connect(self._batch_ready)
        loader.loaded.connect(self._loading_done)
        loader.finished.connect(lambda l=loader: self._loaders.discard(l))
        self._loaders.add(loader)
        loader.start()


    def _batch_ready(self, generation: int, entries: list):
        if generation != self._generation:
            return  # From a reload that has been superseded
        if self._first_batch_pending:
            self._first_batch_pending = False
            self._vehicle_model.replace(entries)
        else:
            self._vehicle_model.append(entries)


    def _loading_done(self, generation: int):
        if generation == self._generation and self._first_batch_pending:
            self._first_batch_pending = False  # No vehicle at all
            self._vehicle_model.clear()


    def _stop_loaders(self):
        for loader in self._loaders:
            loader.cancel()

    def _shutdown_loaders(self):
        self._stop_loaders()
        for loader in list(self._loaders):
            loader.wait(3000)


    def set_accented_card(self, vehicle_path: str | None):
        self._vehicle_model.set_active_path(vehicle_path)


    def _card_clicked(self, index):
        entry = index.data(VehicleListModel.EntryRole)
        if entry is not None:
            self.vehicle_selected.emit(entry.path)


    def _apply_theme(self, theme: Theme):
        refresh_icon = QIcon.fromTheme("view-refresh")
        self.refresh_button.set_icon(tint_icon(refresh_icon, theme.text.color_hex_argb))
        folder_icon = QIcon.fromTheme("folder-open")
        self.folder_button.set_icon(tint_icon(folder_icon, theme.text.color_hex_argb))
