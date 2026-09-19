from PySide6.QtGui import QIcon

from menus import base
from utils import restart

from ui.widgets import Button
from ui.dialogs import ConfirmRestartDialog



class SettingsMenu(base.BaseMenu):

    def __init__(self, mw, header=True):
        super().__init__(mw, header)


        self.reset_btn = Button("Reset all settings")
        self.reset_btn.clicked.connect(self.on_reset_btn_clicked)
        self.master_layout.addWidget(self.reset_btn)

        self.master_layout.addStretch(1)



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
