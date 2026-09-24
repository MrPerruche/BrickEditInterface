from PySide6.QtWidgets import QHBoxLayout

from ui.dialogs import BooleanOutcomeDialog
from ui.widgets import Widget, Label, BoolSwitch

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class UpdateFoundDialog(BooleanOutcomeDialog):

    TEXT = """\
A new version of BrickEdit-Interface is available: Version {0} → {1}.
We heavily recommend you keep this app up to date. Do not reports bug on outdated versions.
Open the download page?"""


    def __init__(self, mw, icon, title, text, outcome_1_text, outcome_2_text,
                 future_version, parent=None, default_outcome: int | None = None):
        super().__init__(mw, icon, title, text, outcome_1_text, outcome_2_text, parent, default_outcome)

        self.future_version = future_version

        self.mw.settings.register("remind_updates_after", "0.0.0")

        self.remind_me_widget = Widget()
        self.remind_me_layout = QHBoxLayout()
        self.remind_me_layout.setContentsMargins(0, 0, 0, 0)
        self.remind_me_widget.setLayout(self.remind_me_layout)
        
        self.remind_me_label = Label("Do not remind me until a new update releases")
        self.remind_me_layout.addWidget(self.remind_me_label)

        self.remind_me_switch = BoolSwitch(self.mw.settings.get("remind_updates_after") != "0.0.0")
        self.remind_me_switch.on_toggled.connect(self.toggle)
        self.remind_me_layout.addWidget(self.remind_me_switch)

        self._add_content(self.remind_me_widget)


    @staticmethod
    def create(mw: 'BrickEditInterface', current_version, future_version):

        return UpdateFoundDialog(
            mw=mw,
            icon=UpdateFoundDialog.INFO_ICON(),
            title="Update Available",
            text=str.format(UpdateFoundDialog.TEXT, current_version, future_version),
            outcome_1_text="Maybe later",
            outcome_2_text="Download now",
            future_version=future_version,
            default_outcome=1,
        )


    def toggle(self):
        self.mw.settings.set("remind_updates_after",
            self.future_version if self.remind_me_switch.get_value() else "0.0.0"
        )
