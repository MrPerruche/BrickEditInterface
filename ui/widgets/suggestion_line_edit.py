"""LineEdit which suggests values while typing, in a list under it (like a combo box's, filtered by the text). Any text
can still be typed: suggestions only help. Same API as LineEdit, plus set_suggestions."""

from PySide6.QtWidgets import QCompleter, QListView, QStyledItemDelegate
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, QSize, QModelIndex, QItemSelectionModel, QStringListModel

from ui.widgets.line_edit import LineEdit
from ui.widgets.popup_list import setup_popup_list
from ui.theme import Theme, theme_manager

from utils import stack_qcolors

import re
from collections.abc import Iterable


Suggestion = str | tuple[str, str]  # A value, or (value, hint). The hint is shown muted next to it, eg. "modded"

HINT_ROLE = Qt.ItemDataRole.UserRole + 1
ITEM_HEIGHT = 28  # Like ComboBox's items
MAX_VISIBLE_ITEMS = 8

_SEPARATORS_RE = re.compile(r"[\s_\-]+")


def squash(text: str) -> str:
    """text without case, spaces, "_" and "-": what suggestions are matched on. "scalable brick" -> "scalablebrick"."""
    return _SEPARATORS_RE.sub("", text).casefold()


def rank_suggestions(text: str, entries: Iterable[tuple[str, str]]) -> list[str]:
    """Values of entries ((value, squash(value))) containing every word of text, best first: the exact match, then the
    ones starting with the first word, then by where the first word is, shortest first."""
    words = [word for word in map(squash, text.split()) if word]
    if not words:
        return []
    whole = "".join(words)
    ranked = [(squashed != whole, squashed.find(words[0]), len(squashed), value.casefold(), value)
              for value, squashed in entries if all(word in squashed for word in words)]
    ranked.sort()
    return [value for *_, value in ranked]


class _SuggestionModel(QStringListModel):
    """Matching suggestions, with their hint (HINT_ROLE)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hints: dict[str, str] = {}

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
        return QSize(option.rect.width(), ITEM_HEIGHT)

    def paint(self, painter, option, index):
        painter.save()
        painter.setFont(option.font)

        background = QColor(self.theme.background.color_hex_argb)
        painter.fillRect(option.rect, background)
        if index == self.view.currentIndex():
            painter.fillRect(option.rect, stack_qcolors(background, QColor(self.theme.surface.color_hex_argb)))

        rect = option.rect.adjusted(6, 0, -6, 0)
        metrics = painter.fontMetrics()
        hint = index.data(HINT_ROLE)
        if hint:
            painter.setPen(QColor(self.theme.text.muted_hex_argb))
            painter.drawText(rect, Qt.AlignVCenter | Qt.AlignRight, hint)
            rect.setRight(rect.right() - metrics.horizontalAdvance(hint) - 8)

        painter.setPen(QColor(self.theme.text.color_hex_argb))
        text = metrics.elidedText(index.data(Qt.ItemDataRole.DisplayRole), Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()


class SuggestionLineEdit(LineEdit):
    """LineEdit showing, while typing, the suggestions which contain every word of its text (case, spaces, "_" and "-"
    don't matter), best first. Pick one with a click, or the arrow keys then Enter; Escape closes the list.
    When editing finishes, a text matching a suggestion but for case, spaces, "_" and "-" becomes that suggestion
    (eg. "scalable brick" -> "ScalableBrick").

    Same API as LineEdit: picking a suggestion sets the text, so text_changed is emitted (not text_edited)."""

    def __init__(self, default: str = "", placeholder: str = "", force_validation: bool = True, parent=None, *,
                 suggestions: Iterable[Suggestion] = ()):
        super().__init__(default, placeholder, force_validation, parent)
        self._entries: list[tuple[str, str]] = []           # (value, squash(value))
        self._by_squashed: dict[str, str | None] = {}       # None: several suggestions, never snapped to

        self._model = _SuggestionModel(self)
        self._completer = QCompleter(self._model, self)
        # Unfiltered: the model only holds the matches, ranked by rank_suggestions
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self._completer.setMaxVisibleItems(MAX_VISIBLE_ITEMS)

        # The completer's own list (it deletes it). A parentless popup window: the global stylesheet doesn't reach it,
        #  it carries it itself (see _apply_theme). Don't reparent it: it would be deleted twice
        self._popup: QListView = self._completer.popup()
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

        self.text_edited.connect(self._update_popup)
        self.editing_finished.connect(self._snap_to_suggestion)
        self.set_suggestions(suggestions)


    def set_suggestions(self, suggestions: Iterable[Suggestion]):
        """Values suggested while typing. A suggestion is a value, or (value, hint), the hint being shown muted next to
        it (eg. "modded")."""
        self._entries = []
        hints: dict[str, str] = {}
        by_squashed: dict[str, str | None] = {}
        for suggestion in suggestions:
            value, hint = (suggestion, "") if isinstance(suggestion, str) else suggestion
            squashed = squash(value)
            self._entries.append((value, squashed))
            hints[value] = hint
            by_squashed[squashed] = value if by_squashed.get(squashed, value) == value else None
        self._model.hints = hints
        self._by_squashed = by_squashed
        if self._popup.isVisible():
            self._update_popup(self.get_true_text())

    def get_suggestions(self) -> list[str]:
        return [value for value, _ in self._entries]

    def matching_suggestion(self, text: str) -> str | None:
        """The suggestion text matches, but for case, spaces, "_" and "-". None if there isn't exactly one."""
        return self._by_squashed.get(squash(text))

    def hide_suggestions(self):
        self._popup.hide()


    def set_text(self, text: str):
        self.hide_suggestions()  # Not typed: nothing to suggest
        super().set_text(text)

    def set_enabled(self, enabled: bool):
        if not enabled:
            self.hide_suggestions()
        super().set_enabled(enabled)


    def _update_popup(self, text: str):
        matches = rank_suggestions(text, self._entries)
        if not matches or matches == [text]:
            self.hide_suggestions()
            return
        self._model.setStringList(matches)
        self._completer.complete()  # Shows the list under the line edit, sized for the matches
        # No suggestion picked yet: Enter keeps the text as typed
        self._popup.selectionModel().setCurrentIndex(QModelIndex(), QItemSelectionModel.SelectionFlag.Clear)
        self._popup.scrollToTop()

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
        if hasattr(self, "_delegate"):  # Not yet when LineEdit.__init__ applies the first theme
            self._apply_popup_theme(theme)

    def _apply_popup_theme(self, theme: Theme):
        self._delegate.theme = theme
        self._popup.setStyleSheet(theme_manager.style_sheet_for(self._popup, theme))
