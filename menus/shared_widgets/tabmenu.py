from PySide6.QtWidgets import QWidget, QLayout, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, QStackedWidget

from typing import Hashable



class TabMenu(QWidget):

    def __init__(self, vertical: bool = False, parent=None):
        super().__init__(parent)

        self.vertical = vertical

        self.idx_conversion_table: dict[Hashable, int] = {}
        self.menus_widgets: dict[Hashable, QWidget] = {}
        self.menus_layouts: dict[Hashable, QLayout] = {}
        self.menus_names: dict[Hashable, str] = {}

        self.selectors_lay = QVBoxLayout() if vertical else QHBoxLayout()
        self.selectors_bg = QButtonGroup()
        self.selectors_rbs: dict[Hashable, QRadioButton] = {}
        self.selectors_stack = QStackedWidget()

        self.master_layout = QVBoxLayout()
        self.master_layout.addLayout(self.selectors_lay)
        self.master_layout.addWidget(self.selectors_stack)

        if not vertical:
            self.selectors_lay.addStretch()
        self.setLayout(self.master_layout)


    def add_menu(self, key: Hashable, name: str, element: QWidget | QLayout, edit_margins: bool = True):

        if key in self.idx_conversion_table:
            raise ValueError(f"Key {key} already exists in tab menu")

        self.idx_conversion_table[key] = len(self.idx_conversion_table)

        # SAVE THE NEW MENU

        if isinstance(element, QWidget):
            self.menus_widgets[key] = element
            self.menus_layouts[key] = self.menus_widgets[key].layout()

        elif isinstance(element, QLayout):
            if edit_margins:
                element.setContentsMargins(0, 0, 0, 0)
            self.menus_layouts[key] = element
            self.menus_widgets[key] = QWidget()
            self.menus_widgets[key].setLayout(element)

        else:
            raise ValueError(f"Element {element} is not a QWidget or QLayout")

        # SAVING (MOST SENSITIVE) IS SUCCESSFUL, WE CAN DO OTHER STUFF

        self.menus_names[key] = name

        # ADD THE SELECTOR

        selector = QRadioButton(name)
        selector.clicked.connect(lambda _: self.show_menu(key))
        self.selectors_lay.addWidget(selector)
        if not self.vertical:
            self.selectors_lay.addStretch()  # Keep radio buttons centered

        self.selectors_bg.addButton(selector)
        self.selectors_rbs[key] = selector
        self.selectors_stack.addWidget(self.menus_widgets[key])
        self.menus_widgets[key].hide()

        # FINAL STUFF
        # If this is the first menu, show it
        if len(self.idx_conversion_table) == 1:
            self.show_menu(key)



    def show_menu(self, key: Hashable):
        for menu_key in self.idx_conversion_table.keys():
            self.menus_widgets[menu_key].hide()

        self.menus_widgets[key].show()
        self.selectors_rbs[key].setChecked(True)


    def __getitem__(self, key: Hashable | slice) -> QWidget:
        """
        Syntax example:
            tab_menu = TabMenu()
            tab_menu.add_menu(0, QVBoxLayout())
            tab_menu[0:] -> Widget of the first menu
            tab_menu[0]  -> Layout of the first menu
        """
        if isinstance(key, slice):
            return self.menus_widgets[key.start]
        else:
            return self.menus_layouts[key]

    def __setitem__(self, key: Hashable, value: QWidget | QLayout):
        if isinstance(key, slice):
            key = key.start
        self.add_menu(key, value)
