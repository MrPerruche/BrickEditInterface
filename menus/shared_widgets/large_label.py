"""Large Label Widget (Header Label)"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class _LabelLevel:
    px_size: int
    top_margin: int


class LargeLabel(QLabel):
    _LEVEL_TO_SIZE = {
        1: _LabelLevel(24, 12),
        2: _LabelLevel(20, 10),
        3: _LabelLevel(16, 8),
        4: _LabelLevel(14, 7),
        5: _LabelLevel(12, 6),
    }

    def __init__(self, text, level: int, center_text=False, margins_mult=1, parent=None):
        super().__init__(text, parent)

        assert level in self._LEVEL_TO_SIZE
        llevel = self._LEVEL_TO_SIZE[level]

        font = self.font()
        font.setPointSize(llevel.px_size)
        font.setBold(True)
        self.setFont(font)

        self.setContentsMargins(0, margins_mult * llevel.top_margin, 0, 0)
        self.setWordWrap(True)

        if center_text:
            self.setAlignment(Qt.AlignCenter)
