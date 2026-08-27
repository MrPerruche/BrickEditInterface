from ui.dialogs.base import BasicInfoDialog


class AnimatedImageErrorDialog(BasicInfoDialog):

    @staticmethod
    def create(mw):
        return AnimatedImageErrorDialog(
            mw=mw,
            icon=AnimatedImageErrorDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text="You cannot select animated images."
        )

class NotAnImageErrorDialog(BasicInfoDialog):

    @staticmethod
    def create(mw):
        return NotAnImageErrorDialog(
            mw=mw,
            icon=NotAnImageErrorDialog.ERROR_ICON(),
            title="BrickEdit-Interface",
            text="Selected file is not an image."
        )
