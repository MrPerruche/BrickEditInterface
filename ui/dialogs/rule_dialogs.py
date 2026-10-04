"""Dialogs of the rule based editor"""

import html

from ui.widgets import Label, LineEdit, MultilineEdit, Button
from ui.dialogs.base import Dialog, BooleanOutcomeDialog, BasicInfoDialog


class ConfirmActionsDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, outcomes: list[str]):
        """outcomes: what each action does, eg. "1. Delete: Deleted 12 bricks." """
        lines = "<br>".join(html.escape(outcome) for outcome in outcomes)
        return ConfirmActionsDialog(
            mw=mw,
            icon=ConfirmActionsDialog.WARNING_ICON(),
            title="Apply Actions?" if len(outcomes) > 1 else "Apply Action?",
            text=f"<html><b>Some bricks will be removed. Save these changes?</b><br>{lines}<br><br>"
                 "A backup of the vehicle is made before saving.</html>",
            outcome_1_text="Save",
            outcome_2_text="Cancel",
            default_outcome=2,
        )


class NoBricksMatchDialog(BasicInfoDialog):

    @staticmethod
    def create(mw):
        return NoBricksMatchDialog(
            mw=mw,
            icon=NoBricksMatchDialog.INFO_ICON(),
            title="No Bricks Selected",
            text="No brick matches the conditions. Nothing was changed."
        )


class CannotApplyActionDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, reason: str):
        return CannotApplyActionDialog(
            mw=mw,
            icon=CannotApplyActionDialog.WARNING_ICON(),
            title="Cannot Apply Action",
            text=f"{reason}\nNothing was saved."
        )


# ----- Presets


class SavePresetDialog(Dialog):
    """Asks for the name and description of a new preset. exec() returns (name, description), or None."""

    def __init__(self, mw, name: str, description: str, warnings: list[str], max_name_length: int,
                 max_description_length: int, parent=None):
        super().__init__(mw, None, "Save Preset", parent)

        self._add_content(Label("Name"))
        self.name_le = LineEdit(name)
        self.name_le.set_max_length(max_name_length)
        self._add_content(self.name_le)

        self._add_content(Label("Description (optional)"))
        self.description_le = MultilineEdit(description)
        self.description_le.set_max_length(max_description_length)
        self._add_content(self.description_le)

        for warning in warnings:
            self._add_content(Label(warning, muted=True))

        self.save_button = Button("Save")
        self.save_button.clicked.connect(self._save)
        self._add_action(self.save_button, auto_close=False, default=True)
        self.cancel_button = Button("Cancel")
        self._add_action(self.cancel_button)

        self.name_le.text_changed.connect(self._update_save_button)
        self._update_save_button()

    def _update_save_button(self, *_):
        self.save_button.set_enabled(bool(self.name_le.get_text().strip()))

    def _save(self):
        name = self.name_le.get_text().strip()
        if not name:
            return
        self.set_return_object((name, self.description_le.get_text().strip()))
        self.close()

    @staticmethod
    def create(mw, name: str, description: str, warnings: list[str], max_name_length: int,
               max_description_length: int):
        return SavePresetDialog(mw, name, description, warnings, max_name_length, max_description_length)


class ReplacePresetDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, name: str):
        return ReplacePresetDialog(
            mw=mw,
            icon=ReplacePresetDialog.WARNING_ICON(),
            title="Replace Preset?",
            text=f"<html>You already have a preset named <b>{html.escape(name)}</b>. Replace it?</html>",
            outcome_1_text="Replace",
            outcome_2_text="Cancel",
            default_outcome=2,
        )


class DeletePresetDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, name: str):
        return DeletePresetDialog(
            mw=mw,
            icon=DeletePresetDialog.WARNING_ICON(),
            title="Delete Preset?",
            text=f"<html>Delete the preset <b>{html.escape(name)}</b>? This cannot be undone. Export it first "
                 "to keep a copy.</html>",
            outcome_1_text="Delete",
            outcome_2_text="Cancel",
            default_outcome=2,
        )


class PresetFileErrorDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, title: str, errors: list[str]):
        return PresetFileErrorDialog(
            mw=mw,
            icon=PresetFileErrorDialog.ERROR_ICON(),
            title=title,
            text="\n\n".join(errors)
        )
