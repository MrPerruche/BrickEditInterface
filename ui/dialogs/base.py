from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal

from ui.widgets import Widget, Label, Button

from ui.theme import Theme, register_has_theme_and_apply, unregister


class Dialog(Widget):

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.qt_dialog = QDialog(parent)
        self.qt_dialog.setWindowTitle(title)

        self.qt_dialog_layout = QVBoxLayout(self.qt_dialog)
        self.qt_dialog_layout.setContentsMargins(20, 20, 20, 20)
        self.qt_dialog_layout.setSpacing(12)

        self._content = Widget(parent=self.qt_dialog)
        self.content_layout = QVBoxLayout(self._content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self._actions = Widget(parent=self.qt_dialog)
        self.actions_layout = QHBoxLayout(self._actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)

        self.qt_dialog_layout.addWidget(self._content)
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
            return self.qt_dialog.exec()

        Dialog._active_dialogs.add(self)

        self.qt_dialog.setAttribute(Qt.WA_DeleteOnClose)
        self.qt_dialog.open()

        return None

    def close(self):
        unregister(self)
        Dialog._active_dialogs.discard(self)
        self.qt_dialog.close()


    def _apply_theme(self, theme: Theme):
        self.qt_dialog.setStyleSheet(f"background-color: {theme.background.color};")



class BasicInfoDialog(Dialog):

    finished = Signal()

    def __init__(self, title: str, text: str, parent=None):
        super().__init__(title, parent)

        self.text_label = Label(text)
        self._add_content(self.text_label)

        self.ok_button = Button("OK")
        self.ok_button.clicked.connect(self.finish)
        self._add_action(self.ok_button)


    def finish(self):
        self.finished.emit()
