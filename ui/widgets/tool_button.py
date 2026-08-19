from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QToolButton, QSizePolicy, QVBoxLayout

from ui.widgets.widget import Widget
from ui.theme import Theme, register_has_theme_and_apply, reapply_theme

from utils import tint_icon


class ToolButton(Widget):

    def __init__(self, icon: QIcon | None = None, tint_icon: bool = False, muted = False, parent=None):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.qt_widget = QToolButton()
        self._layout.addWidget(self.qt_widget)

        self.clicked = self.qt_widget.clicked
        self.toggled = self.qt_widget.toggled

        self.qt_widget.setAutoRaise(False)
        self.qt_widget.setToolButtonStyle(
            Qt.ToolButtonIconOnly
        )

        self.qt_widget.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        self.og_icon = icon
        self.tint_icon = tint_icon
        self.muted = muted
        self.enabled = True
        self.set_button_size(26)
        
        register_has_theme_and_apply(self)

    def set_icon(self, icon: QIcon | None):
        if icon is None:
            self.qt_widget.setIcon(QIcon())
        else:
            self.og_icon = icon
            reapply_theme(self)

    def set_icon_from_theme(self, *names: str):
        for name in names:
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                self.qt_widget.setIcon(icon)
                return True
        return False

    def set_button_size(self, size: int):
        self.qt_widget.setFixedSize(size, size)
        self.qt_widget.setIconSize(QSize(size - 8, size - 8))


    def is_muted(self) -> bool:
        return self.muted

    def set_muted(self, muted):
        if muted != self.muted:
            self.muted = muted
            reapply_theme(self)


    def set_enabled(self, enabled: bool):
        if enabled != self.enabled:
            self.enabled = enabled
            self.qt_widget.setEnabled(enabled)
            reapply_theme(self)


    def set_checkable(self, checkable: bool):
        self.qt_widget.setCheckable(checkable)

    def set_checked(self, checked: bool):
        self.qt_widget.setChecked(checked)

    def is_checked(self) -> bool:
        return self.qt_widget.isChecked()


    def _apply_theme(self, theme: Theme):
    
        self.setStyleSheet(f"""
        QToolButton {{
            color: {theme.text.color};
            background-color: {theme.surface.color};

            border: 2px solid {theme.border.color};
            border-radius: 4px;

            padding: 1px 4px;

            font-size: 13pt;
        }}

        QToolButton:hover {{
            background-color: {theme.surface.color_double};
            border-color: {theme.border.color};
        }}

        QToolButton:pressed {{
            background-color: {theme.surface.muted};
        }}

        QToolButton:checked {{
            background-color: {theme.accent.color};
            border-color: {theme.accent_border.color};
        }}

        QToolButton:disabled {{
            color: {theme.text.muted};
            background-color: {theme.surface.muted};
            border-color: {theme.border.muted};
        }}""")
            
        # if self.og_icon is None, then None is passed to set_icon which will remove icon if it exists
        icon = self.og_icon if (not self.tint_icon) or self.og_icon is None else tint_icon(self.og_icon, theme.text.color_hex_argb)

        if self.muted or not self.enabled:
            icon = tint_icon(icon, theme.base.muted_hex_argb)

        self.qt_widget.setIcon(icon)
