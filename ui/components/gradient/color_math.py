"""
color_math.py -- gradient interpolation, zero Qt-widget dependencies.

Everything here only ever touches QColor (a value type, not a widget), plus
plain Python floats/dataclasses. Nothing in this file draws, receives
events, or needs a running QApplication -- it's safe to unit-test on its
own, and safe to keep even if bar.py / editor.py get replaced wholesale.

Requires ``coloraide`` (already a project dependency -- see the old
menus/gradient_maker/gradient_maker.py, which used it directly).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import count
from typing import NamedTuple

from PySide6.QtGui import QColor
from coloraide import Color


# --------------------------------------------------------------------------- #
# Color spaces
# --------------------------------------------------------------------------- #

class ColorSpace(NamedTuple):
    label: str          # shown in the combo box
    code: str           # coloraide space name, or the literal "hsv"
    hue_capable: bool    # whether "longer hue" toggling means anything for it


# CSS Color 4 calls this axis "hue interpolation method: shorter | longer
# hue" -- same idea as this module's `long_hue` flag, just scoped to
# whichever of these five spaces actually has a hue angle to go around.
DEFAULT_SPACES: list[ColorSpace] = [
    ColorSpace("OKLAB", "oklab", False),
    ColorSpace("OKLCH", "oklch", True),
    ColorSpace("Linear RGB", "srgb-linear", False),
    ColorSpace("sRGB", "srgb", False),
    ColorSpace("HSV", "hsv", True),
]


def _lerp(t: float, a: float, b: float) -> float:
    return a + (b - a) * t


def _lerp_hue(t: float, h1: float, h2: float, *, long_hue: bool, period: float = 360.0) -> float:
    """Interpolate an angle from h1 to h2 (same units, any range)."""
    d = (h2 - h1) % period
    if not long_hue:
        if d > period / 2:
            d -= period
    else:
        if d < period / 2:
            d -= period
    return (h1 + t * d) % period


def interpolate_color(t: float, c1: QColor, c2: QColor, space: ColorSpace, long_hue: bool = False) -> QColor:
    """Blend c1 -> c2 at t in [0, 1] in the given color space."""
    alpha = _lerp(t, c1.alphaF(), c2.alphaF())

    if space.code == "hsv":
        h1, s1, v1, _ = c1.getHsvF()
        h2, s2, v2, _ = c2.getHsvF()
        # Qt reports hue == -1 for achromatic (fully desaturated) colors.
        if h1 < 0:
            h1 = h2 if h2 >= 0 else 0.0
        if h2 < 0:
            h2 = h1
        h = _lerp_hue(t, h1 * 360.0, h2 * 360.0, long_hue=long_hue) / 360.0
        out = QColor.fromHsvF(h % 1.0, _lerp(t, s1, s2), _lerp(t, v1, v2))
        out.setAlphaF(max(0.0, min(1.0, alpha)))
        return out

    ca = Color("srgb", [c1.redF(), c1.greenF(), c1.blueF()])
    cb = Color("srgb", [c2.redF(), c2.greenF(), c2.blueF()])

    if space.code == "oklch":
        L1, C1v, H1 = ca.convert("oklch").coords()
        L2, C2v, H2 = cb.convert("oklch").coords()
        # Achromatic stops report a NaN hue; borrow the other stop's hue so
        # the gradient doesn't try to blend through an undefined angle.
        if math.isnan(H1):
            H1 = H2 if not math.isnan(H2) else 0.0
        if math.isnan(H2):
            H2 = H1
        L = _lerp(t, L1, L2)
        Cc = _lerp(t, C1v, C2v)
        H = _lerp_hue(t, H1, H2, long_hue=long_hue)
        out_c = Color("oklch", [L, Cc, H]).convert("srgb")
    else:
        p1 = ca.convert(space.code).coords()
        p2 = cb.convert(space.code).coords()
        mixed = [_lerp(t, x, y) for x, y in zip(p1, p2)]
        out_c = Color(space.code, mixed).convert("srgb")

    r, g, b = out_c.coords()
    out = QColor.fromRgbF(min(1.0, max(0.0, r)), min(1.0, max(0.0, g)), min(1.0, max(0.0, b)))
    out.setAlphaF(max(0.0, min(1.0, alpha)))
    return out


# --------------------------------------------------------------------------- #
# Stops
# --------------------------------------------------------------------------- #

_id_counter = count()


@dataclass
class ColorStop:
    position: float           # 0..100
    color: QColor
    id: int = field(default_factory=lambda: next(_id_counter))


def sample_gradient(stops: list[ColorStop], t: float, space: ColorSpace, long_hue: bool = False) -> QColor:
    """stops must already be sorted by position ascending. t in [0, 100]."""
    if t <= stops[0].position:
        return QColor(stops[0].color)
    if t >= stops[-1].position:
        return QColor(stops[-1].color)
    for i in range(1, len(stops)):
        a, b = stops[i - 1], stops[i]
        if t <= b.position:
            span = b.position - a.position
            local_t = 0.0 if span <= 0 else (t - a.position) / span
            return interpolate_color(local_t, a.color, b.color, space, long_hue)
    return QColor(stops[-1].color)  # pragma: no cover - unreachable
