from ui.dialogs.base import BasicInfoDialog


class CannotSaveDialog(BasicInfoDialog):

    DESC_TEXT_NO_REASON = "The vehicle cannot be saved."
    DESC_TEXT = "The vehicle cannot be saved because {0}."

    @staticmethod
    def create(reason: str | None):
        return CannotSaveDialog(
            title="BrickEdit-Interface",
            text=str.format(CannotSaveDialog.DESC_TEXT, reason if reason is not None else ". ")
        )



class CannotSaveUneditedDialog(BasicInfoDialog):

    @staticmethod
    def create():
        return CannotSaveUneditedDialog(
            title="BrickEdit-Interface",
            text=str.format(CannotSaveDialog.DESC_TEXT, "it has not been edited")
        )
