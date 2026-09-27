"""Virtualized vehicle list: model + filter proxy + view + delegate + background loader.

Why not one widget per vehicle: building a card (~15 widgets) costs milliseconds, which capped the old list at
25 vehicles and made searching (which rebuilt the list) very slow. Here a QListView only ever *paints* the rows
that are visible, so 1000 vehicles cost the same as 25.

Data flow:
    VehicleLoader (thread) -> VehicleListModel (all valid vehicles) -> VehicleFilterProxy (search) -> VehicleListView
                                                                                                    + VehicleCardDelegate (paints a card)
"""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, UTC

from PySide6.QtCore import (
    QAbstractListModel, QModelIndex, QSortFilterProxyModel, QThread, Qt, Signal, QSize, QRect, QRectF, QPersistentModelIndex
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QListView, QStyle, QStyledItemDelegate

import brickedit

from ui.theme import Theme, register_has_theme_and_apply, theme_manager
from ui.components.vehicle.vehicle_card import VehicleCardData, format_vehicle_card_texts


# Geometry, taken from the old widget-based VehicleCard so the list looks the same
CARD_HEIGHT = 71
CARD_GAP = 6
ROW_HEIGHT = CARD_HEIGHT + CARD_GAP
CARD_MARGINS = (7, 7, 9, 7)  # left, top, right, bottom (inside the card)
THUMBNAIL_SIZE = 56
BORDER_WIDTH = 2
BORDER_RADIUS = 4
TEXT_REFRESH_SECONDS = 30  # "time since" texts are recomputed at most this often


@dataclass
class VehicleListEntry:
    path: str
    data: VehicleCardData
    search_key: str  # lowercase display name, what the search box matches against
    _texts: tuple[str, str, str] | None = field(default=None, repr=False)
    _texts_time: float = field(default=0.0, repr=False)

    def texts(self) -> tuple[str, str, str]:
        """(name, date text, brick count text), cached because painting asks for them all the time."""
        now = time.monotonic()
        if self._texts is None or now - self._texts_time > TEXT_REFRESH_SECONDS:
            self._texts = format_vehicle_card_texts(self.data)
            self._texts_time = now
        return self._texts


# --------------------------------------------------------------------------- #
# Model / proxy
# --------------------------------------------------------------------------- #

class VehicleListModel(QAbstractListModel):

    EntryRole = Qt.ItemDataRole.UserRole + 1
    ActiveRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[VehicleListEntry] = []
        self._row_of: dict[str, int] = {}
        self._active_path: str | None = None

    # -- Qt model API

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._entries)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._entries)):
            return None
        entry = self._entries[index.row()]
        if role == self.EntryRole:
            return entry
        if role == self.ActiveRole:
            return entry.path == self._active_path
        if role == Qt.ItemDataRole.DisplayRole:
            return entry.texts()[0]
        if role == Qt.ItemDataRole.ToolTipRole:
            return entry.path
        return None

    # -- Content

    def entry_at(self, row: int) -> VehicleListEntry:
        return self._entries[row]

    def append(self, entries: list[VehicleListEntry]):
        if not entries:
            return
        first = len(self._entries)
        self.beginInsertRows(QModelIndex(), first, first + len(entries) - 1)
        self._entries.extend(entries)
        for i, entry in enumerate(entries, start=first):
            self._row_of[entry.path] = i
        self.endInsertRows()

    def replace(self, entries: list[VehicleListEntry]):
        self.beginResetModel()
        self._entries = list(entries)
        self._row_of = {entry.path: i for i, entry in enumerate(self._entries)}
        self.endResetModel()

    def clear(self):
        if self._entries:
            self.replace([])

    # -- Active (accented) vehicle

    def set_active_path(self, path: str | None):
        if path == self._active_path:
            return
        old, self._active_path = self._active_path, path
        for p in (old, path):
            row = self._row_of.get(p) if p is not None else None
            if row is not None:
                idx = self.index(row)
                self.dataChanged.emit(idx, idx, [self.ActiveRole])


class VehicleFilterProxy(QSortFilterProxyModel):
    """Search. Keeps the source order; re-evaluated on the fly as the loader adds vehicles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ""

    def set_query(self, query: str):
        query = (query or "").lower().strip()
        if query == self._query:
            return
        self._query = query
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        if not self._query:
            return True
        return self._query in self.sourceModel().entry_at(source_row).search_key


# --------------------------------------------------------------------------- #
# Background loading
# --------------------------------------------------------------------------- #

def _file_stamp(path: str) -> int:
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return -1


class VehicleLoader(QThread):
    """Lists the vehicles folder (newest first) and reads every vehicle's metadata off the UI thread, streaming
    the valid ones to the model in batches so the first rows show up immediately.

    `cache` maps a vehicle path to (file stamp, entry or None if invalid). It is shared between loaders, so
    a reload only re-reads vehicles whose files changed."""

    batch_ready = Signal(int, list)  # generation, [VehicleListEntry]
    loaded = Signal(int)             # generation: everything was listed and sent

    FIRST_BATCH = 12
    BATCH_SECONDS = 0.05
    MAX_BATCH = 60

    def __init__(self, generation: int, vehicles_path: str, cache: dict, parent=None):
        super().__init__(parent)
        self.generation = generation
        self.vehicles_path = vehicles_path
        self.cache = cache
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            with os.scandir(self.vehicles_path) as it:
                folders = sorted(
                    (e for e in it if e.is_dir()),
                    key=lambda e: e.stat().st_mtime,
                    reverse=True,
                )
        except OSError:
            self.loaded.emit(self.generation)
            return

        batch: list[VehicleListEntry] = []
        sent_first = False
        last_send = time.monotonic()
        for folder in folders:
            if self._cancelled:
                return
            entry = self._load(folder.path)
            if entry is not None:
                batch.append(entry)
            now = time.monotonic()
            if batch and (
                len(batch) >= self.MAX_BATCH
                or (not sent_first and len(batch) >= self.FIRST_BATCH)
                or now - last_send > self.BATCH_SECONDS
            ):
                self.batch_ready.emit(self.generation, batch)
                batch, sent_first, last_send = [], True, now
        if self._cancelled:
            return
        if batch:
            self.batch_ready.emit(self.generation, batch)
        self.loaded.emit(self.generation)

    def _load(self, path: str) -> VehicleListEntry | None:
        brm_path = os.path.join(path, "MetaData.brm")
        brv_path = os.path.join(path, "Vehicle.brv")
        stamp = (_file_stamp(brm_path), _file_stamp(brv_path))
        cached = self.cache.get(path)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        entry = self._read(brm_path, brv_path, path)
        self.cache[path] = (stamp, entry)
        return entry

    @staticmethod
    def _read(brm_path: str, brv_path: str, path: str) -> VehicleListEntry | None:
        """Same validity rules the old list used: supported version, metadata present and readable."""
        try:
            brv_head = None
            version = brickedit.FILE_MAIN_VERSION
            if os.path.exists(brv_path):
                with open(brv_path, "rb") as f:
                    brv_head = f.read(3)
                version = brv_head[0] if brv_head else 0
            if version < brickedit.FILE_MIN_SUPPORTED_VERSION:
                return None
            with open(brm_path, "rb") as f:
                brm = bytearray(f.read())
        except OSError:
            return None
        data, error = VehicleCardData.load_brm_silent(brm, bytearray(brv_head) if brv_head else None)
        if error is not None:
            return None
        return VehicleListEntry(path=path, data=data, search_key=data.name.lower().strip() or "unnamed")


# --------------------------------------------------------------------------- #
# Painting
# --------------------------------------------------------------------------- #

class VehicleCardDelegate(QStyledItemDelegate):
    """Paints a vehicle card. Looks like the old Surface-based VehicleCard: regular/accent style, hover and
    pressed backgrounds, thumbnail, name, dates and brick count."""

    MAX_THUMBNAILS = 300

    def __init__(self, view: "VehicleListView"):
        super().__init__(view)
        self._view = view
        self._thumbnails: OrderedDict[tuple[str, float], QPixmap] = OrderedDict()

    def clear_thumbnails(self):
        self._thumbnails.clear()

    def sizeHint(self, option, index) -> QSize:
        return QSize(max(option.rect.width(), 1), ROW_HEIGHT)

    # -- thumbnails (loaded on first paint, ~1.5 ms each)

    def _thumbnail(self, path: str, dpr: float) -> QPixmap:
        key = (path, dpr)
        pixmap = self._thumbnails.get(key)
        if pixmap is not None:
            self._thumbnails.move_to_end(key)
            return pixmap
        source = QPixmap(os.path.join(path, "Preview.png"))
        if source.isNull():
            source = QIcon(":/assets/icons/missing_thumbnail_v2.png").pixmap(QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        side = round(THUMBNAIL_SIZE * dpr)
        pixmap = source.scaled(side, side, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pixmap.setDevicePixelRatio(dpr)
        self._thumbnails[key] = pixmap
        if len(self._thumbnails) > self.MAX_THUMBNAILS:
            self._thumbnails.popitem(last=False)
        return pixmap

    # -- painting

    @staticmethod
    def _fonts(base: QFont) -> tuple[QFont, QFont]:
        name_font, small_font = QFont(base), QFont(base)
        name_font.setPointSize(13)
        name_font.setWeight(QFont.Weight.Normal)
        small_font.setPointSize(11)
        small_font.setWeight(QFont.Weight.Normal)
        return name_font, small_font

    def paint(self, painter: QPainter, option, index):
        entry: VehicleListEntry | None = index.data(VehicleListModel.EntryRole)
        if entry is None:
            return
        theme: Theme = theme_manager.current()
        active: bool = bool(index.data(VehicleListModel.ActiveRole))
        pressed = self._view.pressed_index() == QPersistentModelIndex(index)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        card = option.rect.adjusted(0, 0, 0, -CARD_GAP)
        surface = theme.accent_surface if active else theme.surface
        if pressed:
            fill = surface.muted_qcolor
        elif hovered:
            fill = surface.color_qcolor_advenced(2)
        else:
            fill = surface.color_qcolor
        border = theme.accent_border if active else theme.border

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(border.color_qcolor, BORDER_WIDTH))
        painter.setBrush(fill)
        half = BORDER_WIDTH / 2
        painter.drawRoundedRect(QRectF(card).adjusted(half, half, -half, -half), BORDER_RADIUS - half, BORDER_RADIUS - half)

        left, top, right, bottom = CARD_MARGINS
        inner = card.adjusted(left, top, -right, -bottom)

        # Thumbnail
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        dpr = self._view.devicePixelRatioF()
        pixmap = self._thumbnail(entry.path, dpr)
        pw, ph = pixmap.width() / dpr, pixmap.height() / dpr
        painter.drawPixmap(
            round(inner.left() + (THUMBNAIL_SIZE - pw) / 2), round(inner.top() + (THUMBNAIL_SIZE - ph) / 2), pixmap
        )

        # Texts
        name_font, small_font = self._fonts(option.font)
        name, date_text, brick_text = entry.texts()
        text_left = inner.left() + THUMBNAIL_SIZE + 6
        width = inner.right() + 1 - text_left

        name_fm = QFontMetrics(name_font)
        painter.setFont(name_font)
        painter.setPen(theme.text.color_qcolor)
        name_rect = QRect(text_left, inner.top(), width, name_fm.height())
        painter.drawText(
            name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            name_fm.elidedText(name, Qt.TextElideMode.ElideRight, width),
        )

        small_fm = QFontMetrics(small_font)
        painter.setFont(small_font)
        painter.setPen(theme.text.muted_qcolor)
        details_top = name_rect.bottom() + 1
        details_height = inner.bottom() + 1 - details_top
        brick_lines = brick_text.split("\n")
        brick_width = max(small_fm.horizontalAdvance(line) for line in brick_lines)
        date_width = max(width - brick_width - 8, 0)
        self._draw_lines(painter, small_fm, date_text.split("\n"),
                         QRect(text_left, details_top, date_width, details_height), Qt.AlignmentFlag.AlignLeft)
        self._draw_lines(painter, small_fm, brick_lines,
                         QRect(inner.right() + 1 - brick_width, details_top, brick_width, details_height), Qt.AlignmentFlag.AlignRight)
        painter.restore()

    @staticmethod
    def _draw_lines(painter: QPainter, fm: QFontMetrics, lines: list[str], rect: QRect, h_align):
        """Vertically centered block of single-line, elided texts."""
        line_height = fm.lineSpacing()
        y = rect.top() + (rect.height() - line_height * len(lines)) // 2
        for line in lines:
            painter.drawText(
                QRect(rect.left(), y, rect.width(), line_height), h_align | Qt.AlignmentFlag.AlignVCenter,
                fm.elidedText(line, Qt.TextElideMode.ElideRight, rect.width()),
            )
            y += line_height


# --------------------------------------------------------------------------- #
# View
# --------------------------------------------------------------------------- #

class VehicleListView(QListView):
    """List of vehicle cards. Sized to its content up to `max_height` (like the old ContentSizedScrollArea)."""

    def __init__(self, max_height: int = 275, parent=None):
        super().__init__(parent)
        self.max_height = max_height
        self._pressed = QPersistentModelIndex()

        self.setFrameShape(QListView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(ROW_HEIGHT // 3)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)  # hover
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.viewport().setAutoFillBackground(False)  # transparent: the theme's background shows through

        self.setItemDelegate(VehicleCardDelegate(self))
        register_has_theme_and_apply(self)

    def setModel(self, model):
        super().setModel(model)
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset, model.layoutChanged):
            signal.connect(self.updateGeometry)

    def sizeHint(self) -> QSize:
        rows = self.model().rowCount() if self.model() is not None else 0
        content = max(rows * ROW_HEIGHT - CARD_GAP, 0)
        return QSize(super().sizeHint().width(), min(content, self.max_height))

    def pressed_index(self) -> QPersistentModelIndex:
        return self._pressed

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = QPersistentModelIndex(self.indexAt(event.position().toPoint()))
            self.viewport().update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._pressed.isValid():
            self._pressed = QPersistentModelIndex()
            self.viewport().update()

    def _apply_theme(self, theme: Theme):
        self.viewport().update()
