from ui.dialogs.base import TernaryOutcomeDialog, BasicInfoDialog

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class UpdateFoundDialog(TernaryOutcomeDialog):

    TEXT = """\
A new version of BrickEdit-Interface is available: Version {0} → {1}.
We heavily recommend you keep this app up to date.
Do not reports bug on outdated versions."""


    def __init__(self, mw, icon, title, text, outcome_1_text, outcome_2_text, outcome_3_text,
                 future_version, parent=None, default_outcome: int | None = None):
        super().__init__(mw, icon, title, text, outcome_1_text, outcome_2_text, outcome_3_text, parent, default_outcome)

        self.future_version = future_version

        self.mw.settings.register("remind_updates_after", "0.0.0")

        self.outcome_2_selected.connect(self.ignore_this_version)


    @staticmethod
    def create(mw: 'BrickEditInterface', current_version, future_version):

        return UpdateFoundDialog(
            mw=mw,
            icon=UpdateFoundDialog.INFO_ICON(),
            title="Update Available",
            text=str.format(UpdateFoundDialog.TEXT, current_version, future_version),
            outcome_1_text="Maybe later",
            outcome_2_text="Ignore this update",
            outcome_3_text="See changelogs or download",
            future_version=future_version,
            default_outcome=1,
        )


    def ignore_this_version(self):
        self.mw.settings.set("remind_updates_after", self.future_version)


class UpToDateDialog(BasicInfoDialog):

    @staticmethod
    def create(mw: 'BrickEditInterface'):
        return UpToDateDialog(
            mw=mw,
            icon=UpToDateDialog.INFO_ICON(),
            title="Up to Date",
            text="BrickEdit-Interface is up to date."
        )


class UpdateCheckFailedDialog(BasicInfoDialog):

    @staticmethod
    def create(mw: 'BrickEditInterface', reason: str):
        return UpdateCheckFailedDialog(
            mw=mw,
            icon=UpdateCheckFailedDialog.WARNING_ICON(),
            title="Update Check Failed",
            text=f"Could not check for updates:\n{reason}"
        )
