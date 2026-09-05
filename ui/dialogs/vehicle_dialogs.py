from ui.dialogs.base import BooleanOutcomeDialog, BasicInfoDialog

from random import uniform

import brickedit



class CannotSaveDialog(BasicInfoDialog):

    DESC_TEXT_NO_REASON = "The vehicle cannot be saved."
    DESC_TEXT = "The vehicle cannot be saved because {0}."

    @staticmethod
    def create(mw, reason: str | None):
        return CannotSaveDialog(
            mw=mw,
            icon=CannotSaveDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text=str.format(CannotSaveDialog.DESC_TEXT, reason if reason is not None else ". ")
        )


class CannotSaveUneditedDialog(BasicInfoDialog):

    @staticmethod
    def create(mw):
        return CannotSaveUneditedDialog(
            mw=mw,
            icon=CannotSaveDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text=str.format(CannotSaveDialog.DESC_TEXT, "it has not been edited")
        )


class CannotSaveOverLimit(BasicInfoDialog):

    @staticmethod
    def create(mw, brick_count: int):
        return CannotSaveOverLimit(
            mw=mw,
            icon=CannotSaveDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text=f"Saving failed because this vehicle contains {brick_count:,} / 50,000 bricks."
        )



class VehicleLoadingIssueDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, is_expected_loaded: bool):
        return VehicleLoadingIssueDialog(
            mw=mw,
            icon=VehicleLoadingIssueDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text="You must load a vehicle in order to proceed." if is_expected_loaded else "You cannot proceed while a vehicle is loaded."
        )


class OverwriteOrCancelDialog(BooleanOutcomeDialog):

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    # def on_outcome_1_selected(self):
    #     # version = self.mw.vehicle_selector_banner.get_brvfile_ref().version
    #     # blank_brvfile = brickedit.BRVFile(version=version)
    #     # self.mw.vehicle_selector_banner.save_brv(blank_brvfile, show_dialogs=False, description="Erase contents before overwriting.")
    #     super().on_outcome_1_selected()


    @staticmethod
    def create(mw):
        return OverwriteOrCancelDialog(
            mw=mw,
            icon=OverwriteOrCancelDialog.WARNING_ICON(),
            title="BrickEdit-Interface",
            text="Performing this action requires no vehicle to be loaded, but one currently is.\n\n"
                 "Do you want to erase and overwrite the currently loaded vehicle?",
            outcome_1_text="Erase and overwrite",
            outcome_2_text="Cancel"
        )



class VehicleSavedDialog(BasicInfoDialog):

    @staticmethod
    def create(mw):
        return VehicleSavedDialog(
            mw=mw,
            icon=VehicleSavedDialog.CONFIRM_ICON(),
            title="BrickEdit-Interface",
            text="This vehicle has been saved."
        )


class NothingEverHappensDialog(BasicInfoDialog):

    MSG_DID_SAVE = "This vehicle has been saved.\n"
    MSG_BASE = "Nothing happened."
    MSG_BASE_EASTEREGG = "Nothing ever happens."
    EASTEREGG_PROBABILITY = 0.01

    @staticmethod
    def create(mw, saved: bool):
        return NothingEverHappensDialog(
            mw=mw,
            icon=NothingEverHappensDialog.INFO_ICON(),
            title="BrickEdit-Interface",
            text=(NothingEverHappensDialog.MSG_DID_SAVE if saved else '') + (
                NothingEverHappensDialog.MSG_BASE_EASTEREGG if uniform(0, 1) < NothingEverHappensDialog.EASTEREGG_PROBABILITY else NothingEverHappensDialog.MSG_BASE
            )
        )
