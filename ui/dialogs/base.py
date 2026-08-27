from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, Signal

from ui.widgets import Widget, Label, Button

from ui.theme import Theme, register_has_theme_and_apply, unregister


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class Dialog(Widget):

    ICON_SIZE = 40, 40

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

        self.qt_dialog_layout = QVBoxLayout()
        self.qt_dialog_layout.setContentsMargins(14, 14, 14, 14)
        self.qt_dialog_layout.setSpacing(14)
        self.qt_dialog.setLayout(self.qt_dialog_layout)

        self._icon_and_content = Widget()
        self.icon_and_content_layout = QHBoxLayout(self._icon_and_content)
        self.icon_and_content_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_and_content_layout.setSpacing(14)
        self.qt_dialog_layout.addWidget(self._icon_and_content)

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
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        self.qt_dialog_layout.addWidget(self._actions)

        register_has_theme_and_apply(self)


    def _add_content(self, widget):
        self.content_layout.addWidget(widget)

    def _add_action(self, button: Button, auto_close: bool = True):
        if auto_close:
            button.clicked.connect(self.close)
        self.actions_layout.addWidget(button)


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



class BasicInfoDialog(Dialog):

    finished = Signal()

    def __init__(self, mw, icon: QPixmap | None, title: str, text: str, parent=None):
        super().__init__(mw, icon, title, parent)

        self.text_label = Label(text)
        self._add_content(self.text_label)

        self.ok_button = Button("OK")
        self.ok_button.clicked.connect(self.finish)
        self._add_action(self.ok_button)


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
        parent=None
    ):
        super().__init__(mw, icon, title, parent)
        self.set_return_object(False)

        self.text_label = Label(text)
        self._add_content(self.text_label)

        self.outcome_1_button = Button(outcome_1_text)
        self.outcome_1_button.clicked.connect(self.on_outcome_1_selected)
        self._add_action(self.outcome_1_button)

        self.outcome_2_button = Button(outcome_2_text)
        self.outcome_2_button.clicked.connect(self.on_outcome_2_selected)
        self._add_action(self.outcome_2_button)


    def on_outcome_1_selected(self):
        self.set_return_object(True)
        self.outcome_1_selected.emit()
        self.finished.emit(True)

    def on_outcome_2_selected(self):
        self.set_return_object(False)
        self.outcome_2_selected.emit()
        self.finished.emit(False)
