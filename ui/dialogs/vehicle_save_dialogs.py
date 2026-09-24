from ui.dialogs.base import BasicInfoDialog


class VehicleSaveFailedDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, text: str):
        return VehicleSaveFailedDialog(
            mw=mw,
            icon=VehicleSaveFailedDialog.ERROR_ICON(),
            title="Failed to Save Vehicle",
            text=text
        )


class VehicleMetadataSaveFailedDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, text: str):
        return VehicleMetadataSaveFailedDialog(
            mw=mw,
            icon=VehicleMetadataSaveFailedDialog.ERROR_ICON(),
            title="Failed to Save Metadata",
            text=text
        )
