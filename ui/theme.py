from dataclasses import dataclass
from PySide6.QtGui import QColor
from PySide6.QtCore import QObject, Signal
from typing import Protocol

from systems.settings import settings_manager

def parse_color(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i+2], 16) for i in range(0, 8, 2))


def format_color(c):
    return "#{:02x}{:02x}{:02x}{:02x}".format(*c)


def strongest_overlay(col1, col2):
    """Returns the brightest valid overlay. If no bright overlay exists,
    automatically increases alpha until one does. If impossible, falls back
    to clamping."""

    br, bg, bb, _ = parse_color(col1)
    tr, tg, tb, _ = parse_color(col2)

    bg = (br, bg, bb)
    tgt = (tr, tg, tb)

    alpha = 1 / 255

    # Increase alpha until every channel fits in [0,255]
    for base, target in zip(bg, tgt):
        # Upper bound: overlay <= 255
        if base != 255:
            alpha = max(alpha, (target - base) / (255 - base))

        # Lower bound: overlay >= 0
        if base != 0:
            alpha = max(alpha, (base - target) / base)

    alpha = min(max(alpha, 1 / 255), 1.0)

    a = round(alpha * 255)
    alpha = a / 255.0

    overlay = []
    for base, target in zip(bg, tgt):
        value = (target - (1 - alpha) * base) / alpha
        overlay.append(round(min(255, max(0, value))))

    return format_color((*overlay, a))


def make_muted_color_from_hex(col: str, brightness_mult: float = 0.75) -> str:
    col = col.lstrip('#').rjust(8, 'f')
    r, g, b, a = int(col[:2], 16), int(col[2:4], 16), int(col[4:6], 16), int(col[6:8], 16)
    # OLD:
    # max_cnl = max(r, g, b)
    # r2, g2, b2 = r/2 + max_cnl/4, g/2 + max_cnl/4, b/2 + max_cnl/4

    r2, g2, b2 = (r+128)//2 * brightness_mult, (g+128)//2 * brightness_mult, (b+128)//2 * brightness_mult
    r2, g2, b2 = min(int(r2), 255), min(int(g2), 255), min(int(b2), 255)

    return f"#{r2:02x}{g2:02x}{b2:02x}{a:02x}"


def calculate_alpha_stack(*alpha: int):
    transparency_product = 1
    for a in alpha:
        transparency_product *= (255-a)/255
    return int(255 - 255 * transparency_product)


class ThemeColor:
    def __init__(self, color: str, muted: str | None = None):
        self._r, self._g, self._b, self._a = self._parse_hex(color)
        if muted is not None:
            self._mr, self._mg, self._mb, self._ma = self._parse_hex(muted)
        else:
            self._mr, self._mg, self._mb, self._ma = self._mute(self._r, self._g, self._b, self._a)

        self._color_double = self._stack_alpha_rgba(self._r, self._g, self._b, self._a, 2)
        self._muted_double = self._stack_alpha_rgba(self._mr, self._mg, self._mb, self._ma, 2)

    @staticmethod
    def _parse_hex(col: str) -> tuple[int, int, int, int]:
        col = col.lstrip('#')
        if len(col) == 6:
            col += 'ff'          # default to fully opaque when alpha omitted
        r, g, b, a = int(col[0:2], 16), int(col[2:4], 16), int(col[4:6], 16), int(col[6:8], 16)
        return r, g, b, a

    @staticmethod
    def _mute(r, g, b, a, brightness_mult: float = 0.75) -> tuple[int, int, int, int]:
        r2 = min(int((r + 128) // 2 * brightness_mult), 255)
        g2 = min(int((g + 128) // 2 * brightness_mult), 255)
        b2 = min(int((b + 128) // 2 * brightness_mult), 255)
        return r2, g2, b2, a

    @staticmethod
    def _stack_alpha_rgba(r, g, b, a, times: int) -> str:
        stacked = a
        for _ in range(times - 1):
            stacked = calculate_alpha_stack(stacked, a)
        return f"rgba({r}, {g}, {b}, {stacked})"

    @property
    def color(self) -> str: return f"rgba({self._r}, {self._g}, {self._b}, {self._a})"
    @property
    def color_hex_rgba(self) -> str: return f"#{self._r:02x}{self._g:02x}{self._b:02x}{self._a:02x}"
    @property
    def color_hex_argb(self) -> str: return f"#{self._a:02x}{self._r:02x}{self._g:02x}{self._b:02x}"
    @property
    def color_qcolor(self) -> QColor: return QColor(self._r, self._g, self._b, self._a)

    @property
    def muted(self) -> str: return f"rgba({self._mr}, {self._mg}, {self._mb}, {self._ma})"
    @property
    def muted_hex_rgba(self) -> str: return f"#{self._mr:02x}{self._mg:02x}{self._mb:02x}{self._ma:02x}"
    @property
    def muted_hex_argb(self) -> str: return f"#{self._ma:02x}{self._mr:02x}{self._mg:02x}{self._mb:02x}"
    @property
    def muted_qcolor(self) -> QColor: return QColor(self._mr, self._mg, self._mb, self._ma)

    @property
    def color_double(self) -> str:
        """Color whose transparency is adjusted to simulate being applied twice"""
        return self._color_double

    @property
    def muted_double(self) -> str:
        """Muted color whose transparency is adjusted to simulate being applied twice"""
        return self._muted_double

    def color_advanced(self, alpha_stack: int = 1, hex: bool = False):
        alpha = calculate_alpha_stack(*[self._a for _ in range(alpha_stack)]) if alpha_stack != 1 else self._a
        if hex:
            return f"#{alpha:02x}{self._r:02x}{self._g:02x}{self._b:02x}"
        else:
            return f"rgba({self._r}, {self._g}, {self._b}, {alpha})"

    def color_qcolor_advenced(self, alpha_stack: int = 1):
        alpha = calculate_alpha_stack(*[self._a for _ in range(alpha_stack)]) if alpha_stack != 1 else self._a
        return QColor(self._r, self._g, self._b, alpha)

    def muted_advanced(self, alpha_stack: int = 1, hex: bool = False):
        alpha = calculate_alpha_stack(*[self._ma for _ in range(alpha_stack)]) if alpha_stack != 1 else self._ma
        if hex:
            return f"#{alpha:02x}{self._mr:02x}{self._mg:02x}{self._mb:02x}"
        else:
            return f"rgba({self._mr}, {self._mg}, {self._mb}, {alpha})"

    def muted_qcolor_advenced(self, alpha_stack: int = 1):
        alpha = calculate_alpha_stack(*[self._ma for _ in range(alpha_stack)]) if alpha_stack != 1 else self._ma
        return QColor(self._mr, self._mg, self._mb, alpha)


@dataclass(frozen=True)
class Theme:
    name: str
    display_name: str
    is_highcontrast: bool

    background: ThemeColor
    sidebar: ThemeColor
    surface: ThemeColor
    border: ThemeColor
    text: ThemeColor
    accent: ThemeColor
    accent_surface: ThemeColor
    accent_border: ThemeColor
    danger: ThemeColor
    danger_surface: ThemeColor
    danger_border: ThemeColor

    base: ThemeColor = ThemeColor("#ffffffff")


DARK = Theme(name="dark", display_name="Dark theme", is_highcontrast=False,
    background=ThemeColor("#101420ff"),
    sidebar=ThemeColor("#1b2238ff"),
    surface=ThemeColor("#80809030"),
    border=ThemeColor("#5b5b64ff"),
    text=ThemeColor("#f8ebe0ff"),
    accent=ThemeColor("#dd4433ff"),
    accent_surface=ThemeColor("#dd443350"),
    accent_border=ThemeColor("#ff8866ff"),
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
LIGHT = Theme(name="light", display_name="Light theme", is_highcontrast=False,
    background = ThemeColor("#ebe9e7ff"),
    sidebar=ThemeColor("#dddbd8ff"),
    surface=ThemeColor("#ffffff80", "#80808040"),
    border=ThemeColor("#b8b4b0ff"),
    text=ThemeColor("#303660ff", "#64677aff"),
    accent=ThemeColor("#ee5544ff"),
    accent_surface=ThemeColor("#dd443350"),
    accent_border=ThemeColor("#aa3322ff"),
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
NIGHT = Theme(name="night", display_name="Night theme", is_highcontrast=False,
    background = ThemeColor("#000000ff"),
    sidebar=ThemeColor("#000000ff"),
    surface=ThemeColor("#60607840"),
    border=ThemeColor("#4b4b50ff"),
    text=ThemeColor("#f8ebe0ff"),
    accent=ThemeColor("#dd4433ff"),
    accent_surface=ThemeColor("#dd443350"),
    accent_border=ThemeColor("#ff8866ff"),
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
HIGH_CONTRAST = Theme(name="highcontrast", display_name="High contrast theme", is_highcontrast=True,
    background=ThemeColor("#000000ff"),
    sidebar=ThemeColor("#000000ff"),
    surface=ThemeColor("#ffffff20"),
    border=ThemeColor("#ffffffff"),
    text=ThemeColor("#ffffffff"),
    accent=ThemeColor("#dd4433ff"),
    accent_surface=ThemeColor("#dd443350"),
    accent_border=ThemeColor("#ffc0b8ff"),
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)

BR_DEFAULT = Theme(name="br_default", display_name="BR Default theme", is_highcontrast=False,
    background=ThemeColor("#222327ff"),  # SRC: Basic widget background
    sidebar=ThemeColor("#323439ff"),  # SRC: Value input background
    surface=ThemeColor(strongest_overlay("#222327ff", "#323439ff")),  # Background -> Sidebar
    border=ThemeColor("#484a51ff"),  # SRC: Widget corner. Careful to pick the brightest color, incorrect can be off by 1
    text=ThemeColor("#edededff"),  # SRC: Average text color
    accent=ThemeColor("#a96520ff"),  # SRC: Accent button background
    accent_surface=ThemeColor(strongest_overlay("#323439ff", "#7b4815ff")),  # SRC: Sidebar → Muted widget accent background (eg. saved creation name label background)
    accent_border=ThemeColor("#e68b30"),  # SRC: Accent widget corner. Careful, like for border.
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
BR_BLUE = Theme(name="br_blue", display_name="BR Blue theme", is_highcontrast=False,
    background=ThemeColor("#2a3978ff"),  # SRC: Basic widget background
    sidebar=ThemeColor("#3c50a5ff"),  # SRC: Value input background
    surface=ThemeColor(strongest_overlay("#2a3978ff", "#3c50a5ff")),  # Background -> Sidebar
    border=ThemeColor("#5570e1ff"),  # SRC: Widget corner. Careful to pick the brightest color, incorrect can be off by 1
    text=ThemeColor("#edededff"),  # SRC: Average text color
    accent=ThemeColor("#a96520ff"),  # SRC: Accent button background
    accent_surface=ThemeColor(strongest_overlay("#3c50a5ff", "#7b4815ff")),  # SRC: Sidebar → Muted widget accent background (eg. saved creation name label background)
    accent_border=ThemeColor("#e68b30ff"),  # SRC: Accent widget corner. Careful, like for border.
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
BR_CYAN = Theme(name="br_cyan", display_name="BR Cyan theme", is_highcontrast=False,
    background=ThemeColor("#2a5749ff"),  # SRC: Basic widget background
    sidebar=ThemeColor("#3c7966ff"),  # SRC: Value input background
    surface=ThemeColor(strongest_overlay("#2a5749ff", "#3c7966ff")),  # Background -> Sidebar
    border=ThemeColor("#55a68dff"),  # SRC: Widget corner. Careful to pick the brightest color, incorrect can be off by 1
    text=ThemeColor("#edededff"),  # SRC: Average text color
    accent=ThemeColor("#a96520ff"),  # SRC: Accent button background
    accent_surface=ThemeColor(strongest_overlay("#3c7966ff", "#7b4815ff")),  # SRC: Sidebar → Muted widget accent background (eg. saved creation name label background)
    accent_border=ThemeColor("#e68b30ff"),  # SRC: Accent widget corner. Careful, like for border.
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
BR_GRAY = Theme(name="br_gray", display_name="BR Gray theme", is_highcontrast=False,
    background=ThemeColor("#4d4d4dff"),  # SRC: Basic widget background
    sidebar=ThemeColor("#6c6c6cff"),  # SRC: Value input background
    surface=ThemeColor(strongest_overlay("#4d4d4dff", "#6c6c6cff")),  # Background -> Sidebar
    border=ThemeColor("#959595ff"),  # SRC: Widget corner. Careful to pick the brightest color, incorrect can be off by 1
    text=ThemeColor("#edededff"),  # SRC: Average text color
    accent=ThemeColor("#a96520ff"),  # SRC: Accent button background
    accent_surface=ThemeColor(strongest_overlay("#6c6c6cff", "#7b4815ff")),  # SRC: Sidebar → Muted widget accent background (eg. saved creation name label background)
    accent_border=ThemeColor("#e68b30ff"),  # SRC: Accent widget corner. Careful, like for border.
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
BR_ORANGE = Theme(name="br_orange", display_name="BR Orange theme", is_highcontrast=False,
    background=ThemeColor("#7b4815ff"),  # SRC: Basic widget background
    sidebar=ThemeColor("#a96520ff"),  # SRC: Value input background
    surface=ThemeColor(strongest_overlay("#7b4815ff", "#a96520ff")),  # Background -> Sidebar
    border=ThemeColor("#e68b30ff"),  # SRC: Widget corner. Careful to pick the brightest color, incorrect can be off by 1
    text=ThemeColor("#edededff"),  # SRC: Average text color
    accent=ThemeColor("#bc8100ff"),  # SRC: Accent button background
    accent_surface=ThemeColor(strongest_overlay("#a96520ff", "#895d00ff")),  # SRC: Sidebar → Muted widget accent background (eg. saved creation name label background)
    accent_border=ThemeColor("#ffb100ff"),  # SRC: Accent widget corner. Careful, like for border.
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)
BR_VIOLET = Theme(name="br_violet", display_name="BR Violet theme", is_highcontrast=False,
    background=ThemeColor("#32033aff"),
    sidebar=ThemeColor("#470753ff"),
    surface=ThemeColor("#d422fb21"),
    border=ThemeColor("#640d73ff"),
    text=ThemeColor("#edededff"),
    accent=ThemeColor("#914aa2ff"),
    accent_surface=ThemeColor("#eee4ff34"),
    accent_border=ThemeColor("#c668ddff"),
    # accent=ThemeColor("#dd4433ff"),
    # accent_surface=ThemeColor("#dd443350"),
    # accent_border=ThemeColor("#ff8866ff"),
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)

DEV_TEST = Theme(name="dev", display_name="Debug theme", is_highcontrast=False,
    background=ThemeColor("#000040ff"),
    sidebar=ThemeColor("#000080ff"),
    surface=ThemeColor("#8080ff30"),
    border=ThemeColor("#8080ffff"),
    text=ThemeColor("#ffff80ff"),
    accent=ThemeColor("#dd4433ff"),
    accent_surface=ThemeColor("#dd443350"),
    accent_border=ThemeColor("#ff8866ff"),
    danger=ThemeColor("#ee2830ff"),
    danger_surface=ThemeColor("#ee283050"),
    danger_border=ThemeColor("#ac191eff")
)

class ThemeManager(QObject):
    theme_changed = Signal(object)  # emits a Theme
    themes = (
        DARK, LIGHT, NIGHT, HIGH_CONTRAST,
        BR_DEFAULT, BR_BLUE, BR_CYAN, BR_GRAY, BR_ORANGE, BR_VIOLET,
        DEV_TEST
    )

    def __init__(self):
        super().__init__()

        self._current = DARK
        self.set_theme_from_name(settings_manager.theme)

    def current(self) -> Theme:
        """Returns current theme object."""
        return self._current

    def current_idx(self) -> int:
        try:
            return self.themes.index(self._current)
        except ValueError:
            return 0

    def set_theme(self, theme: Theme) -> None:
        """Sets current theme and update all widgets."""
        self._current = theme
        settings_manager.theme = theme.name
        settings_manager.save()
        self.theme_changed.emit(theme)

    def set_theme_from_name(self, name: str) -> None:
        for theme in self.themes:
            if theme.name != name:
                continue
            self.set_theme(theme)

theme_manager = ThemeManager()


class SupportsTheme(Protocol):
    def _apply_theme(self, theme: Theme) -> None:
        ...

def reapply_theme(target: SupportsTheme):
    target._apply_theme(theme_manager.current())

def repolish(target):
    target.style().unpolish(target)
    target.style().polish(target)

def register_has_theme_and_apply(target: SupportsTheme, theme_manager: Theme = theme_manager):
    """Registers anything which supports themes """
    theme_manager.theme_changed.connect(target._apply_theme)
    target._apply_theme(theme_manager.current())

def unregister(target: SupportsTheme, theme_manager: Theme = theme_manager):
    theme_manager.theme_changed.disconnect(target._apply_theme)
