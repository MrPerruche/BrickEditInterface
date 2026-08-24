from ui.dialogs.base import BasicInfoDialog
from traceback import format_exception

class UnexpectedError(BasicInfoDialog):

    START_MSG = "An unexpected error has occured: "

    @staticmethod
    def create(description: str | None, exception: BaseException | None):
        assert not (description is None and exception is None), "Either description or exception must be provided"
        return UnexpectedError("BrickEdit-Interface",
            UnexpectedError.START_MSG +
            (description if description is not None else "") +
            "\n\n" +
            "".join(format_exception(exception))
        )
