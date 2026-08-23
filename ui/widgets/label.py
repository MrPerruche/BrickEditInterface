from PySide6.QtWidgets import QLabel, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap

from ui.widgets.widget import Widget
from ui.theme import Theme, register_has_theme_and_apply, reapply_theme
from ui.models import TooltipContents

from typing import ClassVar
from utils import tint_icon

from dataclasses import dataclass


class _QLabel(QLabel):
    """QLabel that paints a small icon flush against the end of the last line of text."""

    ICON_TEXT_MARGIN = 5    # px between text and icon
    ICON_VERTICAL_OFFSET = 1  # px to nudge icon up(-) or down(+) relative to vertical centre

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._icon_pixmap: QPixmap | None = None
        self._icon_size: int = 11
        self._icon_visible: bool = False

    def set_icon(self, pixmap: QPixmap | None, size: int):
        self._icon_pixmap = pixmap
        self._icon_size = size
        self._update_margins()
        self.update()

    def set_icon_visible(self, visible: bool):
        self._icon_visible = visible
        self._update_margins()
        self.update()

    def _update_margins(self):
        showing = self._icon_visible and self._icon_pixmap is not None
        r = self._icon_size + self.ICON_TEXT_MARGIN if showing else 0
        self.setContentsMargins(0, 0, r, 0)

    def _last_line_end_x(self) -> int:
        """Use QTextLayout to accurately find where the last line of wrapped text ends."""
        from PySide6.QtGui import QTextLayout, QTextOption

        text = self.text()
        cr = self.contentsRect()

        option = QTextOption()
        if self.wordWrap():
            option.setWrapMode(QTextOption.WrapMode.WordWrap)
        else:
            option.setWrapMode(QTextOption.WrapMode.NoWrap)
        option.setAlignment(self.alignment())

        layout = QTextLayout(text, self.font())
        layout.setTextOption(option)
        layout.beginLayout()

        last_line = None
        y = 0.0
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(cr.width())
            line.setPosition(QPointF(0, y))
            y += line.height()
            last_line = line

        layout.endLayout()

        if last_line is None:
            return 0

        end_pos = last_line.textStart() + last_line.textLength()
        return int(last_line.cursorToX(end_pos)[0])

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self._icon_visible or self._icon_pixmap is None:
            return

        from PySide6.QtGui import QTextLayout, QTextOption

        cr = self.contentsRect()

        option = QTextOption()
        option.setWrapMode(
            QTextOption.WrapMode.WordWrap
            if self.wordWrap()
            else QTextOption.WrapMode.NoWrap
        )
        option.setAlignment(self.alignment())

        layout = QTextLayout(self.text(), self.font())
        layout.setTextOption(option)

        layout.beginLayout()

        lines = []
        y = 0.0

        while True:
            line = layout.createLine()
            if not line.isValid():
                break

            line.setLineWidth(cr.width())
            line.setPosition(QPointF(0, y))
            y += line.height()
            lines.append(line)

        layout.endLayout()

        if not lines:
            return

        last = lines[-1]

        text_height = int(y)

        alignment = self.alignment()

        if alignment & Qt.AlignBottom:
            text_top = cr.bottom() - text_height + 1
        elif alignment & Qt.AlignVCenter:
            text_top = cr.top() + (cr.height() - text_height) // 2
        else:  # Top (default)
            text_top = cr.top()

        
        end_pos = last.textStart() + last.textLength()
        x = (
            cr.left()
            + int(last.cursorToX(end_pos)[0])
            + self.ICON_TEXT_MARGIN
        )

        y = (
            text_top
            + int(last.y())
            + (int(last.height()) - self._icon_size) // 2
            + self.ICON_VERTICAL_OFFSET
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(
            x,
            y,
            self._icon_pixmap.scaled(
                self._icon_size,
                self._icon_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            ),
        )


class Label(Widget):

    info_icon_size = 11
    info_icon = None

    def __init__(self, text: str | None = None,
        font_size = 13, font_weight = 400,
        muted = False,
        word_wrap = True,
        center_text = False,
        parent = None
    ):
        self.is_muted = muted
        super().__init__(parent)

        self.text = text

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.qt_widget = _QLabel(parent=self) if text is None else _QLabel(text, parent=self)
        self.set_font_size(font_size)
        self.set_font_weight(font_weight)
        self.qt_widget.setWordWrap(word_wrap)

        if center_text:
            self.qt_widget.setAlignment(Qt.AlignCenter)

        self.tooltip_widget = None  # kept for API compat, no longer a real widget
        self.tooltip_enabled = False

        self._layout.addWidget(self.qt_widget)

        self.qt_widget.setProperty('muted', self.is_muted)

        if Label.info_icon is None:
            Label.info_icon = QIcon(':/assets/icons/Information.png')

        register_has_theme_and_apply(self)

    def get_text(self) -> str:
        return self.text

    def set_muted(self, muted: bool):
        if muted != self.is_muted:
            self.is_muted = muted
            self.qt_widget.setProperty('muted', muted)
            reapply_theme(self)

    def set_text(self, text: str):
        self.text = text
        self.qt_widget.setText(text)
        self.qt_widget.update()

    def set_font_size(self, size: int):
        font = self.qt_widget.font()
        font.setPointSize(size)
        self.qt_widget.setFont(font)

    def set_font_weight(self, weight: int):
        font = self.qt_widget.font()
        font.setWeight(QFont.Weight(weight))
        self.qt_widget.setFont(font)

    def set_bold(self, bold: bool):
        self.set_font_weight(700 if bold else 400)

    def set_italic(self, italic: bool):
        font = self.qt_widget.font()
        font.setItalic(italic)
        self.qt_widget.setFont(font)

    def set_tooltip(self, tooltip: TooltipContents | None):
        if tooltip is None:
            self.setToolTip("")
            self.tooltip_enabled = False
        else:
            self.setToolTip(tooltip.richtext())
            self.tooltip_enabled = True
        self._update_tooltip_widget()

    def set_hide_tooltip_indicator(self, hide: bool):
        self.tooltip_enabled = hide
        self._update_tooltip_widget()

    def set_alignment(self, *args, **kwargs):
        return self.qt_widget.setAlignment(*args, **kwargs)

    def _update_tooltip_widget(self):
        self.tooltip_widget = True  # flag so callers using is not None still work
        self.qt_widget.set_icon_visible(self.tooltip_enabled)

    def _apply_theme(self, theme: Theme):
        pixmap = tint_icon(
            self.info_icon, theme.text.color_hex_argb, size=self.info_icon_size
        ).pixmap(self.info_icon_size)
        self.qt_widget.set_icon(pixmap, self.info_icon_size)

        self.setStyleSheet(f"""
            QLabel {{
                color: {theme.text.color};
            }}
            QLabel[muted=true] {{
                color: {theme.text.muted};
            }}
        """)



@dataclass(frozen=True)
class LabelStyle:
    font_size: int
    font_weight: int
    margins: tuple[int | None, int | None, int | None, int | None]
    muted: bool

    HEADER_1: ClassVar["LabelStyle"]
    HEADER_2: ClassVar["LabelStyle"]
    HEADER_3: ClassVar["LabelStyle"]
    HEADER_4: ClassVar["LabelStyle"]
    HEADER_5: ClassVar["LabelStyle"]

    LARGE_3: ClassVar["LabelStyle"]
    LARGE_4: ClassVar["LabelStyle"]
    LARGE_5: ClassVar["LabelStyle"]

    DEFAULT: ClassVar["LabelStyle"]

    SUBTEXT_0: ClassVar["LabelStyle"]
    SUBTEXT_1: ClassVar["LabelStyle"]

LabelStyle.HEADER_1 = LabelStyle(26, 700, (None, 12, None, None), False)
LabelStyle.HEADER_2 = LabelStyle(22, 700, (None, 10, None, None), False)
LabelStyle.HEADER_3 = LabelStyle(18, 700, (None, 8, None, None), False)
LabelStyle.HEADER_4 = LabelStyle(16, 650, (None, 7, None, None), False)
LabelStyle.HEADER_5 = LabelStyle(14, 600, (None, 6, None, None), False)

LabelStyle.LARGE_3 = LabelStyle(18, 700, (None, None, None, None), False)
LabelStyle.LARGE_4 = LabelStyle(16, 650, (None, None, None, None), False)
LabelStyle.LARGE_5 = LabelStyle(14, 600, (None, None, None, None), False)

LabelStyle.DEFAULT = LabelStyle(13, 400, (None, None, None, None), False)

LabelStyle.SUBTEXT_0 = LabelStyle(11, 400, (None, 0, None, None), False)
LabelStyle.SUBTEXT_1 = LabelStyle(9, 500, (None, 0, None, -4), True)


class StyledLabel(Label):

    def __init__(self, text, style: LabelStyle, center_text=False, margins_mult=1, muted: bool | None = None, parent=None):
        super().__init__(text,
            style.font_size,
            style.font_weight,
            muted=style.muted if muted is None else muted,
            center_text = center_text,
            parent=parent
        )

        margins = [m*margins_mult if m is not None else 0 for m in style.margins]
        self.setContentsMargins(*margins)
