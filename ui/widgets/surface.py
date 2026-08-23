from PySide6.QtWidgets import QLayout, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from ui.widgets import Widget
from ui.theme import Theme, register_has_theme_and_apply, reapply_theme

from enum import Enum


class SurfaceStyle(Enum):
    REGULAR = 0
    ACCENT = 1

class SurfaceState(Enum):
    NORMAL = 0
    HOVER = 1
    PRESSED = 2

class SurfaceRole(Enum):
    PANEL = 0
    BUTTONLIKE = 1


class Surface(Widget):

    clicked = Signal()
    pressed = Signal()
    released = Signal()

    def __init__(self, 
        surface_style: SurfaceStyle = SurfaceStyle.REGULAR,
        highlight: bool = True,
        role: SurfaceRole = SurfaceRole.PANEL,
        inner_layout_cls: type[QLayout] = QVBoxLayout,
        parent=None
    ):
        super().__init__(parent=parent)
        self.setProperty("surface", True)

        self.surface_style = surface_style
        self.highlight = highlight
        self.role = role
        self.state = SurfaceState.NORMAL

        self.qt_layout: QLayout = inner_layout_cls(self)
        self.setLayout(self.qt_layout)

        self.setAttribute(Qt.WA_StyledBackground, True)
        register_has_theme_and_apply(self)


    # Button stuff

    def enterEvent(self, e):
        if self.role == SurfaceRole.BUTTONLIKE:
            self.set_state(SurfaceState.HOVER)
        super().enterEvent(e)


    def leaveEvent(self, e):
        if self.role == SurfaceRole.BUTTONLIKE:
            self.set_state(SurfaceState.NORMAL)
        super().leaveEvent(e)


    def mousePressEvent(self, e):
        if (
            self.role == SurfaceRole.BUTTONLIKE
            and e.button() == Qt.LeftButton
        ):
            self.set_state(SurfaceState.PRESSED)
            self.pressed.emit()
            e.accept()
            return

        super().mousePressEvent(e)


    def mouseReleaseEvent(self, e):
        if (
            self.role == SurfaceRole.BUTTONLIKE
            and e.button() == Qt.LeftButton
        ):
            inside = self.rect().contains(e.pos())

            self.set_state(
                SurfaceState.HOVER if inside else SurfaceState.NORMAL
            )

            self.released.emit()

            if inside:
                self.clicked.emit()

            e.accept()
            return

        super().mouseReleaseEvent(e)


    # Regular funcs

    def layout(self):
        return self.qt_layout

    def set_surface_style(self, surface_style: SurfaceStyle):
        self.surface_style = surface_style
        reapply_theme(self)

    def set_highlight(self, highlight: bool):
        self.highlight = highlight
        reapply_theme(self)

    def set_widget_content_margins(self, l, t, r, b):
        self.qt_layout.setContentsMargins(l, t, r, b)

    def add_to_widget_content_margins(self, l, t, r, b):
        margins = self.qt_layout.contentsMargins()
        self.qt_layout.setContentsMargins(margins.left()+l, margins.top()+t, margins.right()+r, margins.bottom()+b)

    def set_role(self, role: SurfaceRole):
        self.role = role
        reapply_theme(self)


    def set_state(self, state: SurfaceState):
        if self.state != state:
            self.state = state
            reapply_theme(self)

    def _apply_theme(self, theme: Theme):

        if self.surface_style == SurfaceStyle.ACCENT:
            bg_color = {
                SurfaceState.NORMAL: theme.accent_surface.color,
                SurfaceState.HOVER: theme.accent_surface.color_double,
                SurfaceState.PRESSED: theme.accent_surface.muted,
            }[self.state]
        else:
            bg_color = {
                SurfaceState.NORMAL: theme.surface.color,
                SurfaceState.HOVER: theme.surface.color_double,
                SurfaceState.PRESSED: theme.surface.muted,
            }[self.state]

        border_color = theme.accent_border.color if self.surface_style == SurfaceStyle.ACCENT else theme.border.color

        self.setStyleSheet(f"""
            QWidget[surface] {{
                background-color: {bg_color if self.highlight else '#00000000'};

                border: 2px solid {border_color};
                border-radius: 4px;
            }}
        """)
