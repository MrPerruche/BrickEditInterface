from PySide6.QtWidgets import QPushButton, QVBoxLayout
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QColor

from ui.widgets.widget import Widget
from ui.theme import Theme, register_has_theme_and_apply, theme_manager
from ui.animations.pulse import PulseAnimation
from ui.models import TooltipContents

from utils import tint_icon


class Button(Widget):

    def __init__(self, text: str = '', icon: QIcon | None = None, tint_icon: bool | None = None, icon_size: int = 16, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self.danger = PulseAnimation(
            callback=self._danger_changed,
            duration=900,
            parent=self,
        )

        self.og_text = text
        self.icon_spacing_prepend = " "
        self.qt_widget = QPushButton("(button name not updated in init!)")
        self._layout.addWidget(self.qt_widget)
        
        self.og_icon = icon
        self.tint_icon = tint_icon if tint_icon is not None else False
        self.icon_size = icon_size
        if icon is not None and tint_icon is None:
            raise ValueError("argument tint_icon must be specified if icon is not None")

        self.clicked = self.qt_widget.clicked
        self.toggled = self.qt_widget.toggled

        self.set_text(text)
        register_has_theme_and_apply(self)


    # danger stuff
    
    def set_danger(self, enabled: bool):
        if enabled:
            self.danger.start()
        else:
            self.danger.stop()
            self._apply_theme(theme_manager.current())

    def get_danger(self) -> bool:
        return self.danger.is_active()

    def _danger_changed(self, value: float):
        self._apply_theme(theme_manager.current())


    @staticmethod
    def _blend(a: str, b: str, t: float) -> str:
        ca = QColor(a)
        cb = QColor(b)

        r = round(ca.red()   + (cb.red()   - ca.red())   * t)
        g = round(ca.green() + (cb.green() - ca.green()) * t)
        b = round(ca.blue()  + (cb.blue()  - ca.blue())  * t)
        a = round(ca.alpha() + (cb.alpha() - ca.alpha()) * t)

        return QColor(r, g, b, a).name(QColor.HexArgb)

    # basic stuff

    def set_tooltip(self, tooltip: TooltipContents | None):
        if tooltip is None:
            self.setToolTip("")
        else:
            self.setToolTip(tooltip.richtext())

    def set_enabled(self, enabled: bool):
        self.qt_widget.setEnabled(enabled)

    def set_disabled(self, disabled: bool):
        self.qt_widget.setDisabled(disabled)

    def set_checkable(self, checkable: bool):
        self.qt_widget.setCheckable(checkable)

    def set_checked(self, checked: bool):
        self.qt_widget.setChecked(checked)

    def set_text(self, text: str):
        self.og_text = text
        text = text if self.og_icon is None else self.icon_spacing_prepend + text
        self.qt_widget.setText(text)

    def _set_icon(self, icon: QIcon | None):
        if icon is None:
            self.qt_widget.setIcon(QIcon())
        else:
            self.qt_widget.setIcon(icon)
            self.qt_widget.setIconSize(QSize(self.icon_size, self.icon_size))

    def set_icon(self, icon: QIcon | None):
        self.og_icon = icon
        self._set_icon(icon)
        self._apply_theme(theme_manager.current())

    def get_text(self):
        return self.og_text


    def _apply_theme(self, theme: Theme):
        if self.danger.is_active():
            bg = self._blend(
                theme.surface.color_hex_argb,
                theme.danger_surface.color_hex_argb,
                self.danger.current_value(),
            )
            hover = self._blend(
                theme.surface.color_advanced(2, True),
                theme.danger_surface.color_advanced(2, True),
                self.danger.current_value(),
            )
            pressed = self._blend(
                theme.surface.muted_hex_argb,
                theme.danger_surface.color_hex_argb,
                self.danger.current_value(),
            )
            border = self._blend(
                theme.border.color_hex_argb,
                theme.danger.color_hex_argb,
                self.danger.current_value(),
            )
        else:
            bg = theme.surface.color
            hover = theme.surface.color_double
            pressed = theme.surface.muted
            border = theme.border.color


        style = f"""
            QPushButton {{
                color: {theme.text.color};
                background-color: {bg};

                border: 2px solid {border};
                border-radius: 4px;

                padding: 1px 4px;
                

                font-size: 13pt;
            }}

            QPushButton:hover {{
                background-color: {hover};
                border-color: {border};
            }}

            QPushButton:pressed {{
                background-color: {pressed};
            }}

            QPushButton:checked {{
                background-color: {theme.accent.color};
                border-color: {theme.accent_border.color};
            }}

            QPushButton:disabled {{
                color: {theme.text.muted};
                background-color: {theme.surface.muted};
                border-color: {theme.border.muted};
            }}"""
        self.setStyleSheet(style)

        # if self.og_icon is None, then None is passed to set_icon which will remove icon if it exists
        icon = self.og_icon if (not self.tint_icon) or self.og_icon is None else tint_icon(self.og_icon, theme.text.color_hex_argb)
        self._set_icon(icon)
