from ui.dialogs import BooleanOutcomeDialog


class ConfirmRestartDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, header: str, text: str):
        return ConfirmRestartDialog(
            mw=mw,
            icon=ConfirmRestartDialog.WARNING_ICON(),
            title="BrickEdit-Interface",
            text=f"<html><b>{header}</b><br>{text.replace('\n', '<br>')}</html>",
            outcome_1_text="Cancel",
            outcome_2_text="Continue"
        )
