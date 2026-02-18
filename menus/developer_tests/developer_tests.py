from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtGui import QIcon

from menus import base
from ..shared_widgets import TabMenu

class DeveloperTestMenu(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)

        layout1 = QVBoxLayout()
        label11 = QLabel("First menu")
        layout1.addWidget(label11)
        label12 = QLabel("Second menu")
        layout1.addWidget(label12)
        layout1.addStretch()

        layout2 = QVBoxLayout()
        label21 = QLabel("Hello, World")
        layout2.addWidget(label21)
        label22 = QLabel("Hello, World 2")
        layout2.addWidget(label22)
        layout2.addStretch()

        self.tab_menu = TabMenu()
        self.tab_menu.add_menu(0, "Hello", layout1)
        self.tab_menu.add_menu(1, "World", layout2)
        self.master_layout.addWidget(self.tab_menu)


        self.master_layout.addStretch()


    def get_menu_name(self):
        return "Developer tests"

    def get_icon(self):
        return QIcon(":/assets/icons/unknown.png")
