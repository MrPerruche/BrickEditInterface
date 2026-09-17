from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Signal, Qt

from ui.widgets import Widget
from ui.theme import Theme, register_has_theme_and_apply


class BoolSwitch(Widget):

    on_toggled = Signal(bool)
    on_enabled = Signal(bool)
    on_disabled = Signal(bool)

    def __init__(self, default: bool, true_text="On", false_text="Off", max_size: int = 80):
        super().__init__()
        self._value = default
        self._true_text = true_text
        self._false_text = false_text
        self._max_size = max_size
        self.setProperty("boolswitch", True)
        self.setCursor(Qt.PointingHandCursor)

        self.master_layout = QHBoxLayout()
        self.setLayout(self.master_layout)
        self.master_layout.setContentsMargins(0, 0, 0, 0)

        # "handle" replaces the old Button. It's just a styled label now -
        # BoolSwitch itself owns click handling (see mousePressEvent below),
        # so the handle is set transparent to mouse events rather than
        # consuming clicks itself.
        self.handle = QLabel("not init!")
        self.handle.setProperty("boolswitch-handle", True)
        self.handle.setAlignment(Qt.AlignCenter)
        self.handle.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.master_layout.addWidget(self.handle)
        self.master_layout.addStretch()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.handle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.update_handle()

        register_has_theme_and_apply(self)

    # -----

    def update_handle(self):
        # Update text
        self.handle.setText(self._true_text if self._value else self._false_text)
        # Update layout
        self.handle.setMaximumWidth(self._max_size // 2)
        self.setMaximumWidth(self._max_size)
        # Move handle
        if self._value:
            self.master_layout.removeWidget(self.handle)
            self.master_layout.insertWidget(1, self.handle)
        else:
            self.master_layout.removeWidget(self.handle)
            self.master_layout.insertWidget(0, self.handle)

    # -----

    def get_value(self):
        return self._value

    def set_value(self, value: bool, emit_signal: bool = True):
        if value != self._value:
            self._value = value
            self.update_handle()

            if emit_signal:
                self.on_toggled.emit(value)
                (self.on_enabled if value else self.on_disabled).emit(value)

    def set_text(self, true_text: str, false_text: str, max_size: int = 120):
        self._true_text = true_text
        self._false_text = false_text
        self._max_size = max_size
        self.update_handle()

    def toggle_state(self):
        self.set_value(not self._value)

    # -----

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_state()
        super().mousePressEvent(event)

    # -----

    def _apply_theme(self, theme: Theme):
        self.setStyleSheet(f"""
            QWidget[boolswitch] {{
                background-color: {theme.surface.muted};

                border: 2px solid {theme.border.muted};
                border-radius: 4px;

                padding: 1px 4px;

                font-size: 13pt;
            }}

            QLabel[boolswitch-handle] {{
                color: {theme.text.color};
                background-color: {theme.surface.color};

                border: 2px solid {theme.border.color};
                border-radius: 4px;

                padding: 1px 4px;

                font-size: 13pt;
            }}
        """)