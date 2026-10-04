from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from ui.widgets import Widget, ToolButton, Label


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui.components.brick_filter.filters import BaseFilter
    from ui.components.brick_filter.filter_selector import FilterSelector
    from mainwindow import BrickEditInterface


ADD_BTN_ICON = QIcon.fromTheme("list-add")

class FilterEntry(Widget):


    filter_selected = Signal(object)


    def __init__(self, mw: 'BrickEditInterface', filter_selector: 'FilterSelector', filter_class: type['BaseFilter'], parent=None):
        super().__init__()
        self.mw = mw

        self.master_layout = QHBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.filter_selector = filter_selector

        # Single line: a wrapping label asks for 2 lines of height even when its text fits on one
        self.label = Label('', overflow=Label.Overflow.ELIDE_RIGHT)
        self.master_layout.addWidget(self.label, stretch=1)

        self.filter_class = None
        self.set_filter_class(filter_class)

        self.master_layout.addStretch()

        self.add_btn = ToolButton(ADD_BTN_ICON, tint_icon=True)
        self.add_btn.clicked.connect(lambda: self.filter_selected.emit(self))
        self.master_layout.addWidget(self.add_btn)


    def update_mode(self):
        self.label.set_text(self.filter_class.get_filter_name(self.filter_selector.get_mode()))

    def set_filter_class(self, filter_class: type['BaseFilter']):
        self.filter_class = filter_class
        self.update_mode()
        self.label.set_tooltip(filter_class.get_tooltip_contents())

    def get_filter_class(self):
        return self.filter_class

