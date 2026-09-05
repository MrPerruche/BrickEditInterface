import os
import sys
import math
import struct
from random import uniform
import numpy as np
from brickedit import *

from typing import NoReturn

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter


VERSION = "2.0.0"
EARLY_ACCESS = 1  # 0 = Dev, None = Release, >= 1 = Early Access {v}
DEV_VERSION = EARLY_ACCESS >= 0
DISPLAY_VERSION_SHORT = f"{VERSION} (Dev)" if EARLY_ACCESS == 0 else f"{VERSION} Early Access {EARLY_ACCESS}" if EARLY_ACCESS is not None else VERSION
DISPLAY_VERSION = f"Version {DISPLAY_VERSION_SHORT}"


class Sentinel:

    _instances = {}

    def __new__(cls, name: str):

        if name not in cls._instances:
            instance = super().__new__(cls)
            instance.name = name
            cls._instances[name] = instance
        return cls._instances[name]

    def __repr__(self):
        return f"<{self.name}>"


def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)


def str_time_since(seconds):
    MINUTE, HOUR, DAY, MONTH, YEAR = 60, 60 * 60, 24 * 60 * 60, 30 * 24 * 60 * 60, 365 * 24 * 60 * 60
    if seconds < MINUTE:
        return f"{seconds}s"
    elif seconds < HOUR:
        return f"{seconds // MINUTE}m"
    elif seconds < DAY:
        return f"{seconds // HOUR}h {seconds % HOUR // MINUTE}m"
    elif seconds < MONTH:
        return f"{seconds // DAY}d {seconds % DAY // HOUR}h"
    elif seconds < YEAR:
        return f"{seconds // MONTH} month(s) {seconds % MONTH // DAY}d"
    elif seconds < YEAR*1000:
        return f"{seconds // YEAR} year(s)"
    else:
        return "never"


def get_vehicle_version(vehicle_path: str) -> tuple[int, int]:
    """Returns version of BRM then BRV file. Returns version 0 if file does not exist."""
    brm_path = os.path.join(vehicle_path, 'MetaData.brm')
    brv_path = os.path.join(vehicle_path, 'Vehicle.brv')

    brm_version = 0
    brv_version = 0
    if os.path.exists(brm_path):
        with open(brm_path, 'rb') as f:
            brm_version = int.from_bytes(f.read(1), 'little')
    if os.path.exists(brv_path):
        with open(brv_path, 'rb') as f:
            brv_version = int.from_bytes(f.read(1), 'little')

    return brm_version, brv_version


def parse_float_tuple(text: str):
    text = text.strip().strip("()")
    return tuple(map(float, text.split(",")))


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total



def get_random_color(alpha: bool) -> QColor:
    h = uniform(0, 1)
    s = uniform(0.5, 1)
    v = uniform(0.5, 0.9)
    if alpha:
        return QColor.fromHsvF(h, s, v, uniform(0.85, 1))
    else:
        return QColor.fromHsvF(h, s, v, 1)


def all_equal(iterable, key=lambda x: x):
    iterator = iter(iterable)
    try:
        first = key(next(iterator))
    except StopIteration:
        return True
    return all(first == key(x) for x in iterator)


def get_vehicles_path() -> str | NoReturn:
    if sys.platform.startswith("win"):
        return os.path.expanduser("~\\AppData\\Local\\BrickRigs\\SavedRemastered\\Vehicles")
    
    elif sys.platform.startswith("linux"):
        native_path = os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/552100/pfx/drive_c/users/steamuser/AppData/Local/BrickRigs/SavedRemastered/Vehicles")
        if os.path.exists(native_path):
            return native_path
        
        flatpak_path = os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/compatdata/552100/pfx/drive_c/users/steamuser/AppData/Local/BrickRigs/SavedRemastered/Vehicles")
        if os.path.exists(flatpak_path):
            return flatpak_path
    
    else:
        QMessageBox.critical(None, "Unsupported Operating System",
            "BrickEdit-Interface does not support this operating system."
        )
        sys.exit(1)

def repr_file_size(size_bytes: int, digits: int = 2, unit_change_threshold: int = 1024):
    # If you're dealing with RiB or QiB wth are you doing playing Brick Rigs and using this sht "software" in 2200 ?
    size_names = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    i = 0
    assert unit_change_threshold >= 1024, f"Invalid unit change threshold {unit_change_threshold}"
    while size_bytes >= unit_change_threshold:
        size_bytes /= 1024
        i += 1
    if digits == 0:
        return f"{int(size_bytes)} {size_names[i]}"
    else:
        return f"{round(size_bytes, digits)} {size_names[i]}"


def wipe_layout(layout, delete_widgets: bool = True):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            if delete_widgets:
                widget.deleteLater()
            else:
                widget.hide()
        else:
            child_layout = item.layout()
            if child_layout:
                wipe_layout(child_layout, delete_widgets)


def max_float32_for_tolerance(tol: float) -> float:
    """
    Returns the largest float32 number where precision is still finer than `tol`.
    """
    """# Machine epsilon for float32: 2^-23 ≈ 1.1920929e-7
    eps = 2 ** -23

    # Maximum number where relative precision <= tol
    max_val = tol / eps

    return _float32(max_val)"""
    # With numpy
    return tol / np.finfo(np.float32).eps



def try_serialize(brv: BRVFile, allow_unknown: bool = True) -> bytearray | None:
    try:
        return brv.serialize(allow_unknown=allow_unknown)

    # Message box in case of bugs
    except PermissionError as e:
        QMessageBox.critical(None, "Failed to save changes",
            f"BrickEdit-Interface was denied permission to save changes: {str(e)}"
        )
    except OSError as e:
        QMessageBox.critical(None, "Failed to save changes",
            f"BrickEdit-Interface could not save changes: {str(e)}"
        )
    except Exception as e:
        QMessageBox.critical(None, "Failed to save changes",
            f"BrickEdit failed to save changes (most likely failed to serialize). Please report the following errors to the developers:\n\n{type(e).__name__}: {str(e)}"
        )
        raise e

    return None


def try_serialize_metadata(
    brm: BRMFile,
    file_name: Optional[str] = None,
    description: str = "",
    brick_count: Optional[int] = None,
    size: Vec3 = Vec3(0, 0, 0),
    weight: float = 0.0,
    price: float = 0.0,
    author: Optional[int] = None,
    creation_time: Optional[int] = None,
    last_update_time: Optional[int] = None,
    visibility: int = VISIBILITY_PUBLIC,
    tags: Optional[list[str]] = None
) -> bytearray | None:

    try:
        return brm.serialize(
            file_name=file_name,
            description=description,
            brick_count=brick_count,
            size=size,
            weight=weight,
            price=price,
            author=author,
            creation_time=creation_time,
            last_update_time=last_update_time,
            visibility=visibility,
            tags=tags
        )
    
    except PermissionError as e:
        QMessageBox.critical(None, "Failed to save changes",
            f"BrickEdit-Interface was denied permission to save changes: {str(e)}"
        )
    except OSError as e:
        QMessageBox.critical(None, "Failed to save changes",
            f"BrickEdit-Interface could not save changes: {str(e)}"
        )
    except Exception as e:
        QMessageBox.critical(None, "Failed to save changes",
            f"BrickEdit failed to save changes (most likely failed to serialize). Please report the following errors to the developers:\n\n{type(e).__name__}: {str(e)}"
        )
        raise e

    return None



def linear_srgb_to_oklab(r, g, b):
    # First, convert linear RGB to the LMS-like space (Ottosson's combined matrix)
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    # Apply cube roots (with sign)
    l_ = math.copysign(abs(l)**(1/3), l)
    m_ = math.copysign(abs(m)**(1/3), m)
    s_ = math.copysign(abs(s)**(1/3), s)
    # Now convert to Oklab L,a,b
    L = 0.2104542553*l_ + 0.7936177850*m_ - 0.0040720468*s_
    a = 1.9779984951*l_ - 2.4285922050*m_ + 0.4505937099*s_
    b = 0.0259040371*l_ + 0.7827717662*m_ - 0.8086757660*s_
    return (L, a, b)

def srgb_to_linear(c):
    if c <= 0.04045: return c/12.92
    return ((c+0.055)/1.055)**2.4

def oklab_to_linear_srgb(L, a, b):
    # First, undo the final Oklab matrix
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    # Cube them to get l, m, s
    l = l_**3
    m = m_**3
    s = s_**3
    # Now apply the inverse of M1 to get linear RGB
    r = +4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    b = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return (r, g, b)

def oklab_to_oklch(L, a, b):
    C = math.sqrt(a*a + b*b)
    # Hue in degrees (atan2 gives radians, convert to [0,360))
    h = math.degrees(math.atan2(b, a)) % 360
    return (L, C, h)

def oklch_to_oklab(L, C, h):
    # Assuming h is given in degrees
    rad = math.radians(h)
    a = C * math.cos(rad)
    b = C * math.sin(rad)
    return (L, a, b)



_tint_cache: dict[tuple[int, str, int, int], QIcon] = {}

def tint_icon(icon: QIcon, color: str, size: tuple[int, int] | None = None) -> QIcon:
    if size is None:
        idx_max, current_max = -1, 0
        for idx, s in enumerate(icon.availableSizes()):
            if s.width() > current_max:
                current_max, idx_max = s.width(), idx
        size_x, size_y = (icon.availableSizes()[idx_max].width(), icon.availableSizes()[idx_max].height()) if idx_max != -1 else (64, 64)
    else:
        size_x, size_y = size, size

    key = (icon.cacheKey(), color, size_x, size_y)
    cached = _tint_cache.get(key)
    if cached is not None:
        return cached

    pixmap = icon.pixmap(size_x, size_y)
    out = QPixmap(size_x, size_y)
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(out.rect(), QColor(color))
    painter.end()

    result = QIcon(out)
    _tint_cache[key] = result
    return result



def stack_color(bottom: QColor, top: QColor) -> QColor:
    sa = top.alphaF()
    da = bottom.alphaF()

    oa = sa + da * (1.0 - sa)

    if oa == 0:
        return QColor(0, 0, 0, 0)

    r = (top.redF()   * sa + bottom.redF()   * da * (1.0 - sa)) / oa
    g = (top.greenF() * sa + bottom.greenF() * da * (1.0 - sa)) / oa
    b = (top.blueF()  * sa + bottom.blueF()  * da * (1.0 - sa)) / oa

    return QColor.fromRgbF(r, g, b, oa)


def stack_qcolors(*colors: str | QColor) -> QColor:
    """Color format: '#AARRGGBB'. Applies each color on top of the previous in order"""
    qcolors = [QColor(color) if isinstance(color, str) else color for color in colors]
    assert len(qcolors) > 1, "Must provide at least two colors"
    final = qcolors[0]

    for i in range(1, len(qcolors)):
        final = stack_color(final, qcolors[i])
    return final

    
def stack_str_colors(*colors: str | QColor) -> str:
    """Returns in #AARRGGBB format"""
    return stack_qcolors(*colors).name(QColor.NameFormat.HexArgb)
