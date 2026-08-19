from PySide6.QtWidgets import QHBoxLayout, QApplication
from PySide6.QtGui import QColor, QIcon

from ui.widgets import Label, LineEdit, Button
from ui.components.brick_filter.filters.base_filter import FilterMode, FilterResult, BaseFilter
from ui.validators import HEX_4COLOR_VALIDATOR

from utils import get_random_color

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


def rgba(col: QColor) -> str:
    return f"{col.red():02x}{col.green():02x}{col.blue():02x}{col.alpha():02x}"


class ColorFilter(BaseFilter):

    copy_icon = None

    def __init__(self, mw: 'BrickEditInterface', mode: FilterMode):
        super().__init__(mw)

        if self.copy_icon is None:
            self.copy_icon = QIcon.fromTheme("edit-copy")

        self.mode = mode
        self.color: QColor = get_random_color(True)
        self.clipboard = QApplication.clipboard()

        self.label_layout = QHBoxLayout()
        self.label_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.label_layout)

        # LABEL LAYOUT
        self.label = Label(f"Brick color {mode.get_naming_tuple()[1]} be")
        self.label_layout.addWidget(self.label)

        self.color_le = LineEdit(rgba(self.color).upper())
        self.color_le.setFixedWidth(78)
        self.color_le.set_validator(HEX_4COLOR_VALIDATOR)
        self.color_le.text_changed.connect(self.update_color)
        self.update_color()
        self.label_layout.addWidget(self.color_le)

        # COLOR LAYOUT
        self.color_layout = QHBoxLayout()
        self.color_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.color_layout)

        self.copy_color_hex = Button('Hex', icon=self.copy_icon, tint_icon=True)
        self.copy_color_hex.clicked.connect(lambda: self.copy_color(False))
        self.color_layout.addWidget(self.copy_color_hex, stretch=1)

        self.color_button = Button('FColorBrickProperty', icon=self.copy_icon, tint_icon=True)
        self.color_button.clicked.connect(lambda: self.copy_color(True))
        self.color_layout.addWidget(self.color_button, stretch=1)

        self.color_layout.addWidget(self.remove_filter_button)


    def copy_color(self, ue_format: bool):
        """Sets clipboard to the current color 'RRGGBBAA' format"""
        if ue_format:
            r, g, b, a = self.color.red(), self.color.green(), self.color.blue(), self.color.alpha()
            self.clipboard.setText(f"FColorBrickProperty=(R={r},G={g},B={b},A={a})")
        else:
            self.clipboard.setText(rgba(self.color))

    def update_color(self):
        col_rgba = self.color_le.get_text().strip()
        col_argb = col_rgba[-2:] + col_rgba[:-2]
        self.color = QColor('#' + col_argb)
        self.color_le.set_border_color('#' + col_argb)
        self.filter_edited.emit(self)

    def is_allowed(self, brick) -> FilterResult:
        col_tuple = self.color.red(), self.color.green(), self.color.blue(), self.color.alpha()
        col_num = col_tuple[0] << 24 | col_tuple[1] << 16 | col_tuple[2] << 8 | col_tuple[3]
        try:
            col_brick = brick.get_property(brickedit.p.BRICK_COLOR)
        except brickedit.BrickError:
            return self.mode.filter_did_not_match()

        if col_num == col_brick:
            return self.mode.filter_matched()
        #else:
        return self.mode.filter_did_not_match()


    @classmethod
    def get_filter_name(cls, mode: FilterMode) -> str:
        return f"Brick color {mode.get_naming_tuple()[1]} be (...)"

    @classmethod
    def new(cls, mw: 'BrickEditInterface', mode: FilterMode):
        return ColorFilter(mw, mode)
