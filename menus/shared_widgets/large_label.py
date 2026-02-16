"""Large Label Widget (Header Label)"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

class LargeLabel(QLabel):
    _LEVEL_TO_SIZE = {
        1: 24,
        2: 20,
        3: 16,
        4: 14,
        5: 12
    }

    def __init__(self, text, level: int, center_text=False, parent=None):
        super().__init__(text, parent)

        assert level in self._LEVEL_TO_SIZE

        font = self.font()
        font.setPointSize(self._LEVEL_TO_SIZE[level])
        font.setBold(True)
        self.setFont(font)

        self.setMargin(0)
        self.setWordWrap(True)

        if center_text:
            self.setAlignment(Qt.AlignCenter)
