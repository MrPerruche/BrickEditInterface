import numpy as np
from PIL import Image

from itertools import repeat


def get_colors(img: Image) -> list[tuple[int, int, int, int]]:
    return np.unique(img.getdata(), axis=0).tolist()


def count_colors(img: Image):
    return len(np.unique(img.getdata(), axis=0))


def xy_idx(x: int, y: int, w: int) -> int:
    return y * w + x


def image_bitmask(img: Image) -> list[tuple[tuple[int, int, int, int], list[int]]]:
    data = list(img.getdata())  # flat list, already row-major
    num_pixels = len(data)

    bitmasks = {
        col: [0] * num_pixels
        for col in get_colors(img)
    }

    for idx, col in enumerate(data):
        bitmasks[col][idx] = 1

    return list(bitmasks.items())
