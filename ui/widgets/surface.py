from PySide6.QtWidgets import QLayout, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from ui.widgets import Widget
from ui.theme import Theme, style_rules, set_style_property

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


@style_rules
def _surface_rules(theme: Theme) -> str:
    # Selected by the properties Surface keeps up to date: surface, surfaceStyle (regular|accent),
    #  surfaceHighlight (bool) and surfaceState (normal|hover|pressed). Base rule = no highlight.
    def fills(style: str, color) -> str:
        sel = f'QWidget[surface="true"][surfaceStyle="{style}"][surfaceHighlight=true]'
        return f"""
        {sel} {{ background-color: {color.color}; }}
        {sel}[surfaceState="hover"] {{ background-color: {color.color_double}; }}
        {sel}[surfaceState="pressed"] {{ background-color: {color.muted}; }}"""

    return f"""
        QWidget[surface="true"] {{
            background-color: #00000000;
            border: 2px solid {theme.border.color};
            border-radius: 4px;
        }}
        QWidget[surface="true"][surfaceStyle="accent"] {{
            border-color: {theme.accent_border.color};
        }}""" + fills("regular", theme.surface) + fills("accent", theme.accent_surface)


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
        self.setProperty("surface", True)  # Look is done by _surface_rules through these properties

        self.surface_style = surface_style
        self.highlight = highlight
        self.role = role
        self.state = SurfaceState.NORMAL
        self.setProperty("surfaceStyle", surface_style.name.lower())
        self.setProperty("surfaceHighlight", highlight)
        self.setProperty("surfaceState", self.state.name.lower())

        self.qt_layout: QLayout = inner_layout_cls(self)
        self.setLayout(self.qt_layout)

        self.setAttribute(Qt.WA_StyledBackground, True)


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
        set_style_property(self, "surfaceStyle", surface_style.name.lower())

    def set_highlight(self, highlight: bool):
        self.highlight = highlight
        set_style_property(self, "surfaceHighlight", highlight)

    def set_widget_content_margins(self, l, t, r, b):
        self.qt_layout.setContentsMargins(l, t, r, b)

    def add_to_widget_content_margins(self, l, t, r, b):
        margins = self.qt_layout.contentsMargins()
        self.qt_layout.setContentsMargins(margins.left()+l, margins.top()+t, margins.right()+r, margins.bottom()+b)

    def set_role(self, role: SurfaceRole):
        self.role = role


    def set_state(self, state: SurfaceState):
        if self.state != state:
            self.state = state
            set_style_property(self, "surfaceState", state.name.lower())
