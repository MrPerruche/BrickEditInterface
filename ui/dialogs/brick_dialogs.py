from ui.dialogs.base import BooleanOutcomeDialog, BasicInfoDialog


class UnknownInternalNameDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, internal_name: str):
        return UnknownInternalNameDialog(
            mw=mw,
            icon=UnknownInternalNameDialog.WARNING_ICON(),
            title="Unknown Internal Name",
            text=f"This internal name is not known by BrickEdit: {internal_name}",
            outcome_1_text="Confirm",
            outcome_2_text="Cancel",
            default_outcome=1,
        )


class TooManyColorsDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, max_colors: int):
        return TooManyColorsDialog(
            mw=mw,
            icon=TooManyColorsDialog.WARNING_ICON(),
            title="Too Many Colors",
            text=f"You can only select up to {max_colors} colors."
        )
