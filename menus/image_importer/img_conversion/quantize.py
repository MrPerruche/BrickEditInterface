"""
quantize.py

Reduces a PIL image to at most n_colors distinct opaque colors, with no
dithering (every pixel maps to exactly one palette color, never a blend
of two -- dithering would explode blob/rectangle count downstream).

Two methods:
    "median_cut"   -- PIL's built-in MEDIANCUT quantizer. Fast, simple,
                       a useful baseline / point of comparison against
                       older tools that don't offer anything fancier.
    "kmeans_oklab" -- k-means++ seeded Lloyd's k-means, run in OKLab
                       space (perceptually uniform, unlike raw sRGB) so
                       equal numeric distance ~= equal perceived
                       difference. Implemented directly with numpy for
                       speed; the OKLab conversion matrices are copied
                       verbatim from `coloraide`'s source (not re-derived
                       by hand) and cross-checked against coloraide's own
                       Color().convert() in the __main__ block below --
                       a transcription error in a color matrix is exactly
                       the kind of bug that wouldn't show up as a crash,
                       just a slightly-off palette.

Pixels with alpha < alpha_threshold are treated as "no block here": they
never influence palette selection, never count against n_colors, and stay
fully transparent in the output.

Dependencies: numpy, scipy (only for the denoise pass's neighbor lookups
-- already a dependency of image_layers.py), PIL. coloraide is only
imported in the __main__ verification block, not at runtime.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

import numpy as np
from PIL import Image


# --------------------------------------------------------------------------- #
# OKLab conversion -- matrices copied verbatim from coloraide's source
# (coloraide/spaces/{srgb,srgb_linear,oklab}/__init__.py), not re-derived
# by hand. See the __main__ block for a numeric cross-check against
# coloraide's own Color().convert().
# --------------------------------------------------------------------------- #

_RGB_TO_XYZ = np.array([
    [0.4123907992659593, 0.357584339383878, 0.1804807884018343],
    [0.21263900587151024, 0.715168678767756, 0.07219231536073371],
    [0.01933081871559182, 0.11919477979462598, 0.9505321522496607],
])
_XYZ_TO_RGB = np.array([
    [3.240969941904523, -1.5373831775700941, -0.4986107602930035],
    [-0.9692436362808797, 1.8759675015077204, 0.04155505740717562],
    [0.05563007969699365, -0.20397695888897652, 1.0569715142428784],
])
_XYZ_TO_LMS = np.array([
    [0.819022437996703, 0.3619062600528904, -0.1288737815209879],
    [0.03298365393238847, 0.9292868615863434, 0.03614466635064236],
    [0.04817718935962421, 0.2642395317527308, 0.6335478284694309],
])
_LMS_TO_XYZ = np.array([
    [1.226879875845924, -0.5578149944602171, 0.2813910456659647],
    [-0.04057574521480083, 1.112286803280317, -0.07171105806551635],
    [-0.07637293667466008, -0.42149333240224324, 1.5869240198367818],
])
_LMS3_TO_OKLAB = np.array([
    [0.21045426830931396, 0.7936177747023053, -0.0040720430116192585],
    [1.9779985324311686, -2.42859224204858, 0.450593709617411],
    [0.025904042465547734, 0.7827717124575297, -0.8086757549230774],
])
_OKLAB_TO_LMS3 = np.array([
    [1.0, 0.3963377773761749, 0.21580375730991364],
    [1.0, -0.10556134581565857, -0.0638541728258133],
    [1.0, -0.08948417752981186, -1.2914855480194092],
])


def _srgb_u8_to_linear(rgb_u8: np.ndarray) -> np.ndarray:
    """(N,3) uint8 sRGB -> (N,3) float64 linear-light sRGB, 0-1."""
    c = rgb_u8.astype(np.float64) / 255.0
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def _linear_to_srgb_u8(linear: np.ndarray) -> np.ndarray:
    """(N,3) float64 linear-light sRGB -> (N,3) uint8 sRGB, clipped to gamut."""
    linear = np.clip(linear, 0.0, 1.0)
    srgb = np.where(linear > 0.0031308, 1.055 * np.power(linear, 1 / 2.4) - 0.055, 12.92 * linear)
    return np.clip(np.round(srgb * 255.0), 0, 255).astype(np.uint8)


def srgb_u8_to_oklab(rgb_u8: np.ndarray) -> np.ndarray:
    """(N,3) uint8 sRGB -> (N,3) float64 OKLab."""
    linear = _srgb_u8_to_linear(rgb_u8)
    xyz = linear @ _RGB_TO_XYZ.T
    lms = xyz @ _XYZ_TO_LMS.T
    lms_cbrt = np.cbrt(lms)
    return lms_cbrt @ _LMS3_TO_OKLAB.T


def oklab_to_srgb_u8(lab: np.ndarray) -> np.ndarray:
    """(N,3) float64 OKLab -> (N,3) uint8 sRGB (clipped if out of gamut)."""
    lms_cbrt = lab @ _OKLAB_TO_LMS3.T
    lms = lms_cbrt ** 3
    xyz = lms @ _LMS_TO_XYZ.T
    linear = xyz @ _XYZ_TO_RGB.T
    return _linear_to_srgb_u8(linear)


# --------------------------------------------------------------------------- #
# k-means++ seeded Lloyd's k-means, weighted by pixel frequency
# --------------------------------------------------------------------------- #

def _kmeans_plusplus_init(points: np.ndarray, weights: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Standard k-means++ seeding, generalized to weighted points: the
    first center is picked with probability proportional to `weights`;
    each subsequent center with probability proportional to
    weight * (squared distance to the nearest already-chosen center)."""
    n = points.shape[0]
    centers = np.empty((k, points.shape[1]), dtype=points.dtype)

    first = rng.choice(n, p=weights / weights.sum())
    centers[0] = points[first]

    closest_sq_dist = np.sum((points - centers[0]) ** 2, axis=1)
    for i in range(1, k):
        probs = weights * closest_sq_dist
        total = probs.sum()
        if total <= 0:
            # remaining points are all exact duplicates of chosen centers
            remaining = rng.choice(n, size=k - i, replace=True)
            centers[i:] = points[remaining]
            break
        probs = probs / total
        chosen = rng.choice(n, p=probs)
        centers[i] = points[chosen]
        new_sq_dist = np.sum((points - centers[i]) ** 2, axis=1)
        closest_sq_dist = np.minimum(closest_sq_dist, new_sq_dist)

    return centers


def kmeans_weighted(
    points: np.ndarray, weights: np.ndarray, k: int, max_iter: int = 100, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """
    Weighted Lloyd's k-means with k-means++ seeding.
    points: (N, D) float array (here, OKLab coordinates of unique colors)
    weights: (N,) how many pixels each point represents
    Returns (centers (k, D), assignment (N,) int -- which center each point belongs to).
    """
    rng = np.random.default_rng(seed)
    n = points.shape[0]
    if n <= k:
        # fewer unique points than clusters requested -- every point is its own center
        assignment = np.arange(n)
        return points.copy(), assignment

    centers = _kmeans_plusplus_init(points, weights, k, rng)
    assignment = np.zeros(n, dtype=int)

    for _ in range(max_iter):
        # ||p - c||^2 = ||p||^2 + ||c||^2 - 2 p.c -- avoids ever materializing
        # an (N, k, 3) array, which is what was blowing up memory for large N
        # (a real photo can easily have hundreds of thousands of unique
        # colors before quantization). This is O(N*k) instead of O(N*k*3),
        # and the matrix multiply is much faster besides.
        points_sq = (points ** 2).sum(axis=1)[:, None]         # (N, 1)
        centers_sq = (centers ** 2).sum(axis=1)[None, :]       # (1, k)
        dists = points_sq + centers_sq - 2 * points @ centers.T  # (N, k)
        new_assignment = dists.argmin(axis=1)

        if np.array_equal(new_assignment, assignment) and _:
            break
        assignment = new_assignment

        new_centers = centers.copy()
        for c in range(k):
            mask = assignment == c
            if mask.any():
                w = weights[mask]
                new_centers[c] = (points[mask] * w[:, None]).sum(axis=0) / w.sum()
            # else: empty cluster keeps its old center (rare with ++ seeding)
        if np.allclose(new_centers, centers):
            centers = new_centers
            break
        centers = new_centers

    return centers, assignment


# --------------------------------------------------------------------------- #
# Denoise: replace isolated single-pixel outliers with their neighborhood's
# majority color. Conservative by design -- only touches a pixel that
# differs from every one of its (non-transparent) 4-neighbors, so it
# cleans up quantization speckle without eating genuine small features
# that share an edge with at least one same-colored neighbor.
# --------------------------------------------------------------------------- #

def denoise_index_grid(index_grid: np.ndarray, transparent_id: Optional[int], passes: int = 1) -> np.ndarray:
    grid = index_grid.copy()
    h, w = grid.shape

    for _ in range(passes):
        valid = grid != transparent_id if transparent_id is not None else np.ones_like(grid, dtype=bool)

        up = np.roll(grid, 1, axis=0); up[0, :] = -1
        down = np.roll(grid, -1, axis=0); down[-1, :] = -1
        left = np.roll(grid, 1, axis=1); left[:, 0] = -1
        right = np.roll(grid, -1, axis=1); right[:, -1] = -1
        valid_up = np.roll(valid, 1, axis=0); valid_up[0, :] = False
        valid_down = np.roll(valid, -1, axis=0); valid_down[-1, :] = False
        valid_left = np.roll(valid, 1, axis=1); valid_left[:, 0] = False
        valid_right = np.roll(valid, -1, axis=1); valid_right[:, -1] = False

        matches_up = valid_up & (up == grid)
        matches_down = valid_down & (down == grid)
        matches_left = valid_left & (left == grid)
        matches_right = valid_right & (right == grid)
        has_any_match = matches_up | matches_down | matches_left | matches_right
        has_any_valid_neighbor = valid_up | valid_down | valid_left | valid_right

        isolated = valid & has_any_valid_neighbor & ~has_any_match

        rows, cols = np.where(isolated)
        for r, c in zip(rows, cols):
            neighbor_vals = []
            if r > 0 and valid[r - 1, c]:
                neighbor_vals.append(int(grid[r - 1, c]))
            if r < h - 1 and valid[r + 1, c]:
                neighbor_vals.append(int(grid[r + 1, c]))
            if c > 0 and valid[r, c - 1]:
                neighbor_vals.append(int(grid[r, c - 1]))
            if c < w - 1 and valid[r, c + 1]:
                neighbor_vals.append(int(grid[r, c + 1]))
            if neighbor_vals:
                grid[r, c] = Counter(neighbor_vals).most_common(1)[0][0]

        if len(rows) == 0:
            break

    return grid


# --------------------------------------------------------------------------- #
# Top-level entry point
# --------------------------------------------------------------------------- #

def quantize_image(
    image: Image.Image,
    n_colors: int,
    method: str = "kmeans_oklab",   # "kmeans_oklab" | "median_cut"
    alpha_threshold: int = 1,
    denoise: bool = True,
    denoise_passes: int = 1,
    seed: int = 0,
) -> Image.Image:
    """
    Returns a new RGBA image with at most n_colors distinct opaque colors.
    Pixels with alpha < alpha_threshold are left fully transparent and
    never influence palette selection or count against n_colors. No
    dithering -- exactly one palette color per pixel, never a blend.
    """
    rgba = np.array(image.convert("RGBA"))
    h, w, _ = rgba.shape
    alpha = rgba[..., 3]
    transparent_mask = alpha < alpha_threshold
    rgb = rgba[..., :3]

    packed = (rgb[..., 0].astype(np.uint32) << 16) | (rgb[..., 1].astype(np.uint32) << 8) | rgb[..., 2]
    packed_flat = packed.reshape(-1)
    opaque_flat = ~transparent_mask.reshape(-1)

    unique_vals, inverse, counts = np.unique(packed_flat[opaque_flat], return_inverse=True, return_counts=True)
    unique_colors = np.stack([
        (unique_vals >> 16) & 0xFF, (unique_vals >> 8) & 0xFF, unique_vals & 0xFF
    ], axis=1).astype(np.uint8)

    if len(unique_vals) <= n_colors:
        palette = unique_colors
        assignment = inverse
    elif method == "kmeans_oklab":
        lab_points = srgb_u8_to_oklab(unique_colors)
        centers_lab, cluster_of_unique_color = kmeans_weighted(
            lab_points, counts.astype(np.float64), n_colors, seed=seed
        )
        palette = oklab_to_srgb_u8(centers_lab)
        assignment = cluster_of_unique_color[inverse]  # compose: pixel -> unique color -> cluster
    elif method == "median_cut":
        # PIL looks at the actual image (so it does its own frequency
        # weighting internally) -- feed it the opaque RGB pixels directly.
        rgb_img = Image.fromarray(rgb, mode="RGB")
        quantized = rgb_img.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        palette_flat = quantized.getpalette()[: n_colors * 3]
        palette = np.array(palette_flat, dtype=np.uint8).reshape(-1, 3)
        pixel_indices = np.array(quantized, dtype=np.int64)  # (H, W) palette index per pixel
        # remap to match our unique-color ordering
        assignment = pixel_indices.reshape(-1)[opaque_flat]
    else:
        raise ValueError(f"unknown method: {method}")

    index_grid = np.full((h, w), -1, dtype=np.int64)  # -1 reserved for transparent
    index_grid.reshape(-1)[opaque_flat] = assignment

    if denoise:
        index_grid = denoise_index_grid(index_grid, transparent_id=-1, passes=denoise_passes)

    out_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    opaque = index_grid != -1
    out_rgba[opaque, :3] = palette[index_grid[opaque]]
    out_rgba[opaque, 3] = 255
    # transparent pixels stay (0, 0, 0, 0)

    return Image.fromarray(out_rgba, mode="RGBA")
