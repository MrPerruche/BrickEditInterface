"""
gradient_bar.py — interactive, draggable gradient-stop bar for PySide6.

Meant as a drop-in replacement for
    menus/shared_widgets/multi_color_selector.py (MultiColorSelectorWidget)
in a `ui/`-style rewrite. It keeps the same read API the old widget had
(``get_colors_pos`` / ``get_colors``) so ``menus/gradient_maker/gradient_maker.py``
can swap the widget without touching ``create_vehicle()``.

Only dependency beyond PySide6 is ``coloraide``, which the project already
uses in gradient_maker.py.

Two classes matter to callers:

    GradientBar     -- the bar itself: paints the live gradient preview and
                        the draggable stop handles. Usable standalone.

    GradientEditor   -- GradientBar + a color-space combo box + a small
                        "selected stop" details row (swatch, position spin,
                        remove button). This is the one you probably want
                        in the menu, as a drop-in for MultiColorSelectorWidget.

Interaction model (mirrors GIMP / Photoshop gradient editors):
    - Drag a handle left/right to reposition it, anywhere in [0, 100].
    - Double-click empty space on the bar to insert a new stop there,
      pre-filled with the color the gradient already had at that point.
    - Double-click a handle to open a color picker for it.
    - Right-click a handle, or select it and press Delete/Backspace, to
      remove it (at least 2 stops are always kept).
    - Click a handle to select it; its details show in GradientEditor's
      bottom row for precise numeric editing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import count
from typing import NamedTuple, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from coloraide import Color

# Reuse the project's rounded-square base widget for consistent styling if
# it's importable; otherwise fall back to a plain QWidget so this file also
# runs standalone (see the __main__ demo at the bottom).
try:
    from menus.shared_widgets.square_widget import SquareWidget as _BaseWidget
except ImportError:  # pragma: no cover - fallback for standalone use
    _BaseWidget = QWidget


# --------------------------------------------------------------------------- #
# Color-space interpolation modes
# --------------------------------------------------------------------------- #

class InterpMode(NamedTuple):
    label: str
    space: str          # coloraide space name, or "hsv" (handled via QColor)
    long_arc: bool       # take the long way around the hue wheel


DEFAULT_MODES: list[InterpMode] = [
    InterpMode("OKLAB", "oklab", False),
    InterpMode("OKLCH", "oklch", False),
    InterpMode("OKLCH (longer hue)", "oklch", True),
    InterpMode("Linear RGB", "srgb-linear", False),
    InterpMode("sRGB", "srgb", False),
    InterpMode("HSV", "hsv", False),
    InterpMode("HSV (longer hue)", "hsv", True),
]


def _lerp(t: float, a: float, b: float) -> float:
    return a + (b - a) * t


def _lerp_hue(t: float, h1: float, h2: float, *, long_arc: bool, period: float = 360.0) -> float:
    """Interpolate an angle between h1 and h2 (same units, any range)."""
    d = (h2 - h1) % period
    if not long_arc:
        if d > period / 2:
            d -= period
    else:
        if d < period / 2:
            d -= period
    return (h1 + t * d) % period


def interpolate_color(t: float, c1: QColor, c2: QColor, mode: InterpMode) -> QColor:
    """Blend c1 -> c2 at t in [0, 1] in the given color space."""
    alpha = _lerp(t, c1.alphaF(), c2.alphaF())

    if mode.space == "hsv":
        h1, s1, v1, _ = c1.getHsvF()
        h2, s2, v2, _ = c2.getHsvF()
        # Qt reports hue == -1 for achromatic (fully desaturated) colors.
        if h1 < 0:
            h1 = h2 if h2 >= 0 else 0.0
        if h2 < 0:
            h2 = h1
        h = _lerp_hue(t, h1 * 360.0, h2 * 360.0, long_arc=mode.long_arc) / 360.0
        out = QColor.fromHsvF(h % 1.0, _lerp(t, s1, s2), _lerp(t, v1, v2))
        out.setAlphaF(max(0.0, min(1.0, alpha)))
        return out

    ca = Color("srgb", [c1.redF(), c1.greenF(), c1.blueF()])
    cb = Color("srgb", [c2.redF(), c2.greenF(), c2.blueF()])

    if mode.space == "oklch":
        L1, C1v, H1 = ca.convert("oklch").coords()
        L2, C2v, H2 = cb.convert("oklch").coords()
        # Achromatic stops report a NaN hue; borrow the other stop's hue
        # so the gradient doesn't blend through undefined angles.
        if math.isnan(H1):
            H1 = H2 if not math.isnan(H2) else 0.0
        if math.isnan(H2):
            H2 = H1
        L = _lerp(t, L1, L2)
        Cc = _lerp(t, C1v, C2v)
        H = _lerp_hue(t, H1, H2, long_arc=mode.long_arc)
        out_c = Color("oklch", [L, Cc, H]).convert("srgb")
    else:
        p1 = ca.convert(mode.space).coords()
        p2 = cb.convert(mode.space).coords()
        mixed = [_lerp(t, x, y) for x, y in zip(p1, p2)]
        out_c = Color(mode.space, mixed).convert("srgb")

    r, g, b = out_c.coords()
    out = QColor.fromRgbF(min(1.0, max(0.0, r)), min(1.0, max(0.0, g)), min(1.0, max(0.0, b)))
    out.setAlphaF(max(0.0, min(1.0, alpha)))
    return out


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

_id_counter = count()


@dataclass
class ColorStop:
    position: float           # 0..100
    color: QColor
    id: int = field(default_factory=lambda: next(_id_counter))


def sample_gradient(stops: list[ColorStop], t: float, mode: InterpMode) -> QColor:
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
            return interpolate_color(local_t, a.color, b.color, mode)
    return QColor(stops[-1].color)  # pragma: no cover - unreachable


# --------------------------------------------------------------------------- #
# The bar
# --------------------------------------------------------------------------- #

class GradientBar(_BaseWidget):
    """A horizontal bar showing a live gradient preview with draggable stops."""

    MIN_STOPS = 2
    MAX_STOPS = 32

    stopsChanged = Signal()           # any add/remove/move/recolor
    selectionChanged = Signal(object)  # ColorStop | None
    modeChanged = Signal(object)      # InterpMode

    BAR_HEIGHT = 32
    HANDLE_R = 7
    HANDLE_R_SELECTED = 9
    HANDLE_GAP = 6           # vertical gap between bar and handle row

    def __init__(self, stops: Optional[list[ColorStop]] = None, parent=None):
        super().__init__(parent)

        self._mode: InterpMode = DEFAULT_MODES[0]
        self._stops: list[ColorStop] = stops or [
            ColorStop(0.0, QColor(16, 16, 204)),
            ColorStop(100.0, QColor(204, 16, 32)),
        ]
        self._selected_id: Optional[int] = self._stops[0].id

        self._drag_id: Optional[int] = None
        self._dragging = False

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(self._total_height())

        self._checker_brush = self._make_checker_brush()

    # -- public data API (mirrors the old MultiColorSelectorWidget) -------- #

    def get_colors_pos(self) -> list[tuple[QColor, float]]:
        """Same shape as the widget it replaces: [(QColor, position 0-100), ...]."""
        return [(QColor(s.color), s.position) for s in self._sorted_stops()]

    def get_colors(self) -> list[QColor]:
        return [QColor(s.color) for s in self._sorted_stops()]

    def set_colors_pos(self, values: list[tuple[QColor, float]]) -> None:
        if len(values) < self.MIN_STOPS:
            raise ValueError(f"need at least {self.MIN_STOPS} stops")
        self._stops = [ColorStop(float(pos), QColor(col)) for col, pos in values]
        self._selected_id = self._stops[0].id
        self._drag_id = None
        self._refresh()

    # -- mode ---------------------------------------------------------------

    def mode(self) -> InterpMode:
        return self._mode

    def set_mode(self, mode: InterpMode) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self.modeChanged.emit(mode)
        self._refresh()

    # -- stop manipulation ---------------------------------------------------

    def selected_stop(self) -> Optional[ColorStop]:
        return self._find(self._selected_id)

    def add_stop(self, position: Optional[float] = None, color: Optional[QColor] = None) -> Optional[ColorStop]:
        if len(self._stops) >= self.MAX_STOPS:
            return None
        stops = self._sorted_stops()
        if position is None:
            position = (stops[0].position + stops[-1].position) / 2.0
        position = max(0.0, min(100.0, position))
        if color is None:
            color = sample_gradient(stops, position, self._mode)
        stop = ColorStop(position, QColor(color))
        self._stops.append(stop)
        self._selected_id = stop.id
        self._refresh()
        return stop

    def remove_stop(self, stop: ColorStop) -> None:
        if len(self._stops) <= self.MIN_STOPS:
            return
        self._stops = [s for s in self._stops if s.id != stop.id]
        if self._selected_id == stop.id:
            self._selected_id = self._sorted_stops()[0].id
        self._refresh()

    def remove_selected(self) -> None:
        stop = self.selected_stop()
        if stop is not None:
            self.remove_stop(stop)

    def set_stop_color(self, stop: ColorStop, color: QColor) -> None:
        stop.color = QColor(color)
        self._refresh()

    def set_stop_position(self, stop: ColorStop, position: float) -> None:
        stop.position = max(0.0, min(100.0, position))
        self._refresh()

    # -- geometry helpers ------------------------------------------------- #

    def _sorted_stops(self) -> list[ColorStop]:
        return sorted(self._stops, key=lambda s: s.position)

    def _find(self, stop_id: Optional[int]) -> Optional[ColorStop]:
        if stop_id is None:
            return None
        for s in self._stops:
            if s.id == stop_id:
                return s
        return None

    def _total_height(self) -> int:
        return self.BAR_HEIGHT + self.HANDLE_GAP + 2 * self.HANDLE_R_SELECTED + 2

    def _bar_rect(self) -> QRectF:
        margin = self.HANDLE_R_SELECTED + 1
        return QRectF(margin, 1, max(1.0, self.width() - 2 * margin), self.BAR_HEIGHT)

    def _pos_to_x(self, position: float) -> float:
        bar = self._bar_rect()
        return bar.left() + bar.width() * (position / 100.0)

    def _x_to_pos(self, x: float) -> float:
        bar = self._bar_rect()
        if bar.width() <= 0:
            return 0.0
        t = (x - bar.left()) / bar.width()
        return max(0.0, min(100.0, t * 100.0))

    def _handle_center(self, stop: ColorStop) -> QPointF:
        bar = self._bar_rect()
        r = self.HANDLE_R_SELECTED if stop.id == self._selected_id else self.HANDLE_R
        return QPointF(self._pos_to_x(stop.position), bar.bottom() + self.HANDLE_GAP + r)

    def _hit_test(self, pos: QPointF) -> Optional[ColorStop]:
        best, best_d = None, 1e9
        for stop in self._stops:
            c = self._handle_center(stop)
            d = (c - pos).manhattanLength()
            if d < best_d:
                best, best_d = stop, d
        if best is not None and best_d <= (self.HANDLE_R_SELECTED + 4) * 2:
            return best
        return None

    # -- painting ----------------------------------------------------------- #

    @staticmethod
    def _make_checker_brush() -> QBrush:
        size = 8
        pm = QPixmap(size * 2, size * 2)
        pm.fill(QColor(210, 210, 210))
        p = QPainter(pm)
        p.fillRect(0, 0, size, size, QColor(150, 150, 150))
        p.fillRect(size, size, size, size, QColor(150, 150, 150))
        p.end()
        return QBrush(pm)

    def _refresh(self) -> None:
        self.stopsChanged.emit()
        self.selectionChanged.emit(self.selected_stop())
        self.update()

    def _build_preview_image(self, samples: int) -> QImage:
        stops = self._sorted_stops()
        img = QImage(max(2, samples), 1, QImage.Format_ARGB32_Premultiplied)
        for i in range(img.width()):
            t = 100.0 * i / (img.width() - 1)
            img.setPixelColor(i, 0, sample_gradient(stops, t, self._mode))
        return img

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        bar = self._bar_rect()
        path = QPainterPath()
        path.addRoundedRect(bar, 5, 5)

        has_alpha = any(s.color.alphaF() < 1.0 for s in self._stops)

        painter.save()
        painter.setClipPath(path)
        if has_alpha:
            painter.fillRect(bar, self._checker_brush)

        # Fewer samples while actively dragging keeps drag-repaint cheap;
        # a full-resolution pass happens as soon as the drag ends.
        max_samples = 90 if self._dragging else 220
        samples = max(2, min(max_samples, int(bar.width())))
        image = self._build_preview_image(samples)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(bar, image)
        painter.restore()

        pal = self.palette()
        painter.setPen(QPen(pal.color(QPalette.Mid), 1))
        painter.drawPath(path)

        # Handles: draw unselected first, selected last so its ring is on top.
        stops = self._sorted_stops()
        selected = self.selected_stop()
        for stop in stops:
            if stop.id != self._selected_id:
                self._paint_handle(painter, stop, False)
        if selected is not None:
            self._paint_handle(painter, selected, True)

    def _paint_handle(self, painter: QPainter, stop: ColorStop, selected: bool) -> None:
        pal = self.palette()
        c = self._handle_center(stop)
        r = self.HANDLE_R_SELECTED if selected else self.HANDLE_R

        ring = pal.color(QPalette.Highlight) if selected else pal.color(QPalette.Light)
        painter.setPen(QPen(ring, 2.5 if selected else 1.5))
        painter.setBrush(QBrush(stop.color))
        painter.drawEllipse(c, r, r)

        if stop.color.alphaF() < 0.999:
            # Small alpha hint: draw a checker sliver clipped to the circle.
            clip = QPainterPath()
            clip.addEllipse(c, r, r)
            painter.save()
            painter.setClipPath(clip)
            painter.setOpacity(1.0 - stop.color.alphaF())
            painter.fillRect(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), self._checker_brush)
            painter.restore()

    # -- mouse / keyboard ----------------------------------------------------- #

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position() if hasattr(event, "position") else event.localPos()
        hit = self._hit_test(pos)

        if event.button() == Qt.RightButton:
            if hit is not None:
                self.remove_stop(hit)
            return

        if event.button() != Qt.LeftButton:
            return

        if hit is not None:
            self._selected_id = hit.id
            self._drag_id = hit.id
            self._dragging = True
            self._refresh()
            return

        # Clicked empty space: just deselect-to-bar-position, no stop added
        # (double-click adds one -- see mouseDoubleClickEvent).
        self.setFocus(Qt.MouseFocusReason)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_id is None:
            return
        pos = event.position() if hasattr(event, "position") else event.localPos()
        stop = self._find(self._drag_id)
        if stop is None:
            return
        stop.position = self._x_to_pos(pos.x())
        self._refresh()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_id is not None:
            self._drag_id = None
            self._dragging = False
            self.update()  # one full-resolution repaint now that dragging stopped

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pos = event.position() if hasattr(event, "position") else event.localPos()
        hit = self._hit_test(pos)
        if hit is not None:
            self._edit_color(hit)
            return
        if self._bar_rect().adjusted(-6, -6, 6, 6).contains(pos):
            self.add_stop(position=self._x_to_pos(pos.x()))

    def _edit_color(self, stop: ColorStop) -> None:
        color = QColorDialog.getColor(
            initial=stop.color,
            parent=self,
            title="Select color",
            options=QColorDialog.ShowAlphaChannel,
        )
        if color.isValid():
            self._selected_id = stop.id
            self.set_stop_color(stop, color)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.remove_selected()
            return
        super().keyPressEvent(event)

    def sizeHint(self) -> QSize:
        return QSize(320, self._total_height())


# --------------------------------------------------------------------------- #
# Composite editor: bar + mode combo + selected-stop details row
# --------------------------------------------------------------------------- #

class GradientEditor(_BaseWidget):
    """GradientBar plus a color-space picker and a selected-stop detail row.

    Drop this in wherever ``MultiColorSelectorWidget`` used to live:
    ``get_colors_pos()`` / ``get_colors()`` return the same shape, so
    ``create_vehicle()`` in gradient_maker.py needs no changes. The
    color-space + long-hue radio buttons in that file become redundant --
    ``current_mode()`` gives you both in one place -- but nothing forces you
    to remove them right away.
    """

    stopsChanged = Signal()
    modeChanged = Signal(object)

    def __init__(self, stops: Optional[list[ColorStop]] = None,
                 modes: list[InterpMode] = DEFAULT_MODES, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # -- color space picker --
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Interpolation:"))
        self.mode_combo = QComboBox()
        for m in modes:
            self.mode_combo.addItem(m.label, m)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_combo_changed)
        mode_row.addWidget(self.mode_combo, 1)
        root.addLayout(mode_row)

        # -- the bar --
        self.bar = GradientBar(stops=stops, parent=self)
        self.bar.set_mode(modes[0])
        self.bar.stopsChanged.connect(self.stopsChanged.emit)
        self.bar.selectionChanged.connect(self._on_selection_changed)
        root.addWidget(self.bar)

        # -- selected stop details --
        detail_row = QHBoxLayout()
        detail_row.setSpacing(6)

        self.swatch_button = QPushButton()
        self.swatch_button.setFixedSize(28, 28)
        self.swatch_button.clicked.connect(self._on_swatch_clicked)
        detail_row.addWidget(self.swatch_button)

        self.position_spin = QDoubleSpinBox()
        self.position_spin.setRange(0.0, 100.0)
        self.position_spin.setDecimals(2)
        self.position_spin.setSuffix(" %")
        self.position_spin.valueChanged.connect(self._on_position_spin_changed)
        detail_row.addWidget(self.position_spin, 1)

        self.add_button = QToolButton()
        self.add_button.setText("+")
        self.add_button.setToolTip("Add a stop in the middle")
        self.add_button.clicked.connect(lambda: self.bar.add_stop())
        detail_row.addWidget(self.add_button)

        self.remove_button = QToolButton()
        self.remove_button.setText("\u2212")  # minus sign
        self.remove_button.setToolTip("Remove the selected stop")
        self.remove_button.clicked.connect(self.bar.remove_selected)
        detail_row.addWidget(self.remove_button)

        root.addLayout(detail_row)

        self._syncing = False
        self._on_selection_changed(self.bar.selected_stop())

    # -- forwarded data API -------------------------------------------------- #

    def get_colors_pos(self) -> list[tuple[QColor, float]]:
        return self.bar.get_colors_pos()

    def get_colors(self) -> list[QColor]:
        return self.bar.get_colors()

    def set_colors_pos(self, values: list[tuple[QColor, float]]) -> None:
        self.bar.set_colors_pos(values)

    def current_mode(self) -> InterpMode:
        return self.bar.mode()

    # -- internal wiring ------------------------------------------------------ #

    def _on_mode_combo_changed(self, index: int) -> None:
        mode = self.mode_combo.itemData(index)
        self.bar.set_mode(mode)
        self.modeChanged.emit(mode)

    def _on_selection_changed(self, stop: Optional[ColorStop]) -> None:
        self._syncing = True
        has_stop = stop is not None
        self.swatch_button.setEnabled(has_stop)
        self.position_spin.setEnabled(has_stop)
        self.remove_button.setEnabled(has_stop and len(self.bar._stops) > GradientBar.MIN_STOPS)
        if has_stop:
            self._apply_swatch_style(stop.color)
            self.position_spin.setValue(stop.position)
        self._syncing = False

    def _apply_swatch_style(self, color: QColor) -> None:
        r, g, b, a = color.getRgb()
        self.swatch_button.setStyleSheet(
            f"QPushButton {{ background-color: rgba({r},{g},{b},{a}); "
            f"border-radius: 6px; border: 1px solid palette(mid); }}"
        )

    def _on_swatch_clicked(self) -> None:
        stop = self.bar.selected_stop()
        if stop is None:
            return
        color = QColorDialog.getColor(
            initial=stop.color, parent=self, title="Select color",
            options=QColorDialog.ShowAlphaChannel,
        )
        if color.isValid():
            self.bar.set_stop_color(stop, color)
            self._apply_swatch_style(color)

    def _on_position_spin_changed(self, value: float) -> None:
        if self._syncing:
            return
        stop = self.bar.selected_stop()
        if stop is not None:
            self.bar.set_stop_position(stop, value)


# --------------------------------------------------------------------------- #
# Standalone demo: `python gradient_bar.py`
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = GradientEditor()
    win.setWindowTitle("GradientEditor demo")
    win.resize(420, 140)
    win.show()
    sys.exit(app.exec())