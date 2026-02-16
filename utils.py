import os
import sys
import math
import struct
from random import uniform
from brickedit import *

from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QColor


VERSION = "1.2.0"
DEV_VERSION = True


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
    else:
        return f"{seconds // YEAR} year(s)"


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
    v = uniform(0.2, 0.9)
    if alpha:
        return QColor.fromHsvF(h, s, v, uniform(0.6, 1))
    else:
        return QColor.fromHsvF(h, s, v, 1)


def get_vehicles_path():
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
        return None

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


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().setParent(None)
        elif item.layout():
            clear_layout(item.layout())



def _float32(value):
    """Convert a Python float to single-precision float32."""
    return struct.unpack('f', struct.pack('f', value))[0]

def max_float32_for_tolerance(tol: float) -> float:
    """
    Returns the largest float32 number where precision is still finer than `tol`.
    """
    # Machine epsilon for float32: 2^-23 ≈ 1.1920929e-7
    eps = 2 ** -23

    # Maximum number where relative precision <= tol
    max_val = tol / eps

    return _float32(max_val)



def try_serialize(brv: BRVFile) -> bytearray | None:
    try:
        return brv.serialize()

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
