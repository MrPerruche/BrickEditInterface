"""
bar.py -- the gradient bar itself: live preview + draggable stop handles.

This is the one file in this folder that has to touch raw Qt widget/paint
machinery directly (QWidget, QPainter, mouse events, QColorDialog) -- a
custom-painted, drag-driven control like this has no equivalent in a
themed-wrapper library, since it isn't built out of stock controls in the
first place. Every *other* piece of UI around it (the space combo, the
"longer hue" toggle, the position field) lives in editor.py and is built
entirely out of your ui.widgets wrappers -- see that file's docstring, and
the "raw Qt inventory" in the README for exactly what's in this file.

Interaction model (mirrors GIMP / Photoshop gradient editors):
    - Drag a handle left/right to reposition it, anywhere in [0, 100].
    - Double-click empty space on the bar to insert a new stop there,
      pre-filled with the color the gradient already had at that point.
    - Double-click a handle to open a color picker for it.
    - Right-click a handle, or select it and press Delete/Backspace, to
      remove it (at least MIN_STOPS are always kept).
    - Click a handle to select it -- editor.py's detail row reflects it.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QImage, QMouseEvent, QPainter, QPainterPath,
    QPaintEvent, QPen, QPixmap, QPolygonF
)
from PySide6.QtWidgets import QColorDialog, QSizePolicy, QWidget

from .color_math import ColorSpace, ColorStop, DEFAULT_SPACES, sample_gradient

# --------------------------------------------------------------------------- #
# Theme plumbing: real thing if we're dropped into the app, a tiny
# stand-in otherwise so `python demo.py` still works on its own.
# See the "Fitting it to your theme" section of the README for what to
# edit here once this lives inside the project.
# --------------------------------------------------------------------------- #
from ui.widgets import Widget as _BaseWidget
from ui.theme import Theme, register_has_theme_and_apply

class GradientBar(_BaseWidget):
    """A horizontal bar showing a live gradient preview with draggable stops."""

    MIN_STOPS = 2
    MAX_STOPS = 32

    stopsChanged = Signal()             # any add/remove/move/recolor
    selectionChanged = Signal(object)   # ColorStop | None

    BAR_HEIGHT = 32
    HANDLE_R = 7
    HANDLE_R_SELECTED = 9
    HANDLE_GAP = 6           # vertical gap between the bar and the handle row
    HIT_RADIUS = 12          # px; how close a click needs to land on a handle

    def __init__(self, stops: Optional[list[ColorStop]] = None, parent=None):
        super().__init__(parent)

        self._space: ColorSpace = DEFAULT_SPACES[0]
        self._long_hue: bool = False
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

        # Theme-derived colors, filled in by _apply_theme(); see the
        # dataclass-ish plain attributes below for exactly what's used
        # where in paintEvent().
        self._c_border = QColor("#5b5b64")
        self._c_text = QColor("#f8ebe0")
        self._c_accent = QColor("#ff8866")
        self._c_handle_ring = QColor("#f8ebe0")
        self._checker_brush = self._make_checker_brush()

        register_has_theme_and_apply(self)

    # -- public data API ------------------------------------------------------ #

    def get_colors_pos(self) -> list[tuple[QColor, float]]:
        """[(QColor, position 0-100), ...], sorted by position."""
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

    def get_color_at_pos(self, pos: float) -> QColor:
        return sample_gradient(self._sorted_stops(), pos, self._space, self._long_hue)

    # -- color space / hue direction ------------------------------------------ #

    def space(self) -> ColorSpace:
        return self._space

    def set_space(self, space: ColorSpace) -> None:
        if space == self._space:
            return
        self._space = space
        self._refresh()

    def long_hue(self) -> bool:
        return self._long_hue

    def set_long_hue(self, enabled: bool) -> None:
        if enabled == self._long_hue:
            return
        self._long_hue = enabled
        self._refresh()

    # -- stop manipulation ----------------------------------------------------- #

    def selected_stop(self) -> Optional[ColorStop]:
        return self._find(self._selected_id)

    def stop_count(self) -> int:
        return len(self._stops)

    def add_stop(self, position: Optional[float] = None, color: Optional[QColor] = None) -> Optional[ColorStop]:
        if len(self._stops) >= self.MAX_STOPS:
            return None
        stops = self._sorted_stops()
        if position is None:
            position = (stops[0].position + stops[-1].position) / 2.0
        position = max(0.0, min(100.0, position))
        if color is None:
            color = sample_gradient(stops, position, self._space, self._long_hue)
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

    def select(self, stop: Optional[ColorStop]) -> None:
        new_id = stop.id if stop is not None else None
        if new_id == self._selected_id:
            return
        self._selected_id = new_id
        self._refresh()

    # -- geometry helpers -------------------------------------------------------- #

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
        best, best_dist = None, None
        for stop in self._stops:
            c = self._handle_center(stop)
            dist = ((c.x() - pos.x()) ** 2 + (c.y() - pos.y()) ** 2) ** 0.5
            if best_dist is None or dist < best_dist:
                best, best_dist = stop, dist
        if best is not None and best_dist <= self.HIT_RADIUS:
            return best
        return None

    # -- painting ------------------------------------------------------------------ #

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
            img.setPixelColor(i, 0, sample_gradient(stops, t, self._space, self._long_hue))
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

        painter.setPen(QPen(self._c_border, 2))
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
        c = self._handle_center(stop)
        r = self.HANDLE_R_SELECTED if selected else self.HANDLE_R

        ring = self._c_accent if selected else self._c_handle_ring
        painter.setPen(QPen(ring, 2))
        painter.setBrush(QBrush(stop.color))

        # Diamond shape: top, right, bottom, left.
        diamond = QPolygonF([
            QPointF(c.x(), c.y() - r),
            QPointF(c.x() + r, c.y()),
            QPointF(c.x(), c.y() + r),
            QPointF(c.x() - r, c.y()),
        ])
        painter.drawPolygon(diamond)

        if stop.color.alphaF() < 0.999:
            # Small alpha hint: clip the checker pattern to the diamond.
            clip = QPainterPath()
            clip.addPolygon(diamond)

            painter.save()
            painter.setClipPath(clip)
            painter.setOpacity(1.0 - stop.color.alphaF())
            painter.fillRect(
                QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r),
                self._checker_brush,
            )
            painter.restore()

    # -- mouse / keyboard ------------------------------------------------------------ #

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
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

        self.setFocus(Qt.MouseFocusReason)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if self._drag_id is not None:
            stop = self._find(self._drag_id)
            if stop is not None:
                stop.position = self._x_to_pos(pos.x())
                self._refresh()
            return
        # Not dragging: just show a resize-ish cursor over a handle.
        hovering = self._hit_test(pos) is not None
        self.setCursor(Qt.SizeHorCursor if hovering else Qt.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_id is not None:
            self._drag_id = None
            self._dragging = False
            self.update()  # one full-resolution repaint now that dragging stopped

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        hit = self._hit_test(pos)
        if hit is not None:
            self.edit_stop_color(hit)
            return
        if self._bar_rect().adjusted(-6, -6, 6, 6).contains(pos):
            self.add_stop(position=self._x_to_pos(pos.x()))

    def edit_stop_color(self, stop: ColorStop) -> None:
        """Public so editor.py's detail-row swatch can reuse the exact same
        color picker instead of opening a second, independent dialog."""
        # No custom color-picker wrapper exists in ui/ yet, so this uses
        # QColorDialog directly -- same as the old shared_widgets/
        # color_selector.py did. Swap this call if you ever build one.
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

    # -- theming ------------------------------------------------------------------------ #

    def _apply_theme(self, theme) -> None:
        self._c_border = QColor(theme.border.color_qcolor)
        self._c_text = QColor(theme.text.color_qcolor)
        self._c_accent = QColor(theme.accent_border.color_qcolor)
        self._c_handle_ring = QColor(theme.border.color_qcolor)
        self.update()


class ColorSwatchButton(_BaseWidget):
    """A small clickable, custom-painted color square. Purely a display;
    it has no opinion about *which* color dialog opens on click -- editor.py
    wires its `clicked` signal to `GradientBar.edit_stop_color()` so there's
    exactly one QColorDialog call site in the whole folder.

    Kept in this file rather than editor.py for the same reason GradientBar
    is: it's a custom-painted widget with no ui.widgets equivalent, not an
    assembly of stock wrapper controls.
    """

    clicked = Signal()

    def __init__(self, color: QColor = QColor(128, 128, 128), size: int = 26, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._checker_brush = GradientBar._make_checker_brush()
        self._c_border = QColor("#5b5b64")
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        register_has_theme_and_apply(self)

    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self.isEnabled():
            self.clicked.emit()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 4, 4)

        painter.save()
        painter.setClipPath(path)
        if self._color.alphaF() < 1.0:
            painter.fillRect(rect, self._checker_brush)
        color = self._color if self.isEnabled() else QColor(self._color.red(), self._color.green(), self._color.blue(), 60)
        painter.fillRect(rect, color)
        painter.restore()

        painter.setPen(QPen(self._c_border, 2))
        painter.drawPath(path)

    def _apply_theme(self, theme) -> None:
        self._c_border = QColor(theme.border.color_qcolor)
        self.update()
