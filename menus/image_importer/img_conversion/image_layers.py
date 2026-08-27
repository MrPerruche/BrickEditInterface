"""
image_layers.py

Turns a quantized, non-animated PIL image into a stack of Z-layers, each
containing non-overlapping, same-color axis-aligned rectangles ("plates").
Built around one reusable primitive (`greedy_cover_with_wildcards`) that
covers a set of "must be this color" cells using rectangles allowed to
bulge into "don't care" cells that a higher layer will end up owning.

No dependencies beyond numpy + PIL + scipy (scipy.ndimage.label, used
narrowly inside greedy_cover_with_wildcards -- see note below).

--------------------------------------------------------------------------
Pipeline
--------------------------------------------------------------------------
1. load_color_grid(image)     PIL Image -> (color_id grid, palette, transparent_id)
2. decompose_2d / decompose_layered
     - decompose_2d:      single layer, every color confined to its own cells
     - decompose_layered: single-pass onion-peeling across Z-layers (see its
                           docstring -- this is where the "borrow space from
                           colors that haven't been placed yet" trick lives)

`decompose_image(...)` runs the whole pipeline and supports the four modes
you described (none / 2d / 3d_greedy / 3d_slow).

--------------------------------------------------------------------------
Note on scipy usage (read this if you're wondering why it's back)
--------------------------------------------------------------------------
An earlier version of this module extracted every color's connected
components ONCE up front and kept a full-canvas boolean mask per
component alive simultaneously -- for a real photo, a single color can
fragment into thousands of components (texture/noise), so that meant
thousands of full-size arrays resident in memory at once. That's what was
actually blowing up RAM. It was removed in favor of per-color (not
per-component) processing.

That fixed the memory blowup, but exposed a second, separate problem:
real photographic colors are not just fragmented, they're SPARSE within
their own bounding box (a color can span 30-50% of the image by bounding
box while only ~15-50% of that box is actually that color -- scattered
texture, not one blob). Cropping `greedy_cover_with_wildcards` to a
color's overall bounding box, on its own, still means scanning a
huge-but-sparse area over and over just to place thousands of tiny
scattered rectangles.

The fix used now: `greedy_cover_with_wildcards` splits `must_cover` into
connected components internally, and crops to each component's own tight
local bounding box in turn -- never storing more than one component's
label array at a time, and never scanning more area than that one
component actually spans. This keeps both the memory profile from the
per-color refactor AND fixes the sparse-scan cost, without giving up
either property.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Optional

import numba
import numpy as np
from PIL import Image
from scipy.ndimage import label as cc_label, find_objects

_CONNECTIVITY_4 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])


Rect = tuple[int, int, int, int, int]  # r0, c0, r1, c1, color_id


# --------------------------------------------------------------------------- #
# Step 1: image -> color-id grid
# --------------------------------------------------------------------------- #

def load_color_grid(
    image: Image.Image, alpha_threshold: int = 1
) -> tuple[np.ndarray, list[tuple[int, int, int, int]], Optional[int]]:
    """
    Convert a PIL image into a 2D array of small integer color ids.

    Any pixel with alpha < alpha_threshold is treated as fully transparent
    and collapsed into a single "transparent" color id (regardless of its
    RGB channels), so stray fully-transparent pixels don't waste a color
    slot each.

    Returns:
        color_grid: (H, W) int32 array, each cell is an index into `palette`
        palette: list of (r, g, b, a) tuples, palette[color_grid[y, x]] is
                 the color of that pixel
        transparent_id: the id in `palette` that represents "no block here",
                         or None if the image has no transparent pixels
    """
    rgba = np.array(image.convert("RGBA"), dtype=np.uint32)
    h, w, _ = rgba.shape

    transparent_mask = rgba[..., 3] < alpha_threshold
    rgba = rgba.copy()
    rgba[transparent_mask] = 0  # canonicalize all transparent pixels to (0,0,0,0)

    packed = (rgba[..., 0] << 24) | (rgba[..., 1] << 16) | (rgba[..., 2] << 8) | rgba[..., 3]
    unique_vals, inverse = np.unique(packed.reshape(-1), return_inverse=True)
    color_grid = inverse.reshape(h, w).astype(np.int32)

    palette = [
        (int((v >> 24) & 0xFF), int((v >> 16) & 0xFF), int((v >> 8) & 0xFF), int(v & 0xFF))
        for v in unique_vals
    ]

    transparent_id = None
    if transparent_mask.any():
        idx = int(np.searchsorted(unique_vals, 0))
        if idx < len(unique_vals) and unique_vals[idx] == 0:
            transparent_id = idx

    return color_grid, palette, transparent_id


# --------------------------------------------------------------------------- #
# Core primitive: largest all-True rectangle in a boolean matrix
# --------------------------------------------------------------------------- #
#
# JIT-compiled with numba: this loop is called an enormous number of times
# for real photographic content (tens of thousands of calls for a single
# busy color is normal -- quantized photo noise produces genuinely jagged,
# non-rectangular regions even within one connected component, so there's
# no algorithmic shortcut around needing many small rectangles). At that
# call volume, plain interpreted Python's per-call/per-iteration overhead
# dominates regardless of how tightly each individual call is cropped.
# The stack is a preallocated numpy array instead of a Python list of
# tuples, since numba needs array-based data structures to compile this
# to native code rather than falling back to Python-object mode.

@numba.njit(cache=True)
def _largest_rectangle_impl(mask: np.ndarray) -> tuple[int, int, int, int]:
    rows, cols = mask.shape
    heights = np.zeros(cols, dtype=np.int32)
    best_area = 0
    best_r0, best_c0, best_r1, best_c1 = 0, 0, 0, 0

    stack_cols = np.zeros(cols + 1, dtype=np.int32)
    stack_heights = np.zeros(cols + 1, dtype=np.int32)

    for r in range(rows):
        for c in range(cols):
            heights[c] = heights[c] + 1 if mask[r, c] else 0

        stack_ptr = 0
        for c in range(cols + 1):
            h = heights[c] if c < cols else 0
            start = c
            while stack_ptr > 0 and stack_heights[stack_ptr - 1] >= h:
                stack_ptr -= 1
                s = stack_cols[stack_ptr]
                sh = stack_heights[stack_ptr]
                area = sh * (c - s)
                if area > best_area:
                    best_area = area
                    best_r0, best_c0, best_r1, best_c1 = r - sh + 1, s, r, c - 1
                start = s
            stack_cols[stack_ptr] = start
            stack_heights[stack_ptr] = h
            stack_ptr += 1

    return best_r0, best_c0, best_r1, best_c1


def largest_rectangle(mask: np.ndarray) -> tuple[int, int, int, int]:
    """
    Largest axis-aligned all-True rectangle in `mask` (classic histogram +
    monotonic-stack method). Assumes mask.any() is True.
    Returns (r0, c0, r1, c1), inclusive bounds.
    """
    return _largest_rectangle_impl(mask)


# --------------------------------------------------------------------------- #
# The reusable primitive: cover `must_cover` with rectangles confined to
# `allowed`, letting rectangles bulge into the allowed-but-not-required
# cells (the "don't care" padding) to end up bigger / fewer in number.
# --------------------------------------------------------------------------- #

def compute_components(must_cover: np.ndarray) -> list[tuple[slice, slice, np.ndarray]]:
    """
    Connected components of `must_cover`, each as (row_slice, col_slice,
    local_must_cover) -- exactly the per-component crop that
    `greedy_cover_with_wildcards` needs. Split out so it can be computed
    ONCE per color and reused across every restart of a multi-restart
    search (a color's own pixel mask -- hence its components -- never
    changes across restarts; only processing order and `allowed` do,
    and those are applied later, not here). See `decompose_worker.py`'s
    per-worker-process cache for where this gets reused.
    """
    labeled, n_components = cc_label(must_cover, structure=_CONNECTIVITY_4)
    if n_components == 0:
        return []
    boxes = find_objects(labeled)
    components = []
    for comp_id, box in enumerate(boxes, start=1):
        if box is None:
            continue
        row_slice, col_slice = box
        local_labeled = labeled[row_slice, col_slice]
        local_must_cover = local_labeled == comp_id
        components.append((row_slice, col_slice, local_must_cover))
    return components


def greedy_cover_with_wildcards(
    must_cover: np.ndarray,
    allowed: np.ndarray,
    precomputed_components: Optional[list[tuple[slice, slice, np.ndarray]]] = None,
) -> list[tuple[int, int, int, int]]:
    """
    Produce rectangles, all subsets of `allowed`, whose union covers every
    True cell of `must_cover`. `allowed` must be a superset of `must_cover`.

    `must_cover` is split into its connected components first, and each is
    processed within its own tight local bounding box. This matters a lot
    in practice: a real photo's color can be scattered across a large
    fraction of the canvas while only sparsely filling it (texture/noise),
    so cropping to the *whole* color's bounding box still means scanning a
    huge area repeatedly just to place many small scattered rectangles.
    Per-component cropping keeps each scan proportional to what that patch
    of true content actually spans, not the color's overall sprawl. A
    single large, mostly-solid component (e.g. a real background) still
    gets an appropriately large box and can still grow broadly within it
    -- this only shrinks the box for parts that are genuinely small/sparse.

    Within each component, two-phase per rectangle:
      1. seed  = largest rectangle made purely of still-uncovered cells
      2. grow  = expand that seed outward on all 4 sides while the new
                 row/column is entirely within `allowed`
    Growth is bounded to the component's own local crop -- rectangles
    don't reach across into unrelated, far-away padding, which is a
    reasonable trade given how much it saves on components that don't
    need to.

    Passing allowed = must_cover (no wildcard room) degenerates this into
    plain greedy meshing / classic maximal-rectangle covering.

    Rectangles from different components (or successive rectangles within
    one component, via wildcard growth) can legitimately end up
    overlapping -- harmless visually (same color, same layer) but
    occasionally one ends up entirely redundant (every cell it was
    required to cover is also covered by something else). Those get
    dropped in a cleanup pass at the end: see `_drop_redundant_rectangles`.
    An earlier attempt fixed this by restricting growth in-loop instead,
    but that was strictly worse -- overly conservative growth produced
    MORE total rectangles than the occasional harmless-overlap version
    did, since it blocked legitimate large growth just to avoid overlap
    that a cheap post-pass removes anyway without that downside.
    """
    rects: list[tuple[int, int, int, int]] = []

    # find_objects locates every component's bounding box in a single
    # efficient pass -- the earlier version recomputed each component's
    # bbox by re-scanning the FULL canvas per component (`labeled ==
    # comp_id` + `.any(...)`), which is exactly the same "huge repeated
    # scan" problem all over again, just one level down. With thousands
    # of components for a single color, that alone dominated runtime.
    components = precomputed_components if precomputed_components is not None else compute_components(must_cover)
    if not components:
        return rects

    for row_slice, col_slice, local_must_cover in components:
        r_off, c_off = row_slice.start, col_slice.start
        local_allowed = allowed[row_slice, col_slice]

        remaining = local_must_cover.copy()
        work_r0, work_c0 = 0, 0
        work_r1, work_c1 = remaining.shape[0] - 1, remaining.shape[1] - 1

        while True:
            window = remaining[work_r0:work_r1 + 1, work_c0:work_c1 + 1]
            if not window.any():
                break

            wr0, wc0, wr1, wc1 = largest_rectangle(window)
            r0, c0, r1, c1 = wr0 + work_r0, wc0 + work_c0, wr1 + work_r0, wc1 + work_c0

            can_grow_up = can_grow_down = can_grow_left = can_grow_right = True
            while can_grow_up or can_grow_down or can_grow_left or can_grow_right:
                if can_grow_up:
                    if r0 > 0 and local_allowed[r0 - 1, c0:c1 + 1].all():
                        r0 -= 1
                    else:
                        can_grow_up = False
                if can_grow_down:
                    if r1 < local_allowed.shape[0] - 1 and local_allowed[r1 + 1, c0:c1 + 1].all():
                        r1 += 1
                    else:
                        can_grow_down = False
                if can_grow_left:
                    if c0 > 0 and local_allowed[r0:r1 + 1, c0 - 1].all():
                        c0 -= 1
                    else:
                        can_grow_left = False
                if can_grow_right:
                    if c1 < local_allowed.shape[1] - 1 and local_allowed[r0:r1 + 1, c1 + 1].all():
                        c1 += 1
                    else:
                        can_grow_right = False

            rects.append((r0 + r_off, c0 + c_off, r1 + r_off, c1 + c_off))
            remaining[r0:r1 + 1, c0:c1 + 1] = False

            window_after = remaining[work_r0:work_r1 + 1, work_c0:work_c1 + 1]
            rows_any = window_after.any(axis=1)
            if not rows_any.any():
                continue  # next loop iteration's window.any() catches this and breaks
            cols_any = window_after.any(axis=0)
            new_r0 = int(np.argmax(rows_any))
            new_r1 = len(rows_any) - 1 - int(np.argmax(rows_any[::-1]))
            new_c0 = int(np.argmax(cols_any))
            new_c1 = len(cols_any) - 1 - int(np.argmax(cols_any[::-1]))
            work_r0, work_r1 = work_r0 + new_r0, work_r0 + new_r1
            work_c0, work_c1 = work_c0 + new_c0, work_c0 + new_c1

    return _drop_redundant_rectangles(rects, must_cover)


def _drop_redundant_rectangles(
    rects: list[tuple[int, int, int, int]], must_cover: np.ndarray
) -> list[tuple[int, int, int, int]]:
    """
    Remove any rectangle that contributes nothing: every must_cover cell
    it covers is also covered by at least one other surviving rectangle.
    Processed smallest-area-first so we preferentially drop small
    subsumed rectangles and keep the large ones that actually did the
    covering. Strictly safe -- never removes a rectangle that's the sole
    coverage for any required cell, so `must_cover` stays fully covered.
    """
    if len(rects) <= 1:
        return rects

    coverage = np.zeros(must_cover.shape, dtype=np.int32)
    for (r0, c0, r1, c1) in rects:
        coverage[r0:r1 + 1, c0:c1 + 1] += 1

    order = sorted(
        range(len(rects)),
        key=lambda i: (rects[i][2] - rects[i][0] + 1) * (rects[i][3] - rects[i][1] + 1),
    )
    keep = set(range(len(rects)))
    for i in order:
        r0, c0, r1, c1 = rects[i]
        sub_must_cover = must_cover[r0:r1 + 1, c0:c1 + 1]
        sub_coverage = coverage[r0:r1 + 1, c0:c1 + 1]
        if not (sub_must_cover & (sub_coverage < 2)).any():
            coverage[r0:r1 + 1, c0:c1 + 1] -= 1
            keep.discard(i)

    return [rects[i] for i in sorted(keep)]


# --------------------------------------------------------------------------- #
# Step 3a: plain 2D decomposition (no wildcard borrowing at all)
# --------------------------------------------------------------------------- #

def decompose_2d(
    color_grid: np.ndarray,
    transparent_id: Optional[int],
    color_components_cache: Optional[dict[int, list]] = None,
) -> list[Rect]:
    """Single-layer, no-wildcard decomposition: every color is confined to
    its own true cells, nobody borrows space from anybody else."""
    rects: list[Rect] = []
    for color_id in np.unique(color_grid):
        color_id = int(color_id)
        if color_id == transparent_id:
            continue
        mask = color_grid == color_id
        components = None
        if color_components_cache is not None:
            components = color_components_cache.get(color_id)
            if components is None:
                components = compute_components(mask)
                color_components_cache[color_id] = components
        for (r0, c0, r1, c1) in greedy_cover_with_wildcards(mask, mask, precomputed_components=components):
            rects.append((r0, c0, r1, c1, color_id))
    return rects


# --------------------------------------------------------------------------- #
# Step 3b: layered decomposition (the actual point of this module)
# --------------------------------------------------------------------------- #

@dataclass
class LayeredResult:
    layers: list[list[Rect]]
    overflow_pixels: int
    color_order: list[int]


def decompose_layered(
    color_grid: np.ndarray,
    transparent_id: Optional[int],
    max_layers: int,
    order: str | list[int] = "area_desc",
    rng: Optional[random.Random] = None,
    color_components_cache: Optional[dict[int, list]] = None,
) -> LayeredResult:
    """
    Single-pass onion-peeling. Process colors largest to smallest (default).
    Each color is placed on the lowest Z-layer where its own cells are
    free, and its rectangle(s) are allowed to bulge into any cell that
    hasn't been claimed by an already-processed (already-correct) color
    yet -- borrowing space from colors that haven't been placed, trusting
    that when they ARE placed, they'll land on a strictly higher layer and
    correctly patch over the mistake.

    Operates on whole colors (which may be spatially disconnected), not
    per connected-component -- see the module docstring for why. The
    "borrow space" correctness argument doesn't care whether the unit
    being placed is one connected blob or a disconnected color mask.

    Only meaningful for max_layers >= 2 (a lone background color would
    otherwise "borrow" the whole canvas with nothing above to fix it) --
    max_layers <= 1 transparently falls back to the plain 2D decomposition.

    `order` accepts either one of the named strategies below, or an
    explicit `list[int]` of color ids giving the exact processing order to
    use (bypassing the sort/shuffle entirely) -- this is what lets a
    caller replay or perturb a specific ordering (e.g. `perturb_ordering`
    below) instead of only ever sampling a fresh one. The ordering
    actually used is always reported back via `LayeredResult.color_order`,
    so callers never have to reimplement the sort/shuffle logic just to
    know what produced a given result.

    `color_components_cache`, if given, is a dict this function reads
    from and writes into: `{color_id: components}`, where `components`
    is whatever `compute_components` returns for that color's mask. A
    color's mask (hence its connected components) never changes across
    restarts of the same color_grid -- only processing order and the
    per-restart `allowed` regions do -- so a caller running many restarts
    against the same image (e.g. DecomposeWorker's local-search loop) can
    pass the SAME dict across every restart to skip re-running
    `scipy.ndimage.label` + `find_objects` for colors it's already seen.
    Pass None (the default) to always compute fresh, exactly as before.
    """
    if max_layers <= 1:
        color_order = [int(c) for c in np.unique(color_grid) if c != transparent_id]
        return LayeredResult(
            layers=[decompose_2d(color_grid, transparent_id, color_components_cache)],
            overflow_pixels=0,
            color_order=color_order,
        )

    shape = color_grid.shape

    color_ids, counts = np.unique(color_grid, return_counts=True)
    items = [(int(c), int(n)) for c, n in zip(color_ids, counts) if c != transparent_id]

    if isinstance(order, list):
        # Explicit ordering (e.g. a perturbed ordering from a previous
        # restart) -- used directly, no sort/shuffle. Any color present in
        # color_grid but missing from `order` (shouldn't normally happen,
        # since both are meant to come from the same image) is appended
        # area-desc rather than silently dropped, so correctness never
        # depends on the caller's list being perfectly in sync.
        counts_by_id = {c: n for c, n in items}
        supplied = set(order)
        ordered = [(c, counts_by_id[c]) for c in order if c in counts_by_id]
        missing = [item for item in items if item[0] not in supplied]
        ordered.extend(sorted(missing, key=lambda item: -item[1]))
    elif order == "area_desc":
        ordered = sorted(items, key=lambda item: -item[1])
    elif order == "area_asc":
        ordered = sorted(items, key=lambda item: item[1])
    elif order == "random":
        ordered = list(items)
        (rng or random).shuffle(ordered)
    else:
        raise ValueError(f"unknown order: {order}")

    # owner_layer[y, x]: highest layer currently touching this cell (-1 = untouched)
    owner_layer = np.full(shape, -1, dtype=np.int32)
    # true_claimed[y, x]: this cell's real color has been placed -- permanently
    # off-limits to everyone else's filler, regardless of layer order
    true_claimed = np.zeros(shape, dtype=bool)
    if transparent_id is not None:
        true_claimed |= color_grid == transparent_id

    layers_out: list[list[Rect]] = [[] for _ in range(max_layers)]
    overflow_pixels = 0

    for color_id, _count in ordered:
        color_mask = color_grid == color_id

        touched = owner_layer[color_mask]
        touched = touched[touched >= 0]
        lo = 0 if touched.size == 0 else int(touched.max()) + 1

        if lo < max_layers:
            target_layer = lo
        else:
            # over budget: use whichever layer corrupts the fewest of this
            # color's own cells, and log the damage
            conflict_counts = [int((owner_layer[color_mask] >= L).sum()) for L in range(max_layers)]
            target_layer = int(np.argmin(conflict_counts))
            overflow_pixels += conflict_counts[target_layer]

        # color_mask is OR'd in explicitly for the overflow case, where some
        # of this color's own cells may already be >= target_layer
        allowed = color_mask | (~true_claimed & (owner_layer < target_layer))

        components = None
        if color_components_cache is not None:
            components = color_components_cache.get(color_id)
            if components is None:
                components = compute_components(color_mask)
                color_components_cache[color_id] = components

        for (r0, c0, r1, c1) in greedy_cover_with_wildcards(color_mask, allowed, precomputed_components=components):
            layers_out[target_layer].append((r0, c0, r1, c1, color_id))
            owner_layer[r0:r1 + 1, c0:c1 + 1] = target_layer
            true_claimed[r0:r1 + 1, c0:c1 + 1] |= color_mask[r0:r1 + 1, c0:c1 + 1]

    while layers_out and not layers_out[-1]:
        layers_out.pop()

    return LayeredResult(
        layers=layers_out,
        overflow_pixels=overflow_pixels,
        color_order=[c for c, _ in ordered],
    )


def perturb_ordering(base_ordering: list[int], rng: random.Random) -> list[int]:
    """
    Return a new color ordering that's a small, local perturbation of
    `base_ordering` -- for driving a local-search variant of "3D stacking
    (slow)" instead of pure independent random restarts. The idea: with
    `n!` possible orderings, pure random sampling almost never lands near
    a previously-good ordering, so most attempts are wasted; a small
    perturbation of an already-good ordering tends to still be decent,
    which is exactly the locality pure-random restarts throw away.

    Applies exactly one randomly-chosen move:
      - swap two ADJACENT elements      -- smallest, most local change
      - swap two ARBITRARY elements     -- a bigger, non-local jump
      - reverse a random contiguous run -- 2-opt-style move

    Does not mutate `base_ordering`. `rng` is a plain `random.Random`
    (not numpy) to match `decompose_layered`'s existing rng convention.
    """
    ordering = list(base_ordering)
    n = len(ordering)
    if n < 2:
        return ordering

    move = rng.choice(("swap_adjacent", "swap_any", "reverse_segment"))

    if move == "swap_adjacent":
        i = rng.randrange(n - 1)
        ordering[i], ordering[i + 1] = ordering[i + 1], ordering[i]
    elif move == "swap_any":
        i, j = rng.sample(range(n), 2)
        ordering[i], ordering[j] = ordering[j], ordering[i]
    else:  # reverse_segment
        i, j = sorted(rng.sample(range(n), 2))
        ordering[i:j + 1] = list(reversed(ordering[i:j + 1]))

    return ordering


# --------------------------------------------------------------------------- #
# Orchestration: the four modes
# --------------------------------------------------------------------------- #

@dataclass
class DecomposeResult:
    layers: list[list[Rect]]
    palette: list[tuple[int, int, int, int]]
    total_rects: int
    overflow_pixels: int

    def summary(self) -> str:
        per_layer = ", ".join(str(len(layer)) for layer in self.layers)
        return (
            f"{self.total_rects} rectangles across {len(self.layers)} layers "
            f"[{per_layer}]"
            + (f", {self.overflow_pixels} px overflow" if self.overflow_pixels else "")
        )


def _run_layered(color_grid, transparent_id, max_layers, order, rng=None) -> DecomposeResult:
    result = decompose_layered(color_grid, transparent_id, max_layers, order=order, rng=rng)
    total = sum(len(layer) for layer in result.layers)
    return DecomposeResult(layers=result.layers, palette=[], total_rects=total, overflow_pixels=result.overflow_pixels)


def decompose_image(
    image: Image.Image,
    mode: str = "3d_greedy",   # "none" | "2d" | "3d_greedy" | "3d_slow"
    max_layers: int = 8,
    max_restarts: int = 12,
    alpha_threshold: int = 1,
    cancel_check: Optional[Callable[[], bool]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,  # (rect_count, restart_index)
) -> DecomposeResult:
    """Run the full pipeline. See module docstring for the pipeline stages."""
    color_grid, palette, transparent_id = load_color_grid(image, alpha_threshold)

    if mode == "none":
        ys, xs = np.where(color_grid != (transparent_id if transparent_id is not None else -999))
        colors = color_grid[ys, xs]
        rects = [(int(y), int(x), int(y), int(x), int(c)) for y, x, c in zip(ys, xs, colors)]
        return DecomposeResult(layers=[rects], palette=palette, total_rects=len(rects), overflow_pixels=0)

    if mode == "2d":
        result = _run_layered(color_grid, transparent_id, max_layers=1, order="area_desc")
        result.palette = palette
        return result

    if mode == "3d_greedy":
        result = _run_layered(color_grid, transparent_id, max_layers, order="area_desc")
        result.palette = palette
        return result

    if mode == "3d_slow":
        rng = random.Random(0)
        attempts = ["area_desc", "area_asc"]
        while len(attempts) < max_restarts:
            attempts.append("random")

        best: Optional[DecomposeResult] = None
        for i, order in enumerate(attempts):
            if cancel_check and cancel_check():
                break
            candidate = _run_layered(color_grid, transparent_id, max_layers, order=order, rng=rng)
            if best is None or (candidate.overflow_pixels, candidate.total_rects) < (best.overflow_pixels, best.total_rects):
                best = candidate
            if progress_callback:
                progress_callback(best.total_rects, i + 1)

        assert best is not None
        best.palette = palette
        return best

    raise ValueError(f"unknown mode: {mode}")
