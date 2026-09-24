from ui.dialogs.base import BooleanOutcomeDialog


class UnsupportedVehicleVersionDialog(BooleanOutcomeDialog):
    """Warns that a vehicle's file version is outside the supported range, but still
    lets the user choose to load it anyway instead of refusing outright."""

    @staticmethod
    def create_too_old(mw, version: int):
        return UnsupportedVehicleVersionDialog(
            mw=mw,
            icon=UnsupportedVehicleVersionDialog.WARNING_ICON(),
            title="Unsupported Vehicle Version",
            text=(
                f"This vehicle was saved in file version {version}, which is older than "
                "BrickEdit-Interface currently supports.\n\n"
                "Loading it anyway may cause instability or unexpected behavior."
            ),
            outcome_1_text="Load Anyway",
            outcome_2_text="Cancel",
            default_outcome=2,
        )

    @staticmethod
    def create_too_new(mw, version: int, update_available: bool):
        if update_available:
            text = (
                f"This vehicle was saved in file version {version}, which is newer than "
                "BrickEdit-Interface currently supports.\n\n"
                "An update is available and may add support for this version -- we recommend "
                "updating before loading it.\n\n"
                "Loading it anyway may cause instability or unexpected behavior."
            )
        else:
            text = (
                f"This vehicle was saved in file version {version}, which is newer than "
                "BrickEdit-Interface currently supports.\n\n"
                "Loading it anyway may cause instability or unexpected behavior. If you run into "
                "any issues, please report them -- it helps us add support for this version."
            )
        return UnsupportedVehicleVersionDialog(
            mw=mw,
            icon=UnsupportedVehicleVersionDialog.WARNING_ICON(),
            title="Unsupported Vehicle Version",
            text=text,
            outcome_1_text="Load Anyway",
            outcome_2_text="Cancel",
            default_outcome=2,
        )
