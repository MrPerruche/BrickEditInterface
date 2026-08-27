from ui.dialogs.base import BasicInfoDialog


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
