import numpy as np
from PIL import Image


def linear_to_srgb(img):
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0

    srgb = np.where(
        rgb <= 0.0031308,
        rgb * 12.92,
        1.055 * np.power(rgb, 1 / 2.4) - 0.055,
    )

    return Image.fromarray(
        np.round(srgb * 255).clip(0, 255).astype(np.uint8),
        "RGB",
    )

def srgb_to_linear(img):
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0

    linear = np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        ((rgb + 0.055) / 1.055) ** 2.4,
    )

    return Image.fromarray(
        np.round(linear * 255).clip(0, 255).astype(np.uint8),
        "RGB",
    )
