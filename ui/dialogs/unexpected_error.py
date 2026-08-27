from ui.dialogs.base import BasicInfoDialog
from traceback import format_exception

class UnexpectedErrorDialog(BasicInfoDialog):

    START_MSG = "An unexpected error has occured: "

    @staticmethod
    def create(mw, description: str | None, exception: BaseException | None):
        assert not (description is None and exception is None), "Either description or exception must be provided"
        return UnexpectedErrorDialog(
            mw=mw,
            icon=UnexpectedErrorDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text=UnexpectedErrorDialog.START_MSG +
                  (description if description is not None else "") +
                  "\n\n" +
                  "".join(format_exception(exception))
        )
