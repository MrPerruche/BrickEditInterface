from ui.dialogs.base import BasicInfoDialog, BooleanOutcomeDialog


class FileNotFoundDialog(BasicInfoDialog):

    FILE_NOT_FOUND_NT = "File not found."
    FILE_NOT_FOUND_TEXT = "File not found at '{0}'."

    @staticmethod
    def create(mw, path: str | None):
        return FileNotFoundDialog(
            mw=mw,
            icon=FileNotFoundDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text=str.format(FileNotFoundDialog.FILE_NOT_FOUND_TEXT, path)
            if path is not None and path else FileNotFoundDialog.FILE_NOT_FOUND_NT
        )


class CorruptSettingsDialog(BooleanOutcomeDialog):

    TEXT = "Failed to load user settings!\nPlease report the following error to the author:\n\n{0}: {1}."

    @staticmethod
    def create(exc: Exception):
        return CorruptSettingsDialog(
            mw=None,
            icon=CorruptSettingsDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text=str.format(CorruptSettingsDialog.TEXT, type(exc).__name__, exc),
            outcome_1="Close BEI",
            outcome_2="Reset settings"
        )
