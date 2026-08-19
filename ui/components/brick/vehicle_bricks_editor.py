from PySide6.QtWidgets import QVBoxLayout

from ui.dialogs import CannotSaveUneditedDialog
from ui.widgets import Widget, Switcher, SwitcherEntry, Label
from ui.components.brick.grouping_methods import *
from ui.components.brick.property_set import PropertySet

from utils import wipe_layout, clamp

from collections import defaultdict

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface
    from ui.components.brick_filter.brick_selector import BrickSelector


import logging
logger = logging.getLogger(__name__)


GMS: list[BaseGM] = [
    NoGroupingGM(),
    TypeGM(),
    ClassGM(),
    EditorGroupGM(),
    WeldGroupGM(),
    MergeAllGM(),
]


class VehicleBricksEditor(Widget):

    def __init__(self,
        mw: 'BrickEditInterface',
        bs: 'BrickSelector',
        gm: BaseGM = GMS[0]
    ):
        super().__init__()
        self.mw = mw
        self.brick_selector = bs
        self.grouping_method = gm

        # self.gms_to_brick_lists[GMS i] -> list of every (page of this GM -> 1 page being a tuple of its name and bricks)
        self.gms_to_brick_lists: list[ list[tuple[str, list[brickedit.Brick]]] ] = [[] for _ in GMS]
        # self.gms_to_property_sets[GMS i] -> list of every PropertySet if saved else None
        self.gms_to_property_sets: list[ list[PropertySet | None] ] = [[] for _ in GMS]
        #
        self.current_page_indices: list[int] = [0 for _ in GMS]
        #
        self.frozen_properties = set()

        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)


        self.property_set_controls_layout = QVBoxLayout()
        self.property_set_controls_layout.setContentsMargins(0, 4, 0, 4)
        self.master_layout.addLayout(self.property_set_controls_layout)

        self.grouping_method_switcher = Switcher([SwitcherEntry(e.get_name(), e.get_tooltip()) for e in GMS])
        self.grouping_method_switcher.index_changed.connect(self.update_grouping_method)
        self.property_set_controls_layout.addWidget(self.grouping_method_switcher)

        self.page_switcher = Switcher([])
        self.page_switcher.index_changed.connect(self.update_page)
        self.property_set_controls_layout.addWidget(self.page_switcher)
        self.page_switcher.hide()

        self.no_bricks_selected = Label("No bricks selected.")
        self.master_layout.addWidget(self.no_bricks_selected)

        self.live_property_set: PropertySet | None = None
        self.property_set_container = QVBoxLayout()
        self.property_set_container.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.property_set_container)

        self.mw.vehicle_selector_banner.vehicle_loaded.connect(self.reload_vehicle)
        self.reload_vehicle()

        # self._reload()


    def reload_vehicle(self):
        self._reload()


    def get_active_gm_idx(self):
        return self.grouping_method_switcher.get_idx()


    def _clear_property_set_data(self):
        wipe_layout(self.property_set_container, delete_widgets=True)

        self.live_property_set = None
        self.gms_to_brick_lists = [[] for _ in GMS]
        self.current_page_indices = [0 for _ in GMS]

        for page_list in self.gms_to_property_sets:
            for property_set in page_list:
                if property_set is not None:
                    property_set.deleteLater()


    def _reload(self):

        self._clear_property_set_data()
        brvfile = self.mw.vehicle_selector_banner.get_brvfile_ref()

        # Get bricks or make empty
        if brvfile is None:
            return self._build_empty()

        filtered_bricks = [brick for brick in brvfile.bricks if self.brick_selector.is_allowed(brick)]
        if not filtered_bricks:
            return self._build_empty()
        self.no_bricks_selected.hide()
        self.page_switcher.show()

        # Reset GM / Page data
        self.gms_to_brick_lists = [list(gm.split(self.mw, filtered_bricks).items()) for gm in GMS]

        self.gms_to_property_sets = [
            [None for _ in self.gms_to_brick_lists[i]]
            for i in range(len(self.gms_to_brick_lists))
        ]
        # self.current_page_indices = [0 for _ in GMS]  # Done by self._clear_property_set_data
        self.frozen_properties = self.brick_selector.get_frozen_properties()

        # Build current page
        self._update_page_switcher()
        self._reload_page()



    def _reload_page(self):

        # Clear current page
        wipe_layout(self.property_set_container, delete_widgets=False)

        # Get active menu stuff
        active_gm_idx = self.grouping_method_switcher.get_idx()
        brick_lists = self.gms_to_brick_lists[active_gm_idx]
        current_page = self.current_page_indices[active_gm_idx]
        if current_page >= len(brick_lists):
            return

        # Verify a property set wasn't already made
        property_set = self.gms_to_property_sets[active_gm_idx][current_page]
        if property_set is not None:
            self.property_set_container.addWidget(property_set)
            property_set.show()
            self.live_property_set = property_set
            return

        # import time  # DEBUG
        # temp_t0 = time.perf_counter()

        # Get all properties
        name, bricks = brick_lists[current_page]
        name: str
        bricks: list[brickedit.Brick]

        frozen_properties_found = set()
        properties = defaultdict(set)

        for brick in bricks:
            brick_properties = brick.get_all_properties() | brick.ppatch

            for prop, val in brick_properties.items():
                if prop in self.frozen_properties:
                    frozen_properties_found.add(prop)
                    # continue
                if isinstance(val, bytearray):
                    val = bytes(val)
                properties[prop].add(val)


        # Make property set DEBUG
        # import cProfile, pstats, io

        # temp_t1 = time.perf_counter()
        # profiler = cProfile.Profile()
        # profiler.enable()
        property_set = PropertySet(self.brick_selector, properties, self.frozen_properties)
        # profiler.disable()
        # temp_t2 = time.perf_counter()

        # buf = io.StringIO()
        # pstats.Stats(profiler, stream=buf).sort_stats('cumulative').print_stats(20)
        # logger.info("\n" + buf.getvalue())

        # print(f"collect={temp_t1-temp_t0:.3f}s  widgets={temp_t2-temp_t1:.3f}s  n_bricks={len(bricks)} n_props={len(properties)}")

        # Keep it in memory ONLY IF if it becomes relevant -> user did a change. If there is no change then reconstructing this widget will yield the same thing so we don't have to keep it in memory
        property_set.properties_edited.connect(self.save_current_property_set)
        self.live_property_set = property_set
        

        self.property_set_container.addWidget(property_set)



    def build_modified_brvfile(self, save: bool, save_args: dict) -> brickedit.BRVFile:

        # Validation
        if self.live_property_set is None:
            logger.warning("Trying to save property set but live property set is currently None.")
            CannotSaveUneditedDialog.create().exec()
            return

        brvfile = self.mw.vehicle_selector_banner.get_brvfile_copy()

        # Get concerned brick ids
        gm_idx = self.get_active_gm_idx()
        page = self.current_page_indices[gm_idx]
        bricks: list[brickedit.Brick] = self.gms_to_brick_lists[gm_idx][page][1]
        relevant_brick_ids: set[str] = {b.ref.id for b in bricks}

        # Update brick properties on the brvfile copy
        self.live_property_set.update_bricks([brick for brick in brvfile.bricks if brick.ref.id in relevant_brick_ids])

        # Save
        if save:
            self.mw.vehicle_selector_banner.save_brv(brvfile, **save_args)

        return brvfile



    def _update_page_switcher(self):
        brick_lists = self.gms_to_brick_lists[self.get_active_gm_idx()]

        self.page_switcher.index_changed.disconnect(self.update_page)
        try:
            self.page_switcher.set_items([name for name, _ in brick_lists], 0)
            self.page_switcher.set_index(self.current_page_indices[self.get_active_gm_idx()])
        finally:
            self.page_switcher.index_changed.connect(self.update_page)

    def update_page(self):
        brick_lists = self.gms_to_brick_lists[self.get_active_gm_idx()]
        current_idx = self.page_switcher.get_idx()
        current_idx = current_idx if current_idx is not None else 0
        page = clamp(current_idx, 0, len(brick_lists) - 1)
        self.current_page_indices[self.get_active_gm_idx()] = page
        self._reload_page()


    def _build_empty(self):
        self.no_bricks_selected.show()
        self.page_switcher.hide()


    def save_current_property_set(self):
        gm_idx = self.get_active_gm_idx()
        page = self.current_page_indices[gm_idx]

        if self.live_property_set is None:
            logger.warning("Trying to save property set but live property set is currently None.")
            return
        self.gms_to_property_sets[gm_idx][page] = self.live_property_set


    # ----------

    def update_grouping_method(self):
        self.grouping_method = GMS[self.grouping_method_switcher.get_idx()]
        self._reload_page()
        self._update_page_switcher()


    def set_grouping_method(self, grouping_method: BaseGM):
        if grouping_method != self.grouping_method:
            self.grouping_method_switcher.set_index(GMS.index(grouping_method))
            self.update_grouping_method()
