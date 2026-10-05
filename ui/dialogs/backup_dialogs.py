import html

from ui.dialogs.base import BasicInfoDialog, BooleanOutcomeDialog


class RecoverBackupDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, backup_label: str | None = None):
        what = "this backup" if backup_label is None else f"<b>{html.escape(backup_label)}</b>"
        return RecoverBackupDialog(
            mw=mw,
            icon=RecoverBackupDialog.WARNING_ICON(),
            title="Recover Backup",
            text=f"<html>Are you sure you want to recover {what}? This will overwrite the current vehicle.<br>"
                 "A backup of the current vehicle will be made first.</html>",
            outcome_1_text="Recover",
            outcome_2_text="Cancel",
            default_outcome=1,
        )


class FastUndoConfirmDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, backup_label: str, age_text: str | None):
        """age_text: how long ago the backup was made (eg. "1h 5m"), None if it is dated in the future"""
        when = "dated in the future" if age_text is None else f"{html.escape(age_text)} ago"
        return FastUndoConfirmDialog(
            mw=mw,
            icon=FastUndoConfirmDialog.WARNING_ICON(),
            title="Fast Undo",
            text=f"<html>Revert to <b>{html.escape(backup_label)}</b> ({when})?<br>"
                 "Changes made since will be lost.</html>",
            outcome_1_text="Revert",
            outcome_2_text="Cancel",
            default_outcome=2,
        )


class NothingToUndoDialog(BasicInfoDialog):

    @staticmethod
    def create(mw):
        return NothingToUndoDialog(
            mw=mw,
            icon=NothingToUndoDialog.WARNING_ICON(),
            title="Nothing to Undo",
            text="This vehicle has no BrickEdit-Interface backup to revert to.",
        )


class DeleteBackupDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, backup_label: str, recycle_bin: bool):
        if recycle_bin:
            text = (f"<html>Send <b>{html.escape(backup_label)}</b> to the recycle bin?<br>"
                    "It can be restored from the recycle bin later.</html>")
        else:
            text = (f"<html>Permanently delete <b>{html.escape(backup_label)}</b>?<br>"
                    "This action cannot be undone.</html>")
        return DeleteBackupDialog(
            mw=mw,
            icon=DeleteBackupDialog.WARNING_ICON(),
            title="Delete Backup",
            text=text,
            outcome_1_text="Send to recycle bin" if recycle_bin else "Delete permanently",
            outcome_2_text="Cancel",
            default_outcome=2,
        )


class DeleteExcessBackupsDialog(BooleanOutcomeDialog):

    @staticmethod
    def create(mw, count: int, size_text: str, recycle_bin: bool):
        backups = f"<b>{count} excess backup{'s' if count != 1 else ''}</b> ({html.escape(size_text)})"
        if recycle_bin:
            text = (f"<html>Send {backups} to the recycle bin?<br>"
                    "They can be restored from the recycle bin later.</html>")
        else:
            text = f"<html>Permanently delete {backups}?<br>This action cannot be undone.</html>"
        return DeleteExcessBackupsDialog(
            mw=mw,
            icon=DeleteExcessBackupsDialog.WARNING_ICON(),
            title="Delete Excess Backups",
            text=text,
            outcome_1_text="Send to recycle bin" if recycle_bin else "Delete permanently",
            outcome_2_text="Cancel",
            default_outcome=2,
        )


class BackupOperationFailedDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, action: str, errors: list[BaseException]):
        """action: what failed, eg. "delete the backup" """
        details = "<br>".join(html.escape(f"{type(e).__name__}: {e}") for e in errors[:5])
        if len(errors) > 5:
            details += f"<br>... and {len(errors) - 5} more."
        return BackupOperationFailedDialog(
            mw=mw,
            icon=BackupOperationFailedDialog.ERROR_ICON(),
            title="Backup Operation Failed",
            text=f"<html>Failed to {html.escape(action)}.<br><br>{details}</html>",
        )
