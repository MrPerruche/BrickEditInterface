from PySide6.QtWidgets import QLayout, QVBoxLayout
from PySide6.QtCore import Qt, Signal

from ui.widgets import Widget
from ui.theme import Theme, style_rules, set_style_property, theme_manager
from ui.animations.pulse import PulseAnimation, blend_colors

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

        self.danger = PulseAnimation(
            callback=self._danger_changed,
            duration=900,
            parent=self,
        )
        self._danger_enabled = False  # The pulse itself only runs while the surface is shown


    # danger stuff

    def set_danger(self, enabled: bool):
        """Pulses toward the theme's danger colors, like Button.set_danger()"""
        self._danger_enabled = enabled
        # Scopes the own sheet set every frame to this surface: a plain QWidget[surface="true"] selector would
        #  also beat the global rules of the surfaces nested in this one
        self.setProperty("surfaceDanger", enabled)
        if not enabled:
            self.danger.stop()
            self.setStyleSheet("")  # Back to the global rules
        elif self.isVisible():
            self.danger.start()

    def get_danger(self) -> bool:
        return self._danger_enabled

    def showEvent(self, e):
        if self._danger_enabled:
            self.danger.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self.danger.stop()  # Don't restyle every frame while nobody can see it
        super().hideEvent(e)

    def _danger_changed(self, value: float):
        if not self._danger_enabled:
            return
        theme = theme_manager.current()
        accent = self.surface_style == SurfaceStyle.ACCENT
        fill = theme.accent_surface if accent else theme.surface
        border = theme.accent_border if accent else theme.border

        def bg(color: str) -> str:
            return blend_colors(color if self.highlight else "#00000000", theme.danger_surface.color_hex_argb, value)

        sel = 'QWidget[surfaceDanger="true"]'
        self.setStyleSheet(f"""
            {sel} {{
                background-color: {bg(fill.color_hex_argb)};
                border: 2px solid {blend_colors(border.color_hex_argb, theme.danger.color_hex_argb, value)};
                border-radius: 4px;
            }}
            {sel}[surfaceState="hover"] {{ background-color: {bg(fill.color_advanced(2, True))}; }}
            {sel}[surfaceState="pressed"] {{ background-color: {bg(fill.muted_hex_argb)}; }}""")


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
