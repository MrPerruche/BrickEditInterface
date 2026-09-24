from ui.dialogs.base import BooleanOutcomeDialog


class RecoverBackupDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw):
        return RecoverBackupDialog(
            mw=mw,
            icon=RecoverBackupDialog.WARNING_ICON(),
            title="Recover Backup",
            text="Are you sure you want to recover this backup? This will overwrite the current vehicle.",
            outcome_1_text="Recover",
            outcome_2_text="Cancel",
            default_outcome=1,
        )


class DeleteBackupDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, backup_path: str):
        return DeleteBackupDialog(
            mw=mw,
            icon=DeleteBackupDialog.WARNING_ICON(),
            title="Delete Backup",
            text=f"Are you sure you want to delete {backup_path}? This action cannot be undone.",
            outcome_1_text="Delete",
            outcome_2_text="Cancel",
            default_outcome=2,
        )
