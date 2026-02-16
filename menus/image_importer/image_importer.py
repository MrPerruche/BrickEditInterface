from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QIcon

from menus import base
from .widgets import ImageSelector

class ImageImporter(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)

        self.image_selector = ImageSelector()
        self.master_layout.addWidget(self.image_selector)
        self.master_layout.addStretch()

    def get_menu_name(self):
        return "Image Importer"

    def get_icon(self):
        return QIcon(":/assets/icons/ImageIcon.png")
