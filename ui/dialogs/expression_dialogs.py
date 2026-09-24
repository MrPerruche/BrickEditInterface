from ui.dialogs.base import BasicInfoDialog


class InvalidExpressionDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, text: str):
        return InvalidExpressionDialog(
            mw=mw,
            icon=InvalidExpressionDialog.WARNING_ICON(),
            title="Invalid Expression",
            text=text
        )
