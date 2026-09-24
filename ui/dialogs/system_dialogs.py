from ui.dialogs.base import BasicInfoDialog


class SerializationFailedDialog(BasicInfoDialog):

    @staticmethod
    def create(mw, text: str):
        return SerializationFailedDialog(
            mw=mw,
            icon=SerializationFailedDialog.ERROR_ICON(),
            title="Failed to Save Changes",
            text=text
        )


class UnsupportedOSDialog(BasicInfoDialog):

    @staticmethod
    def create(mw):
        return UnsupportedOSDialog(
            mw=mw,
            icon=UnsupportedOSDialog.ERROR_ICON(),
            title="Unsupported Operating System",
            text="BrickEdit-Interface does not support this operating system."
        )
