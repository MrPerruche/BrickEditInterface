from enum import Enum, auto

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QRectF, QEvent
from PySide6.QtGui import (
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QPalette,
)


class SquareState(Enum):
    NORMAL = auto()
    SEVERE = auto()
    HIGHLIGHT = auto()
    ACCENT = auto()


class SquareWidget(QWidget):
    """Rounded square widget with state-based coloring."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Rendering constants
        self.radius: int = 6

        # Hard-coded semantic colors
        # Normal is intentionally lighter than the background
        self._normal_fill = QColor(92, 92, 92, 24)
        self._normal_border = QColor(56, 56, 56)

        self._severe_fill = QColor(192, 24, 36, 72)
        self._severe_border = QColor(192, 24, 36)

        self._state = SquareState.NORMAL

        # Background painting via palette (safe for child widgets)
        self.setAutoFillBackground(True)
        self._apply_background_color()

        # Layout constraints
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(3 * self.radius)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_state(self, state: SquareState):
        if self._state == state:
            return

        self._state = state
        self._apply_background_color()
        self.update()

    def state(self) -> SquareState:
        return self._state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _colors_for_state(self):
        pal = self.palette()

        if self._state == SquareState.NORMAL:
            fill = self._normal_fill
            border = self._normal_border

        elif self._state == SquareState.SEVERE:
            fill = self._severe_fill
            border = self._severe_border

        elif self._state == SquareState.HIGHLIGHT:
            base = pal.color(QPalette.Highlight)
            fill = QColor(base)
            fill.setAlpha(72)
            border = base

        elif self._state == SquareState.ACCENT:
            base = pal.color(QPalette.Accent)
            fill = QColor(base)
            fill.setAlpha(72)
            border = base

        return fill, border

    def _apply_background_color(self):
        fill, _ = self._colors_for_state()

        palette = self.palette()
        palette.setColor(self.backgroundRole(), fill)
        self.setPalette(palette)


    def changeEvent(self, event):
        if event.type() == QEvent.PaletteChange:
            # Re-resolve highlight/accent colors when OS theme changes
            self._apply_background_color()
            self.update()

        super().changeEvent(event)

    def paintEvent(self, event):
        # Let Qt paint background & children first
        super().paintEvent(event)

        _, border = self._colors_for_state()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        painter.setPen(QPen(border, 1))
        painter.drawPath(path)
