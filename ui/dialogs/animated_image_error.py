from ui.dialogs.base import BasicInfoDialog


class AnimatedImageError(BasicInfoDialog):

    @staticmethod
    def create():
        return AnimatedImageError("BrickEdit-Interface", "You cannot select animated images.")
