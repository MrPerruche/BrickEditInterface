from ui.dialogs.base import BooleanOutcomeDialog


class UnsupportedVehicleVersionDialog(BooleanOutcomeDialog):
    """Warns that a vehicle's file version is outside the supported range, but still
    lets the user choose to load it anyway instead of refusing outright."""

    @staticmethod
    def create_too_old(mw, version: int):
        br_version = f"1.{version-7}" if version >= 7 else "legacy"
        return UnsupportedVehicleVersionDialog(
            mw=mw,
            icon=UnsupportedVehicleVersionDialog.WARNING_ICON(),
            title="Unsupported Vehicle Version",
            text=(
                f"This vehicle was saved in file version {version} (Brick Rigs {br_version}), "
                "which is older than BrickEdit-Interface currently supports.\n"
                "Loading it anyway will likely cause instability and unexpected behavior.\n"
                "You can update a vehicle's brv by loading the vehicle in Brick Rigs, doing any "
                "change and undoing it (CTRL+Z ok), then saving the vehicle."
            ),
            outcome_1_text="Load Anyway",
            outcome_2_text="Cancel",
            default_outcome=2,
        )

    @staticmethod
    def create_too_new(mw, version: int, update_available: bool):
        br_version = f"1.{version-7}" if version >= 7 else "legacy"
        text = (
            f"This vehicle was saved in file version {version} (Brick Rigs {br_version} ?), which "
            f"is newer than BrickEdit-Interface currently supports.\n"
        )
        if update_available:
            text += (
                "An update is available and may add support for this version. Please try updating "
                "BrickEdit-Interface first.\n"
                "Loading it anyway may cause instability and unexpected behavior (both errors and "
                "unpredictable UI behavior). "
            )
        else:
            text += (
                "Loading it anyway may cause instability or unexpected behavior (both errors and "
                "unpredictable UI behavior). If you run into any issues, feel free to report "
                "them (with logs!). It helps us add support for Brick Rigs updates faster."
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
