from PySide6.QtWidgets import QLineEdit, QVBoxLayout
from PySide6.QtGui import QValidator, QPalette, QColor

from ui.widgets import Widget
from ui.theme import Theme, register_has_theme_and_apply, repolish, reapply_theme


class _QLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.owner = None

    def focusOutEvent(self, event):
        if self.owner is not None:
            self.owner._focus_lost()

        super().focusOutEvent(event)


class LineEdit(Widget):

    def __init__(self, default: str = "", placeholder: str = "", force_validation: bool = True, parent=None):
        super().__init__(parent=parent)
        self.placeholder = placeholder
        self.force_validation = force_validation
        self._last_acceptable = default

        self.border_color: str | None = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.qt_widget = _QLineEdit()
        self.qt_widget.owner = self
        self.qt_widget.setText(default)
        self.qt_widget.setPlaceholderText(placeholder)
        self.qt_widget.textChanged.connect(self._on_text_changed)
        self._layout.addWidget(self.qt_widget)

        self.text_changed = self.qt_widget.textChanged
        self.editing_finished = self.qt_widget.editingFinished

        self.qt_widget.setProperty('validation', 'acceptable')
        register_has_theme_and_apply(self)


    def is_valid(self):
        return self.qt_widget.hasAcceptableInput()


    def get_text(self):
        if self.qt_widget.hasAcceptableInput() or not self.force_validation:
            return self.qt_widget.text()
        else:
            return self._last_acceptable


    def get_true_text(self):
        return self.qt_widget.text()


    def set_text(self, text: str):
        self.qt_widget.setText(text)
        self._on_text_changed(text)


    def set_border_color(self, color: str | None):
        """Force border color. Color format: '#AARRGGBB'. Set to None to go back to default."""
        self.border_color = color
        reapply_theme(self)


    def set_validator(self, validator):
        self.qt_widget.setValidator(validator)

        if self.qt_widget.hasAcceptableInput():
            self._last_acceptable = self.qt_widget.text()

        self._on_text_changed(self.get_true_text())


    def set_placeholder(self, placeholder: str = ""):
        self.qt_widget.setPlaceholderText(placeholder)
        self.placeholder = placeholder


    def set_max_length(self, max_length: int):
        self.qt_widget.setMaxLength(max_length)


    def _set_validation_state(self, state):
        state_str = 'acceptable' if state == QValidator.Acceptable else 'bad'

        self.qt_widget.setProperty('validation', state_str)
        repolish(self.qt_widget)


    def set_enabled(self, enabled: bool):
        self.qt_widget.setEnabled(enabled)



    def select_all(self):
        self.qt_widget.selectAll()



    def _on_text_changed(self, text):
        validator = self.qt_widget.validator()
        if validator is None:
            return

        state, _, _ = validator.validate(text, 0)

        if state == QValidator.Acceptable:
            self._last_acceptable = text

        self._set_validation_state(state)

    def _focus_lost(self):
        if self.qt_widget.validator() is None:
            return

        if not self.qt_widget.hasAcceptableInput() and self.force_validation:
            self.qt_widget.setText(self._last_acceptable)

    def _apply_theme(self, theme: Theme):

        border_color = self.border_color if self.border_color is not None else theme.border.color
        border_color_disabled = self.border_color if self.border_color is not None else theme.border.muted

        self.setStyleSheet(f"""
            QLineEdit {{
                color: {theme.text.color};
                background-color: {theme.surface.color};

                border: 2px solid {border_color};
                border-radius: 4px;

                padding: 0px 4px;
                

                font-size: 13pt;
            }}
            QLineEdit[validation="bad"] {{
                background-color: {theme.danger_surface.color};
                border-color: {theme.danger_border.color};
            }}

            QLineEdit:hover {{
                background-color: {theme.surface.color_double};
            }}
            QLineEdit:hover[validation="bad"] {{
                background-color: {theme.danger_surface.color_double};
            }}

            QLineEdit:pressed {{
                background-color: {theme.surface.muted};
            }}
            QLineEdit:pressed[validation="bad"] {{
                background-color: {theme.danger_surface.muted};
            }}

            QLineEdit:checked {{
                background-color: {theme.accent.color};
            }}

            QLineEdit:disabled {{
                color: {theme.text.muted};
                background-color: {theme.surface.muted};
                border-color: {border_color_disabled};
            }}
            QLineEdit:disabled[validation="bad"] {{
                background-color: {theme.danger_surface.muted};
                border-color: {theme.danger_border.muted};
            }}
        """)
