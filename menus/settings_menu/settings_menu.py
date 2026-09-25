from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QIcon

import os

from systems.settings import settings_manager
from menus import base
from utils import restart

from ui.widgets import Label, StyledLabel, LabelStyle, Button, Separator, Slider, ComboBox, BoolSwitch
from ui.dialogs import ConfirmRestartDialog
from ui.theme import theme_manager



UI_SCALE_SLIDER_VALUES = sorted(
    list(range(50, 100)) +
    list(range(100, 200, 2)) +
    list(range(200, 400+1, 5)) +
    [125, 175]
)

class SettingsMenu(base.BaseMenu):

    def __init__(self, mw, header=True):
        super().__init__(mw, header)

        self.dirty = False

        # UI SETTINGS
        self.ui_settings_label = StyledLabel("User Interface", LabelStyle.HEADER_3)
        self.master_layout.addWidget(self.ui_settings_label)

        # Theme
        self.theme_lay = QHBoxLayout()
        self.theme_lay.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.theme_lay)

        self.theme_label = Label("Theme")
        self.theme_lay.addWidget(self.theme_label)

        self.theme_cb = ComboBox(False)
        for theme in theme_manager.themes:
            self.theme_cb.add_item(theme.display_name)
        self.theme_cb.set_current_idx(theme_manager.current_idx())
        self.theme_cb.item_changed.connect(self.now_dirty)
        self.theme_lay.addWidget(self.theme_cb)

        # UI Scale
        self.ui_scale_lay = QHBoxLayout()
        self.ui_scale_lay.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.ui_scale_lay)

        self.ui_scale_label = Label("Scale")
        self.ui_scale_lay.addWidget(self.ui_scale_label)

        # Get highest scale in allowed scales <= scale setting
        current_scale = int(settings_manager.get("ui_scale") * 100)
        slider_scale_idx = 0
        for i, val in enumerate(UI_SCALE_SLIDER_VALUES):
            if val >= current_scale:
                slider_scale_idx = i
                break
        self.ui_scale_slider = Slider(UI_SCALE_SLIDER_VALUES, slider_scale_idx)
        self.ui_scale_slider.value_changed.connect(self.ui_scale_slider_changed)
        self.ui_scale_lay.addWidget(self.ui_scale_slider)


        # UPDATES
        self.updates_label = StyledLabel("Updates", LabelStyle.HEADER_3)
        self.master_layout.addWidget(self.updates_label)

        self.ignore_update_lay = QHBoxLayout()
        self.ignore_update_lay.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.ignore_update_lay)

        self.ignore_update_label = Label("Ignore currently available update")
        self.ignore_update_lay.addWidget(self.ignore_update_label)

        self.ignore_update_switch = BoolSwitch(False)
        self.ignore_update_switch.on_toggled.connect(self.now_dirty)
        self.ignore_update_lay.addWidget(self.ignore_update_switch)

        self.check_updates_btn = Button("Check for Updates")
        self.check_updates_btn.clicked.connect(self.mw.check_for_updates)
        self.master_layout.addWidget(self.check_updates_btn)

        # APPLY BUTTONS
        self.master_layout.addWidget(Separator())

        self.apply_layout = QHBoxLayout()
        self.apply_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.apply_layout)

        self.apply_btn = Button("Apply changes")
        self.apply_btn.clicked.connect(self.on_apply_changes_clicked)
        self.apply_layout.addWidget(self.apply_btn)

        self.reset_btn = Button("Reset all")
        self.reset_btn.clicked.connect(self.on_reset_btn_clicked)
        self.apply_layout.addWidget(self.reset_btn)

        # END OF INIT
        self.ui_scale_slider_changed()
        self.refresh_ignore_update_switch()
        self.set_dirty(False)

        self.master_layout.addStretch(1)


    def showEvent(self, event):
        super().showEvent(event)
        # The switch reflects "remind_updates_after", which can also change from the
        # update-found popup (Ignore this version) while this menu isn't visible.
        self.refresh_ignore_update_switch()


    def refresh_ignore_update_switch(self):
        if self.dirty:
            return
        known_update = self.mw.update_checker.latest_version
        self.ignore_update_switch.set_value(
            known_update is not None and settings_manager.get("remind_updates_after", "0.0.0") == known_update,
            emit_signal=False
        )
        self.ignore_update_switch.setEnabled(known_update is not None)


    def _is_restart_required(self):
        if self.ui_scale_slider.get_value() != int(settings_manager.get("ui_scale") * 100):
            return True
        return False

    def _apply_changes_internally(self):
        # Themes
        current_theme_idx = theme_manager.current_idx()
        new_theme_idx = self.theme_cb.get_current_idx()
        if current_theme_idx != new_theme_idx:
            theme_manager.set_theme(theme_manager.themes[new_theme_idx])

        # UI Scale
        new_scale = self.ui_scale_slider.get_value() / 100
        old_scale = settings_manager.get("ui_scale")
        if new_scale != old_scale:  # float != float is okay because these floats never have a reason to loose precision
            settings_manager.set("ui_scale", new_scale)
            os.environ["QT_SCALE_FACTOR"] = str(new_scale)

        # Ignore current update
        known_update = self.mw.update_checker.latest_version
        target = known_update if (self.ignore_update_switch.get_value() and known_update) else "0.0.0"
        if settings_manager.get("remind_updates_after", "0.0.0") != target:
            settings_manager.set("remind_updates_after", target)


    def _apply_changes_full(self, must_restart: bool):
        self._apply_changes_internally()
        self.set_dirty(False)
        if must_restart:
            restart()


    # ------

    def ui_scale_slider_changed(self):
        self.ui_scale_slider.set_text(f"{self.ui_scale_slider.get_value()}%", 37)
        self.now_dirty()

    # ------


    def now_dirty(self):
        self.set_dirty(True)

    def set_dirty(self, is_dirty: bool):
        self.dirty = is_dirty
        self.apply_btn.set_danger(is_dirty)
        self.apply_btn.set_disabled(not is_dirty)

    def on_apply_changes_clicked(self):

        must_restart = self._is_restart_required()

        if must_restart:
            dlg = ConfirmRestartDialog.create(self.mw, "Restart BEI?", "BrickEdit-Interface must be restarted in order to apply changes safely.")
            dlg.outcome_2_selected.connect(lambda: self._apply_changes_full(True))
            dlg.exec()
        else:
            self._apply_changes_full(False)

    def on_reset_btn_clicked(self):
        dlg = ConfirmRestartDialog.create(self.mw, "Restart BEI?", "BrickEdit-Interface must be restarted in order to reset all settings safely.")
        dlg.outcome_2_selected.connect(self.reset_and_restart_procedure)
        dlg.exec()

    def reset_and_restart_procedure(self):
        self.mw.settings.reset_all()
        restart()


    def get_menu_name(self) -> str:
        return "Settings"

    def _make_menu_info(self) -> base.MenuInfo:
        return base.MenuInfo(
            QIcon(":/assets/icons/SettingsIcon.png"), True,
            bottom_menu = True
        )
