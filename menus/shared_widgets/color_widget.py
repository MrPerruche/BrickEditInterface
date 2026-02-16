from random import randint
from typing import Optional, Callable

from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication
from PySide6.QtCore import QSize, QTimer
from PySide6.QtGui import QIcon

from .square_widget import SquareWidget

from brickedit import BRVFile, p, vhelper
from utils import get_random_color


class ColorWidget(SquareWidget):

    def __init__(self, brv_source: Callable[[], Optional[BRVFile]], parent=None):
        super().__init__(parent)

        self.brv_source = brv_source
        self.color: int = self.generate_color()
        self.clipboard = QApplication.clipboard()

        self.info_label = QLabel("Set the brick(s) you wish to edit to this color:", self)
        self.info_label.setWordWrap(True)

        # Layout containing eveyrhting
        self.master_layout = QVBoxLayout(self)
        self.master_layout.addWidget(self.info_label)

        # Layout containing the color reset button and the copy buttons
        self.color_layout = QHBoxLayout()
        self.master_layout.addLayout(self.color_layout)
        
        # ============================================================
        # Color button
        # ============================================================

        # Constants
        self.color_button_size = 64
        self.color_icon_size = 28
        self.color_icon = QIcon.fromTheme("view-refresh")

        # Button
        self.color_button = QPushButton()
        self.color_button.setFixedSize(self.color_button_size, self.color_button_size)
        self.color_button.setIcon(self.color_icon)
        self.color_button.setIconSize(QSize(self.color_icon_size, self.color_icon_size))
        self.color_button.clicked.connect(self.reroll_color)

        # Layout
        self.color_layout.addWidget(self.color_button)

        # ============================================================
        # Copy layouts
        # ============================================================

        self.copy_layout = QVBoxLayout()
        self.color_layout.addLayout(self.copy_layout)

        self.ue_copy_layout = QHBoxLayout()
        self.hex_copy_layout = QHBoxLayout()

        self.copy_layout.addLayout(self.ue_copy_layout)
        self.copy_layout.addLayout(self.hex_copy_layout)

        # ============================================================
        # Copy layouts
        # ============================================================

        self.copy_layout = QVBoxLayout()
        self.color_layout.addLayout(self.copy_layout)

        self.ue_copy_layout = QHBoxLayout()
        self.hex_copy_layout = QHBoxLayout()

        self.copy_layout.addLayout(self.ue_copy_layout)
        self.copy_layout.addLayout(self.hex_copy_layout)

        # ============================================================
        # Copy layouts
        # ============================================================

        self.copy_layout = QVBoxLayout()
        self.color_layout.addLayout(self.copy_layout)

        self.ue_copy_layout = QHBoxLayout()
        self.hex_copy_layout = QHBoxLayout()

        self.copy_layout.addLayout(self.ue_copy_layout)
        self.copy_layout.addLayout(self.hex_copy_layout)

        # ============================================================
        # Copy buttons constants
        # ============================================================

        self.copy_icon = QIcon.fromTheme("edit-copy")
        self.copy_button_size = 32
        self.copy_icon_size = 17

        # ============================================================
        # UE copy
        # ============================================================

        self.ue_copy_button = QPushButton()
        self.ue_copy_button.setFixedSize(self.copy_button_size, self.copy_button_size)
        self.ue_copy_button.setIcon(self.copy_icon)
        self.ue_copy_button.setIconSize(QSize(self.copy_icon_size, self.copy_icon_size))
        self.ue_copy_button.clicked.connect(
            lambda: self._copy_with_feedback(
                self.set_to_clipboard_ue_code,
                self.ue_copy_label
            )
        )

        self.ue_copy_label = QLabel("FColorBrickProperty(...)")

        self.ue_copy_layout.addWidget(self.ue_copy_button)
        self.ue_copy_layout.addWidget(self.ue_copy_label)


        # ============================================================
        # HEX copy
        # ============================================================

        self.hex_copy_button = QPushButton()
        self.hex_copy_button.setFixedSize(self.copy_button_size, self.copy_button_size)
        self.hex_copy_button.setIcon(self.copy_icon)
        self.hex_copy_button.setIconSize(QSize(self.copy_icon_size, self.copy_icon_size))
        self.hex_copy_button.clicked.connect(
            lambda: self._copy_with_feedback(
                self.set_to_clipboard_hex_code,
                self.hex_copy_label
            )
        )

        self.hex_copy_label = QLabel(self.get_hex_code(self.color))

        self.hex_copy_layout.addWidget(self.hex_copy_button)
        self.hex_copy_layout.addWidget(self.hex_copy_label)

        

        # Style
        self._apply_color_button_style()

        # Do not stretch.

    def get_ue_code(self, col):
        r, g, b, a = self._unpack_color(col)
        return f"FColorBrickProperty=(R={r},G={g},B={b},A={a})"

    def get_hex_code(self, col):
        return f"{col:08x}".upper()

    def set_to_clipboard_ue_code(self):
        return self.clipboard.setText(self.get_ue_code(self.color))

    def set_to_clipboard_hex_code(self):
        return self.clipboard.setText(self.get_hex_code(self.color))

    def _unpack_color(self, color: int):
        r = (color >> 24) & 0xFF
        g = (color >> 16) & 0xFF
        b = (color >> 8) & 0xFF
        a = color & 0xFF
        return r, g, b, a

    def blend_with_white(self, r, g, b, factor):
        return (
            int(r + (255 - r) * factor),
            int(g + (255 - g) * factor),
            int(b + (255 - b) * factor),
        )

    def _apply_color_button_style(self):
        r, g, b, a = self._unpack_color(self.color)
        r, g, b = self.blend_with_white(r, g, b, (255-a) / 255)
        self.hex_copy_label.setText(self.get_hex_code(self.color))
        self.color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgb({r}, {g}, {b});
            }}
            QPushButton:pressed {{
                background-color: rgb({max(r - 20, 0)}, {max(g - 20, 0)}, {max(b - 20, 0)});
            }}
        """)

    def generate_color(self):

        brv: Optional[BRVFile] = self.brv_source()
        
        # make sure the color is not totally black or white
        r, g, b, a = get_random_color(True).getRgb()
        color = (r << 24) | (g << 16) | (b << 8) | a

        # is the brv not loaded?
        if brv is None:
            return color

        # billions colors possible vs 50000 max bricks. I can't be asked to care
        for brick in brv.bricks:
            if brick.get_property(p.BRICK_COLOR) == color:
                return self.generate_color()  # Retry

        return color

    def reroll_color(self):
        # self.__init__()
        self.color = self.generate_color()
        self._apply_color_button_style()


    def _copy_with_feedback(self, copy_fn, label: QLabel):
        original_text = label.text()

        copy_fn()
        label.setText("Copied ✓")

        QTimer.singleShot(
            900,
            lambda: label.setText(original_text)
    )
