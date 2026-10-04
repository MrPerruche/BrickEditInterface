"""The actions applied to the selected bricks, in order. Each action is a card, dragged by its header to reorder it."""

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QApplication, QWidget, QScrollArea
from PySide6.QtGui import QIcon, QDrag
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray, QPoint

from ui.widgets import Widget, Surface, Label, ToolButton
from ui.theme import Theme, style_rules
from ui.models import TooltipContents
from ui.components.brick_filter.filters.base_filter import BaseFilter

from menus.rule_based_editor.actions import BaseAction, action_classes

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface
    from systems.bei_files import ConfigReader


MIME_TYPE = "application/x-bei-action-index"
DROP_INDICATOR_HEIGHT = 3
AUTOSCROLL_MARGIN = 60
DRAG_TOOLTIP = TooltipContents("Drag to change the order actions are applied in.")


@style_rules
def _action_list_rules(theme: Theme) -> str:
    return f"""
        QWidget[actionDropIndicator="true"] {{
            background-color: {theme.accent_border.color};
            border-radius: 1px;
        }}"""


class _CardHeader(Widget):
    """Header of an ActionCard, which the card is dragged by"""

    def __init__(self, card: 'ActionCard'):
        super().__init__()
        self.card = card
        self._press_pos: QPoint | None = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.position().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if (self._press_pos is not None and e.buttons() & Qt.MouseButton.LeftButton
                and (e.position().toPoint() - self._press_pos).manhattanLength() >= QApplication.startDragDistance()):
            hot_spot, self._press_pos = self._press_pos, None
            mime = QMimeData()
            mime.setData(MIME_TYPE, QByteArray(str(self.card.index).encode()))
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.setHotSpot(hot_spot)
            drag.exec(Qt.DropAction.MoveAction)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._press_pos = None
        super().mouseReleaseEvent(e)


class ActionCard(Surface):
    """One action: its type, and the settings of that type. Settings of the other types are kept while the card
    lives, so switching back and forth loses nothing."""

    changed = Signal()                 # Type or settings changed
    remove_requested = Signal(object)  # The card

    def __init__(self, mw: 'BrickEditInterface', action_cls: type[BaseAction]):
        super().__init__()
        self.mw = mw
        self.index = 0
        self._instances: dict[type[BaseAction], BaseAction] = {}
        self._selection: list[brickedit.Brick] = []

        self.header = _CardHeader(self)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.header.set_tooltip(DRAG_TOOLTIP)  # Shown over the handle and the number (no "?" indicator: too busy)
        header_layout.addWidget(Label("≡", muted=True))
        self.step_label = Label("")
        header_layout.addWidget(self.step_label)
        self.type_cb = BaseFilter.make_combo_box([cls.get_name() for cls in action_classes])
        header_layout.addWidget(self.type_cb, stretch=1)
        self.remove_button = ToolButton(QIcon.fromTheme("edit-delete"), tint_icon=True)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))
        header_layout.addWidget(self.remove_button)
        self.layout().addWidget(self.header)

        self.action_layout = QVBoxLayout()
        self.action_layout.setContentsMargins(0, 4, 0, 0)
        self.layout().addLayout(self.action_layout)

        self.hint_label = Label("", muted=True)
        self.hint_label.set_font_size(11)
        self.layout().addWidget(self.hint_label)
        self.hint_label.hide()
        self._show_hint = False

        self.set_action_type(action_cls)
        self.type_cb.item_changed.connect(self._on_type_selected)


    @property
    def action(self) -> BaseAction:
        return self._instances[action_classes[max(self.type_cb.get_current_idx(), 0)]]

    def set_action_type(self, action_cls: type[BaseAction]) -> BaseAction:
        self.type_cb.qt_widget.blockSignals(True)
        try:
            self.type_cb.set_current_idx(action_classes.index(action_cls))
        finally:
            self.type_cb.qt_widget.blockSignals(False)
        self._show(action_cls)
        return self.action

    def _on_type_selected(self, *_):
        self._show(action_classes[max(self.type_cb.get_current_idx(), 0)])
        self.changed.emit()

    def _show(self, action_cls: type[BaseAction]):
        if action_cls not in self._instances:
            action = action_cls(self.mw)
            action.options_changed.connect(self.changed.emit)
            self._instances[action_cls] = action
            self.action_layout.addWidget(action)
        for cls, action in self._instances.items():
            action.setVisible(cls is action_cls)
        self._instances[action_cls].on_selection_changed(self._selection)
        self.type_cb.set_tooltip(action_cls.get_tooltip())
        self._update_hint()

    def set_selection(self, bricks: list[brickedit.Brick]):
        self._selection = bricks
        self.action.on_selection_changed(bricks)

    def set_position(self, index: int, count: int):
        self.index = index
        self.step_label.set_text(f"{index + 1}.")
        self.remove_button.set_enabled(count > 1)
        self._show_hint = index < count - 1
        self._update_hint()

    def _update_hint(self):
        hint = self.action.next_selection_hint() if self._show_hint else None
        self.hint_label.set_text(f"↓ {hint}" if hint else "")
        self.hint_label.setVisible(bool(hint))


class ActionList(Widget):
    """Action cards, in the order they're applied"""

    changed = Signal()  # Order, types or settings of the actions changed

    def __init__(self, mw: 'BrickEditInterface', parent=None):
        super().__init__(parent)
        self.mw = mw
        self.cards: list[ActionCard] = []
        self._selection: list[brickedit.Brick] = []
        self.setAcceptDrops(True)

        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.setSpacing(6)

        self.drop_indicator = QWidget(self)
        self.drop_indicator.setProperty("actionDropIndicator", True)
        self.drop_indicator.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.drop_indicator.hide()


    def actions(self) -> list[BaseAction]:
        return [card.action for card in self.cards]

    def _make_card(self, action_cls: type[BaseAction] | None, config: 'ConfigReader | None') -> ActionCard:
        card = ActionCard(self.mw, action_cls or action_classes[0])
        card.set_selection(self._selection)
        if config is not None:
            try:
                card.action.apply_config(config)
            except BaseException:
                card.deleteLater()
                raise
        card.changed.connect(self.changed.emit)
        card.remove_requested.connect(self.remove_card)
        return card

    def add_action(self, action_cls: type[BaseAction] | None = None) -> BaseAction:
        card = self._make_card(action_cls, None)
        self.cards.append(card)
        self.master_layout.addWidget(card)
        self._update_positions()
        return card.action

    def set_actions(self, entries: list[tuple[type[BaseAction], 'ConfigReader | None']]):
        """Replaces every action. Raises BeiFileError if a config is invalid, in which case nothing changes."""
        new_cards: list[ActionCard] = []
        try:
            for action_cls, config in entries:
                new_cards.append(self._make_card(action_cls, config))
        except BaseException:
            for card in new_cards:
                card.deleteLater()
            raise
        for card in self.cards:
            self.master_layout.removeWidget(card)
            card.hide()
            card.deleteLater()
        self.cards = new_cards
        for card in self.cards:
            self.master_layout.addWidget(card)
        self._update_positions()

    def remove_card(self, card: ActionCard):
        if len(self.cards) <= 1 or card not in self.cards:
            return
        self.cards.remove(card)
        self.master_layout.removeWidget(card)
        card.hide()
        card.deleteLater()
        self._update_positions()

    def move(self, index: int, insert_at: int):
        """Moves the action at index so it ends up before the action currently at insert_at"""
        if insert_at in (index, index + 1) or not 0 <= index < len(self.cards):
            return
        card = self.cards.pop(index)
        self.cards.insert(insert_at - 1 if insert_at > index else insert_at, card)
        for card in self.cards:
            self.master_layout.removeWidget(card)
        for card in self.cards:
            self.master_layout.addWidget(card)
        self._update_positions()

    def set_selection(self, bricks: list[brickedit.Brick]):
        """Bricks matching the conditions, passed to each action (see BaseAction.on_selection_changed)"""
        self._selection = bricks
        for card in self.cards:
            card.set_selection(bricks)

    def _update_positions(self):
        for i, card in enumerate(self.cards):
            card.set_position(i, len(self.cards))
        self.changed.emit()


    # Drag and drop

    def _insert_index(self, y: float) -> int:
        for i, card in enumerate(self.cards):
            if y < card.geometry().center().y():
                return i
        return len(self.cards)

    def _show_indicator(self, index: int):
        if not self.cards:
            return
        spacing = self.master_layout.spacing()
        if index < len(self.cards):
            y = self.cards[index].geometry().top() - (spacing + DROP_INDICATOR_HEIGHT) // 2
        else:
            y = self.cards[-1].geometry().bottom() + (spacing - DROP_INDICATOR_HEIGHT) // 2 + 1
        self.drop_indicator.setGeometry(0, max(0, y), self.width(), DROP_INDICATOR_HEIGHT)
        self.drop_indicator.raise_()
        self.drop_indicator.show()

    def _autoscroll(self, pos: QPoint):
        """Cards can be tall: scroll the menu when dragging near the edge of the visible area"""
        parent = self.parentWidget()
        while parent is not None and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if parent is not None and parent.widget() is not None:
            target = self.mapTo(parent.widget(), pos)
            parent.ensureVisible(target.x(), target.y(), 0, AUTOSCROLL_MARGIN)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_TYPE):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_TYPE):
            pos = e.position().toPoint()
            self._show_indicator(self._insert_index(pos.y()))
            self._autoscroll(pos)
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self.drop_indicator.hide()

    def dropEvent(self, e):
        self.drop_indicator.hide()
        if not e.mimeData().hasFormat(MIME_TYPE):
            return
        e.acceptProposedAction()
        self.move(int(bytes(e.mimeData().data(MIME_TYPE)).decode()), self._insert_index(e.position().y()))
