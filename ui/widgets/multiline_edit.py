from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QTextOption, QTextCursor, QKeyEvent, QKeySequence, QInputMethodEvent

from ui.widgets import Widget
from ui.theme import Theme, style_rules

import unicodedata

_BORDER_WIDTH = 2      # matches the QSS border below
_VERTICAL_PADDING = 2  # matches the QSS padding below (top + bottom each)
_GRIP_HEIGHT = 8        # reserved strip inset into the bottom of the widget, not added to its outer height


def _utf16_len(text: str) -> int:
    return len(text.encode('utf-16-le')) // 2


def _truncate_utf16(text: str, max_units: int) -> str:
    """Longest start of text at most max_units UTF-16 code units long, without splitting a surrogate pair"""
    units = 0
    for i, ch in enumerate(text):
        units += 2 if ord(ch) > 0xFFFF else 1
        if units > max_units:
            return text[:i]
    return text


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
    into the viewport-margin strip reserved for it -- see MultilineEdit. Also has an equivalent of
    QLineEdit.setMaxLength, which QPlainTextEdit lacks."""

    def __init__(self):
        super().__init__()
        self.grip: "_MultilineEditGrip | None" = None

        self._max_length: int | None = None
        self._last_insert_end = 0  # Document position right after the last inserted text
        self.document().contentsChange.connect(self._on_contents_change)
        self.textChanged.connect(self._enforce_max_length)

    # -- max length -- #
    # User input that doesn't fit is cut *before* being inserted (keys, paste / drop, input methods): trimming it
    #  afterwards would be a separate undo step, and undoing it would bring the overflow back, trimmed again at once,
    #  so the undo history before it would be out of reach. _enforce_max_length is only a fallback for other edits.

    def set_max_length(self, max_length: int | None):
        self._max_length = None if max_length is None else max(0, max_length)
        if self._max_length is not None and self._text_length() > self._max_length:
            self.setPlainText(self.toPlainText())  # Truncated, and clears the undo history of the longer text

    def setPlainText(self, text: str):
        super().setPlainText(text if self._max_length is None else _truncate_utf16(text, self._max_length))

    def _text_length(self) -> int:
        # In UTF-16 code units like QLineEdit.maxLength, minus the document's trailing paragraph separator
        return self.document().characterCount() - 1

    def _room(self) -> int | None:
        """UTF-16 code units that can be inserted in place of the selection, None if there's no limit"""
        if self._max_length is None:
            return None
        cursor = self.textCursor()
        return max(0, self._max_length - self._text_length() + cursor.selectionEnd() - cursor.selectionStart())

    @staticmethod
    def _typed_text(e: QKeyEvent) -> str:
        """Text a key press inserts, mirroring QWidgetTextControl's key handling"""
        if (e.matches(QKeySequence.StandardKey.InsertParagraphSeparator)
                or e.matches(QKeySequence.StandardKey.InsertLineSeparator)):
            return "\n"
        text = e.text()
        # Qt inserts tabs and printable text (QChar::isPrint is false for the C* categories)
        if text and (text[0] == "\t" or unicodedata.category(text[0])[0] != "C"):
            return text
        return ""

    def keyPressEvent(self, e: QKeyEvent):
        room = self._room()
        if room is not None and _utf16_len(self._typed_text(e)) > room:
            e.accept()  # Swallowed, so a parent doesn't get it either (eg. Enter accepting a dialog)
            return
        super().keyPressEvent(e)

    def insertFromMimeData(self, source: QMimeData):  # Paste and drop
        room = self._room()
        if room is not None and source.hasText():
            text = source.text().replace("\r\n", "\n")  # Inserted as a single line break
            source = QMimeData()
            source.setText(_truncate_utf16(text, room))
        super().insertFromMimeData(source)

    def inputMethodEvent(self, e: QInputMethodEvent):
        room = self._room()
        if room is not None and e.commitString():
            e.setCommitString(
                _truncate_utf16(e.commitString(), room + e.replacementLength()),
                e.replacementStart(), e.replacementLength()
            )
        super().inputMethodEvent(e)

    def _on_contents_change(self, position: int, _removed: int, added: int):
        self._last_insert_end = position + added

    def _enforce_max_length(self):
        if self._max_length is None:
            return
        overflow = self._text_length() - self._max_length
        if overflow <= 0:
            return

        # Drop the overflow from the end of what was just inserted, keeping the existing text like QLineEdit
        end = min(self._last_insert_end, self._text_length())
        if end < overflow:
            end = self._text_length()
        start = end - overflow
        if start > 0 and 0xDC00 <= ord(self.document().characterAt(start)) <= 0xDFFF:
            start -= 1  # Don't split a surrogate pair (eg. an emoji)

        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.joinPreviousEditBlock()  # Merges with the insertion's undo step, if it was an edit block itself
        cursor.removeSelectedText()
        cursor.endEditBlock()

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

    def set_max_length(self, max_length: int | None):
        """Like LineEdit.set_max_length (counted in UTF-16 code units, as Qt does); None removes the limit"""
        self.qt_widget.set_max_length(max_length)

    def set_line_wrap(self, enabled: bool):
        self.qt_widget.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if enabled else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.qt_widget.setWordWrapMode(QTextOption.WrapMode.WordWrap if enabled else QTextOption.WrapMode.NoWrap)

    def set_enabled(self, enabled: bool):
        self.qt_widget.setEnabled(enabled)

    def select_all(self):
        self.qt_widget.selectAll()
