from PySide6.QtGui import QPainter

from ui.widgets.widget import Widget
from ui.theme import Theme, register_has_theme_and_apply


class Separator(Widget):
    def __init__(
        self,
        margin_top: int = 9,
        margin_bottom: int = 9,
        parent=None
    ):
        super().__init__(parent)

        self.margin_top = margin_top
        self.margin_bottom = margin_bottom

        self.setFixedHeight(2 + margin_top + margin_bottom)

        register_has_theme_and_apply(self)


    def _apply_theme(self, theme: Theme):
        self._color = theme.border.color_hex_argb
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(
            0,
            self.margin_top,
            self.width(),
            2,
            self._color,
        )
