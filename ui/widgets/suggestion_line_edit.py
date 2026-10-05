"""LineEdit which suggests values while typing, in a list under it (like a combo box's, filtered by the text). Any text
can still be typed: suggestions only help. Same API as LineEdit, plus set_suggestions."""

from PySide6.QtWidgets import QCompleter, QListView, QStyledItemDelegate
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QSize, QRect, QModelIndex, QItemSelectionModel, QStringListModel, QEvent, QTimer

from ui.widgets.line_edit import LineEdit
from ui.widgets.popup_list import setup_popup_list, SCROLL_BAR_WIDTH
from ui.theme import Theme, theme_manager

from utils import stack_qcolors

import re
from collections.abc import Iterable


Suggestion = str | tuple[str, str]  # A value, or (value, hint). The hint is shown muted next to it, eg. "modded"

HINT_ROLE = Qt.ItemDataRole.UserRole + 1
ITEM_HEIGHT = 28  # Like ComboBox's items
TEXT_MARGIN = 6   # Left and right of an item, like ComboBox's
HINT_SPACING = 8  # Between a value and its hint
MAX_VISIBLE_ITEMS = 8

_SEPARATORS_RE = re.compile(r"[\s_\-]+")
# Focus given by the user to the line edit, which lists every suggestion if it's empty. Not eg. PopupFocusReason: the
#  list closing gives the focus back to the line edit, it must not reopen
_USER_FOCUS_REASONS = (Qt.FocusReason.MouseFocusReason, Qt.FocusReason.TabFocusReason,
                       Qt.FocusReason.BacktabFocusReason, Qt.FocusReason.ShortcutFocusReason)


def squash(text: str) -> str:
    """text without case, spaces, "_" and "-": what suggestions are matched on. "scalable brick" -> "scalablebrick"."""
    return _SEPARATORS_RE.sub("", text).casefold()


def rank_suggestions(text: str, entries: Iterable[tuple[str, str, str]], all_if_empty: bool = False) -> list[str]:
    """Values of entries ((value, squash(value), squash(hint))) whose value or hint contains every word of text, best
    first: the exact match, then the ones whose value starts with the first word, then by where the first word is in
    the value (matches in the hint only last), shortest first.
    Text without words: every value in alphabetical order if all_if_empty, else none."""
    words = [word for word in map(squash, text.split()) if word]
    if not words:
        return sorted((value for value, *_ in entries), key=str.casefold) if all_if_empty else []
    whole, first = "".join(words), words[0]
    ranked = []
    for value, squashed, hint in entries:
        if all(word in squashed or word in hint for word in words):
            position = squashed.find(first)
            ranked.append((squashed != whole, position < 0, position, len(squashed), value.casefold(), value))
    ranked.sort()
    return [value for *_, value in ranked]


class _SuggestionModel(QStringListModel):
    """Matching suggestions, with their hint (HINT_ROLE)"""

    def __init__(self, hints: dict[str, str], parent=None):
        super().__init__(parent)
        self.hints = hints

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == HINT_ROLE:
            return self.hints.get(super().data(index, Qt.ItemDataRole.DisplayRole), "")
        return super().data(index, role)


class _SuggestionDelegate(QStyledItemDelegate):
    """Paints suggestions like ComboBox's items. Only the current one (arrow keys or mouse) is highlighted."""

    def __init__(self, view: QListView):
        super().__init__(view)
        self.view = view
        self.theme = theme_manager.current()

    def sizeHint(self, option, index):
        # Width as laid out by paint: what the list is widened to (see SuggestionLineEdit._show_popup)
        metrics = option.fontMetrics
        hint = index.data(HINT_ROLE)
        width = 2 * TEXT_MARGIN + metrics.horizontalAdvance(index.data(Qt.ItemDataRole.DisplayRole) or "") + 1
        if hint:
            width += HINT_SPACING + metrics.horizontalAdvance(hint)
        return QSize(width, ITEM_HEIGHT)

    def paint(self, painter, option, index):
        painter.save()
        painter.setFont(option.font)

        background = QColor(self.theme.background.color_hex_argb)
        painter.fillRect(option.rect, background)
        if index == self.view.currentIndex():
            painter.fillRect(option.rect, stack_qcolors(background, QColor(self.theme.surface.color_hex_argb)))

        rect = option.rect.adjusted(TEXT_MARGIN, 0, -TEXT_MARGIN, 0)
        metrics = painter.fontMetrics()
        hint = index.data(HINT_ROLE)
        if hint:
            painter.setPen(QColor(self.theme.text.muted_hex_argb))
            painter.drawText(rect, Qt.AlignVCenter | Qt.AlignRight, hint)
            rect.setRight(rect.right() - metrics.horizontalAdvance(hint) - HINT_SPACING)

        painter.setPen(QColor(self.theme.text.color_hex_argb))
        # Elided when the list can't be widened enough (see SuggestionLineEdit._show_popup)
        text = metrics.elidedText(index.data(Qt.ItemDataRole.DisplayRole), Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()


class SuggestionLineEdit(LineEdit):
    SHOW_ALL_WHEN_EMPTY = True

    def __init__(self, default: str = "", placeholder: str = "", force_validation: bool = True, parent=None, *,
                 suggestions: Iterable[Suggestion] = ()):
        super().__init__(default, placeholder, force_validation, parent)
        self._entries: list[tuple[str, str, str]] = []     # (value, squash(value), squash(hint))
        self._hints: dict[str, str] = {}
        self._by_squashed: dict[str, str | None] = {}       # None: several suggestions, never snapped to
        self._completer: QCompleter | None = None           # See _ensure_popup
        self._popup: QListView | None = None
        self._closing_click = False                         # See eventFilter

        self.qt_widget.installEventFilter(self)
        self.text_edited.connect(self._update_popup)
        self.editing_finished.connect(self._snap_to_suggestion)
        self.set_suggestions(suggestions)


    def set_suggestions(self, suggestions: Iterable[Suggestion]):
        """Values suggested while typing. A suggestion is a value, or (value, hint), the hint being shown muted next to
        it (eg. "modded"). Typed words are looked for in hints too."""
        self._entries = []
        self._hints = {}
        by_squashed: dict[str, str | None] = {}
        for suggestion in suggestions:
            value, hint = (suggestion, "") if isinstance(suggestion, str) else suggestion
            squashed = squash(value)
            self._entries.append((value, squashed, squash(hint)))
            self._hints[value] = hint
            by_squashed[squashed] = value if by_squashed.get(squashed, value) == value else None
        self._by_squashed = by_squashed
        if self._popup is not None:
            self._model.hints = self._hints
            if self._popup.isVisible():
                self._update_popup(self.get_true_text())

    def get_suggestions(self) -> list[str]:
        return [value for value, *_ in self._entries]

    def matching_suggestion(self, text: str) -> str | None:
        """The suggestion text matches, but for case, spaces, "_" and "-". None if there isn't exactly one."""
        return self._by_squashed.get(squash(text))

    def hide_suggestions(self):
        if self._popup is not None:
            self._popup.hide()


    def set_text(self, text: str):
        self.hide_suggestions()  # Not typed: nothing to suggest
        super().set_text(text)

    def set_enabled(self, enabled: bool):
        if not enabled:
            self.hide_suggestions()
        super().set_enabled(enabled)


    def _ensure_popup(self):
        if self._popup is not None:
            return
        self._model = _SuggestionModel(self._hints, self)
        self._completer = QCompleter(self._model, self)
        # Unfiltered: the model only holds the matches, ranked by rank_suggestions
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setMaxVisibleItems(MAX_VISIBLE_ITEMS)

        # The completer's own list (it deletes it). A parentless popup window: the global stylesheet doesn't reach it,
        #  it carries it itself (see _apply_popup_theme). Don't reparent it: it would be deleted twice
        self._popup = self._completer.popup()
        setup_popup_list(self._popup)
        self._popup.setUniformItemSizes(True)
        self._popup.setMouseTracking(True)
        self._popup.entered.connect(self._on_item_hovered)
        self._delegate = _SuggestionDelegate(self._popup)
        self._popup.setItemDelegate(self._delegate)
        self._apply_popup_theme(theme_manager.current())
        # Not QLineEdit.setCompleter: the line edit would filter the list itself, and put the highlighted suggestion
        #  in the text while browsing them with the arrow keys
        self._completer.setWidget(self.qt_widget)
        self._completer.activated[str].connect(self._choose)
        self._popup.installEventFilter(self)  # After the completer's: runs before it

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self._popup:
            if kind == QEvent.Type.MouseButtonPress and not self._popup.rect().contains(event.position().toPoint()):
                # A click outside closes the list, then Qt replays it on what's under the mouse: if it's this line
                #  edit, it must not list every suggestion again
                self._closing_click = True
                QTimer.singleShot(0, self, self._end_closing_click)
        elif watched is self.qt_widget and self.SHOW_ALL_WHEN_EMPTY:
            if ((kind == QEvent.Type.FocusIn and event.reason() in _USER_FOCUS_REASONS)
                    or (kind == QEvent.Type.MouseButtonPress and not self._closing_click)):
                QTimer.singleShot(0, self, self._show_all_if_empty)  # Once the click or focus change is handled
        return super().eventFilter(watched, event)

    def _end_closing_click(self):
        self._closing_click = False

    def _show_all_if_empty(self):
        shown = self._popup is not None and self._popup.isVisible()
        if (self.SHOW_ALL_WHEN_EMPTY and not shown and self.qt_widget.hasFocus() and self.qt_widget.isEnabled()
                and not squash(self.get_true_text())):
            self._update_popup(self.get_true_text())

    def _update_popup(self, text: str):
        matches = rank_suggestions(text, self._entries, all_if_empty=self.SHOW_ALL_WHEN_EMPTY)
        if not matches or matches == [text]:
            self.hide_suggestions()
            return
        self._ensure_popup()
        self._model.setStringList(matches)
        self._show_popup(len(matches))
        # No suggestion picked yet: Enter keeps the text as typed
        self._popup.selectionModel().setCurrentIndex(QModelIndex(), QItemSelectionModel.SelectionFlag.Clear)
        self._popup.scrollToTop()

    def _show_popup(self, count: int):
        # As wide as the line edit, or wider to fit the suggestions (like ComboBox's list), as far as the screen allows
        #  (beyond, they are elided). The completer keeps it on screen
        self._popup.ensurePolished()  # Measured with the stylesheet's font, even before it's first shown
        width = self._popup.sizeHintForColumn(0) + 2 * self._popup.frameWidth()
        if count > MAX_VISIBLE_ITEMS:
            width += SCROLL_BAR_WIDTH
        width = min(max(width, self.qt_widget.width()), self.qt_widget.screen().availableGeometry().width())
        # Where the completer puts it by default: under the line edit, 2 px up (the list goes at the rect's bottom left)
        self._completer.complete(QRect(0, -1, width, self.qt_widget.height()))

    def _on_item_hovered(self, index: QModelIndex):
        # Like a combo box: the hovered suggestion is the current one, the one Enter picks
        self._popup.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)

    def _choose(self, value: str):
        self.set_text(value)

    def _snap_to_suggestion(self):
        text = self.get_true_text()
        value = self.matching_suggestion(text)
        if value is not None and value != text:
            self.set_text(value)


    def _apply_theme(self, theme: Theme):
        super()._apply_theme(theme)
        if getattr(self, "_popup", None) is not None:  # Not built yet (or LineEdit.__init__ applying the first theme)
            self._apply_popup_theme(theme)

    def _apply_popup_theme(self, theme: Theme):
        self._delegate.theme = theme
        self._popup.setStyleSheet(theme_manager.style_sheet_for(self._popup, theme))
