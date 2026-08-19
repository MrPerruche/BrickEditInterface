from ui.dialogs.base import BasicInfoDialog


class VehicleLoadingIssueDialog(BasicInfoDialog):

    @staticmethod
    def create(is_expected_loaded: bool):
        return VehicleLoadingIssueDialog(
            title="BrickEdit-Interface",
            text="You must load a vehicle in order to proceed." if is_expected_loaded else "You cannot proceed while a vehicle is loaded."
        )
