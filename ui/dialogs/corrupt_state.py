from ui.dialogs.base import BasicInfoDialog


class CorruptStateDialog(BasicInfoDialog):

    DESC_TEXT = "BrickEdit-Interface is currently in a corrupt state{0}Please reload the vehicle or restart the program."

    @staticmethod
    def create(mw, description: str | None):
        return CorruptStateDialog(
            mw = mw,
            icon = CorruptStateDialog.ERROR_ICON(),
            title = "BrickEdit-Interface",
            text = str.format(CorruptStateDialog.DESC_TEXT, f": {description}\n\n" if description is not None else ". ")
        )
