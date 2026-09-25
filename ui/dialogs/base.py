from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, Signal

from ui.widgets import Widget, Label, Button

from ui.theme import Theme, register_has_theme_and_apply, unregister


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class Dialog(Widget):

    ICON_SIZE = 40, 40

    # Without an explicit minimum, QDialog shrinks to the narrowest width its layout can get
    # away with -- for a word-wrapped Label, that's just the widest single word, producing a
    # tall, one-word-per-line dialog instead of a properly wrapped paragraph.
    MIN_WIDTH = 420

    _ERROR_ICON = None
    _WARNING_ICON = None
    _INFO_ICON = None
    _CONFIRM_ICON = None


    @classmethod
    def ERROR_ICON(cls):
        if cls._ERROR_ICON is None:
            cls._ERROR_ICON = QIcon(":/assets/icons/IconError.png").pixmap(*cls.ICON_SIZE)
        return cls._ERROR_ICON

    @classmethod
    def WARNING_ICON(cls):
        if cls._WARNING_ICON is None:
            cls._WARNING_ICON = QIcon(":/assets/icons/IconWarning.png").pixmap(*cls.ICON_SIZE)
        return cls._WARNING_ICON

    @classmethod
    def INFO_ICON(cls):
        if cls._INFO_ICON is None:
            cls._INFO_ICON = QIcon(":/assets/icons/IconInfo.png").pixmap(*cls.ICON_SIZE)
        return cls._INFO_ICON

    @classmethod
    def CONFIRM_ICON(cls):
        if cls._CONFIRM_ICON is None:
            cls._CONFIRM_ICON = QIcon(":/assets/icons/IconConfirm.png").pixmap(*cls.ICON_SIZE)
        return cls._CONFIRM_ICON



    def __init__(self, mw: 'BrickEditInterface', icon: QPixmap | None, title: str, parent=None):
        super().__init__(parent)

        self.mw: 'BrickEditInterface' = mw
        self.return_object = None

        self.qt_dialog = QDialog(parent)
        self.qt_dialog.setWindowTitle(title)
        self.qt_dialog.setMinimumWidth(self.MIN_WIDTH)

        self.qt_dialog_layout = QVBoxLayout()
        self.qt_dialog_layout.setContentsMargins(0, 0, 0, 0)
        self.qt_dialog_layout.setSpacing(0)

        self.qt_dialog_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.qt_dialog.setLayout(self.qt_dialog_layout)

        self._content_section = Widget()
        content_section_layout = QVBoxLayout(self._content_section)
        content_section_layout.setContentsMargins(14, 14, 14, 14)
        self.qt_dialog_layout.addWidget(self._content_section, stretch=1)

        self._icon_and_content = Widget()
        self.icon_and_content_layout = QHBoxLayout(self._icon_and_content)
        self.icon_and_content_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_and_content_layout.setSpacing(14)
        content_section_layout.addWidget(self._icon_and_content)

        if icon is not None:
            self.icon_label = QLabel()
            self.icon_label.setPixmap(icon)
            self.icon_and_content_layout.addWidget(self.icon_label)

        self._content = Widget()
        self.content_layout = QVBoxLayout(self._content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_and_content_layout.addWidget(self._content, stretch=1)

        self._actions = Widget()
        self.actions_layout = QHBoxLayout(self._actions)
        self.actions_layout.setContentsMargins(14, 10, 14, 14)
        self.actions_layout.setSpacing(8)
        self.qt_dialog_layout.addWidget(self._actions)
        self._action_buttons: list[Button] = []

        register_has_theme_and_apply(self)
        self.destroyed.connect(lambda: unregister(self))


    def _add_content(self, widget):
        self.content_layout.addWidget(widget)

    def _add_action(self, button: Button, auto_close: bool = True, default: bool = False):
        if auto_close:
            button.clicked.connect(self.close)
        if default:
            button.set_default(True)
        # Expanding + equal stretch lets multiple action buttons share any leftover row width
        # equally; equalizing their minimum widths (below) is what actually guarantees they're
        # the same size even when the row is exactly as wide as their labels need.
        button.setSizePolicy(QSizePolicy.Expanding, button.sizePolicy().verticalPolicy())
        self.actions_layout.addWidget(button, stretch=1)
        self._action_buttons.append(button)
        self._equalize_action_widths()

    def _equalize_action_widths(self):
        widest = max(b.sizeHint().width() for b in self._action_buttons)
        for b in self._action_buttons:
            b.setMinimumWidth(widest)


    _active_dialogs = set()

    def exec(self, blocking: bool = True):
        if blocking:
            self.qt_dialog.exec()
            return self.get_return_object()

        Dialog._active_dialogs.add(self)

        self.qt_dialog.setAttribute(Qt.WA_DeleteOnClose)
        self.qt_dialog.open()

        return self.get_return_object()

    def get_return_object(self):
        return self.return_object

    def set_return_object(self, obj):
        self.return_object = obj

    def close(self):
        unregister(self)
        Dialog._active_dialogs.discard(self)
        self.qt_dialog.close()


    def _apply_theme(self, theme: Theme):
        self.qt_dialog.setStyleSheet(f"background-color: {theme.sidebar.color};")
        self._actions.setStyleSheet(f"background-color: {theme.background.color};")



class BasicInfoDialog(Dialog):

    finished = Signal()

    def __init__(self, mw, icon: QPixmap | None, title: str, text: str, parent=None):
        super().__init__(mw, icon, title, parent)

        self.text_label = Label(text)
        self._add_content(self.text_label)

        self.ok_button = Button("OK")
        self.ok_button.clicked.connect(self.finish)
        self._add_action(self.ok_button, default=True)


    def finish(self):
        self.finished.emit()



class BooleanOutcomeDialog(Dialog):

    finished = Signal(bool)
    outcome_1_selected = Signal()
    outcome_2_selected = Signal()


    def __init__(self,
        mw,
        icon: QPixmap | None,
        title: str,
        text: str,
        outcome_1_text: str,
        outcome_2_text: str,
        parent=None,
        default_outcome: int | None = None,
    ):
        super().__init__(mw, icon, title, parent)
        self.set_return_object(False)

        self.text_label = Label(text)
        self._add_content(self.text_label)

        self.outcome_1_button = Button(outcome_1_text)
        self.outcome_1_button.clicked.connect(self.on_outcome_1_selected)
        self._add_action(self.outcome_1_button, default=default_outcome == 1)

        self.outcome_2_button = Button(outcome_2_text)
        self.outcome_2_button.clicked.connect(self.on_outcome_2_selected)
        self._add_action(self.outcome_2_button, default=default_outcome == 2)


    def on_outcome_1_selected(self):
        self.set_return_object(True)
        self.outcome_1_selected.emit()
        self.finished.emit(True)

    def on_outcome_2_selected(self):
        self.set_return_object(False)
        self.outcome_2_selected.emit()
        self.finished.emit(False)



class TernaryOutcomeDialog(Dialog):

    finished = Signal(int)
    outcome_1_selected = Signal()
    outcome_2_selected = Signal()
    outcome_3_selected = Signal()


    def __init__(self,
        mw,
        icon: QPixmap | None,
        title: str,
        text: str,
        outcome_1_text: str,
        outcome_2_text: str,
        outcome_3_text: str,
        parent=None,
        default_outcome: int | None = None,
    ):
        super().__init__(mw, icon, title, parent)
        self.set_return_object(0)

        self.text_label = Label(text)
        self._add_content(self.text_label)

        self.outcome_1_button = Button(outcome_1_text)
        self.outcome_1_button.clicked.connect(self.on_outcome_1_selected)
        self._add_action(self.outcome_1_button, default=default_outcome == 1)

        self.outcome_2_button = Button(outcome_2_text)
        self.outcome_2_button.clicked.connect(self.on_outcome_2_selected)
        self._add_action(self.outcome_2_button, default=default_outcome == 2)

        self.outcome_3_button = Button(outcome_3_text)
        self.outcome_3_button.clicked.connect(self.on_outcome_3_selected)
        self._add_action(self.outcome_3_button, default=default_outcome == 3)


    def on_outcome_1_selected(self):
        self.set_return_object(1)
        self.outcome_1_selected.emit()
        self.finished.emit(1)

    def on_outcome_2_selected(self):
        self.set_return_object(2)
        self.outcome_2_selected.emit()
        self.finished.emit(2)

    def on_outcome_3_selected(self):
        self.set_return_object(3)
        self.outcome_3_selected.emit()
        self.finished.emit(3)
