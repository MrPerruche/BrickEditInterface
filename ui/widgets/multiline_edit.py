from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextOption

from ui.widgets import Widget
from ui.theme import Theme, style_rules

_BORDER_WIDTH = 2      # matches the QSS border below
_VERTICAL_PADDING = 2  # matches the QSS padding below (top + bottom each)
_GRIP_HEIGHT = 8        # reserved strip inset into the bottom of the widget, not added to its outer height


@style_rules
def _multiline_edit_rules(theme: Theme) -> str:
    return f"""
        QPlainTextEdit[beiMultilineEdit="true"] {{
            color: {theme.text.color};
            background-color: {theme.surface.color};

            border: {_BORDER_WIDTH}px solid {theme.border.color};
            border-radius: 4px;

            padding: {_VERTICAL_PADDING}px 4px;

            font-size: 13pt;
        }}

        QPlainTextEdit[beiMultilineEdit="true"]:hover {{
            background-color: {theme.surface.color_double};
        }}

        QPlainTextEdit[beiMultilineEdit="true"]:focus {{
            background-color: {theme.surface.muted};
        }}

        QPlainTextEdit[beiMultilineEdit="true"]:disabled {{
            color: {theme.text.muted};
            background-color: {theme.surface.muted};
            border-color: {theme.border.muted};
        }}

        QWidget[beiMultilineEditGrip="true"] {{
            background-color: transparent;
            border-radius: 0 0 2px 2px;
        }}
        QWidget[beiMultilineEditGrip="true"]:hover {{
            background-color: {theme.surface.color_double};
        }}

        QWidget[beiMultilineEditGripBar="true"] {{
            background-color: {theme.border.color};
            border-radius: 1px;
        }}"""


class _MultilinePlainTextEdit(QPlainTextEdit):
    """QPlainTextEdit that keeps its resize grip (if any) pinned to its own bottom edge, inset
    into the viewport-margin strip reserved for it -- see MultilineEdit."""

    def __init__(self):
        super().__init__()
        self.grip: "_MultilineEditGrip | None" = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.grip is not None:
            self.grip.setGeometry(0, self.height() - _GRIP_HEIGHT - _BORDER_WIDTH, self.width(), _GRIP_HEIGHT)


class _MultilineEditGrip(QWidget):
    """Thin bar inset into the bottom of the text edit -- drag it up/down to resize, like a
    browser textarea. A child of the QPlainTextEdit itself (not of MultilineEdit's own layout),
    so it never adds to the widget's outer size -- otherwise it throws off vertical alignment
    with sibling widgets (eg. buttons) in whatever row/form this widget is placed in."""

    def __init__(self, target: QPlainTextEdit, min_height: int, parent=None):
        super().__init__(parent)
        self._target = target
        self._min_height = min_height
        self._drag_origin_y: float | None = None
        self._drag_start_height = 0

        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setProperty('beiMultilineEditGrip', True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        bar = QWidget()
        bar.setFixedSize(24, 3)
        bar.setProperty('beiMultilineEditGripBar', True)
        layout.addWidget(bar)

    def set_min_height(self, min_height: int):
        self._min_height = min_height

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_origin_y = e.globalPosition().y()
            self._drag_start_height = self._target.height()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_origin_y is not None:
            delta = e.globalPosition().y() - self._drag_origin_y
            new_height = max(self._min_height, round(self._drag_start_height + delta))
            self._target.setFixedHeight(new_height)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_origin_y = None
        super().mouseReleaseEvent(e)


class MultilineEdit(Widget):
    """A multiline text input -- Qt's own equivalent of a `QLineEdit` is `QPlainTextEdit`
    (lighter-weight than `QTextEdit`, which additionally supports rich text).

    `lines` sets the default height (in text lines). If `resizable` is set, a drag handle is
    inset into the bottom of the widget so the user can adjust its height, like a browser
    `<textarea>` -- it doesn't add to the widget's outer size, so it stays aligned with sibling
    widgets the same way a non-resizable instance would.
    """

    def __init__(self, default: str = "", placeholder: str = "", line_wrap: bool = True,
        lines: float = 4, resizable: bool = False, parent=None
    ):
        super().__init__(parent=parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.qt_widget = _MultilinePlainTextEdit()
        self.qt_widget.setPlainText(default)
        self.qt_widget.setPlaceholderText(placeholder)
        self.qt_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.qt_widget.setProperty('beiMultilineEdit', True)  # Selected by _multiline_edit_rules
        self.set_line_wrap(line_wrap)
        self._layout.addWidget(self.qt_widget)

        self.text_changed = self.qt_widget.textChanged

        self.resizable = resizable
        self._grip = None
        if resizable:
            self._grip = _MultilineEditGrip(self.qt_widget, min_height=self._height_for_lines(1), parent=self.qt_widget)
            self.qt_widget.grip = self._grip
            self._grip.raise_()
            self.qt_widget.setViewportMargins(0, 0, 0, _GRIP_HEIGHT)

        self.set_lines(lines)

    def _height_for_lines(self, lines: float) -> int:
        fm = self.qt_widget.fontMetrics()
        doc_margin = self.qt_widget.document().documentMargin()
        extra = 2 * (doc_margin + _BORDER_WIDTH + _VERTICAL_PADDING)
        if self.resizable:
            extra += _GRIP_HEIGHT  # reserved viewport margin for the grip -- keep it out of the text area
        return round(fm.lineSpacing() * lines + extra)

    def set_lines(self, lines: float):
        height = self._height_for_lines(lines)
        self.qt_widget.setFixedHeight(height)
        if self._grip is not None:
            self._grip.set_min_height(self._height_for_lines(1))

    def get_text(self) -> str:
        return self.qt_widget.toPlainText()

    def set_text(self, text: str):
        self.qt_widget.setPlainText(text)

    def set_placeholder(self, placeholder: str = ""):
        self.qt_widget.setPlaceholderText(placeholder)

    def set_read_only(self, read_only: bool):
        self.qt_widget.setReadOnly(read_only)

    def set_line_wrap(self, enabled: bool):
        self.qt_widget.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if enabled else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.qt_widget.setWordWrapMode(QTextOption.WrapMode.WordWrap if enabled else QTextOption.WrapMode.NoWrap)

    def set_enabled(self, enabled: bool):
        self.qt_widget.setEnabled(enabled)

    def select_all(self):
        self.qt_widget.selectAll()
