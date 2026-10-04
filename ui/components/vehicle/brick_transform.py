"""Moving, rotating and scaling bricks as a whole, like a single object. Qt free.

Rotations are given like a brick's rotation (Unreal's FRotator, see brick_analysis): turning bricks by a rotation turns
them the way a brick with this rotation is turned from a brick without rotation. Eg. (0, 0, 90) is a quarter turn
about the vertical axis. Scaling is uniform: a brick turned by any angle can't be stretched along a world axis.
"""

from dataclasses import dataclass, field
from math import isfinite, floor, ceil
from typing import Iterable

import brickedit

from ui.components.vehicle.brick_analysis import Axes, TupleVec3, rotation_axes, axes_to_rotation, local_to_world


EXACT_EPSILON = 1e-12  # Rotation matrix components closer than this to 0, 1 or -1 are made exact


# Properties holding a length, multiplied when bricks are scaled
SCALED_PROPERTIES = frozenset({
    brickedit.p.BRICK_SIZE,
    brickedit.p.SPINNER_RADIUS, brickedit.p.SPINNER_SIZE,
    brickedit.p.WHEEL_DIAMETER, brickedit.p.WHEEL_WIDTH, brickedit.p.TIRE_WIDTH,
    brickedit.p.PATTERN_SCALE,
    brickedit.p.FONT_SIZE,
})
# Scaled properties in cm, rounded by BrickTransform.rounding. Pattern scale is a ratio, font size not a length
ROUNDED_PROPERTIES = SCALED_PROPERTIES - {brickedit.p.PATTERN_SCALE, brickedit.p.FONT_SIZE}

ROUND_OFF, ROUND_NEAREST, ROUND_UP, ROUND_DOWN = range(4)
ROUNDING_NOISE = 1e-9  # Relative. Multiples of the step closer than this are exact (eg. 0.3 / 0.1 = 2.9999999999999996)


def _zero() -> brickedit.Vec3:
    return brickedit.Vec3(0.0, 0.0, 0.0)


@dataclass(frozen=True)
class BrickTransform:
    """Scales bricks by scale and turns them by rotation, both about a pivot, then moves them by offset. Lengths
    (see ROUNDED_PROPERTIES) are then rounded to a multiple of round_step, unless rounding is ROUND_OFF."""
    rotation: brickedit.Vec3 = field(default_factory=_zero)  # Degrees, like a brick's rotation
    scale: float = 1.0
    offset: brickedit.Vec3 = field(default_factory=_zero)    # cm
    rounding: int = ROUND_OFF
    round_step: float = 1.0                                  # cm

    def rotates(self) -> bool:
        return any(self.rotation.as_tuple())

    def scales(self) -> bool:
        return self.scale != 1.0

    def moves(self) -> bool:
        return any(self.offset.as_tuple())

    def rounds(self) -> bool:
        return self.rounding != ROUND_OFF

    def is_identity(self) -> bool:
        return not (self.rotates() or self.scales() or self.moves() or self.rounds())

    def describe(self) -> str:
        """What the transform does, eg. "rotated and moved" (empty if nothing)"""
        done = [verb for verb, does in (("rotated", self.rotates()), ("scaled", self.scales()),
                                        ("moved", self.moves()), ("rounded", self.rounds())) if does]
        if len(done) <= 1:
            return "".join(done)
        return ", ".join(done[:-1]) + " and " + done[-1]

    def is_valid(self) -> bool:
        """Every value is a finite number, the scale is positive (a negative scale would mirror the bricks), and so is
        the rounding step"""
        values = (*self.rotation.as_tuple(), self.scale, *self.offset.as_tuple(), self.round_step)
        return all(isfinite(v) for v in values) and self.scale > 0 and self.round_step > 0


def positions_center(bricks: Iterable[brickedit.Brick]) -> brickedit.Vec3:
    """Center of the box holding the positions of bricks. Their shapes are ignored: only positions are known."""
    positions = [brick.pos.as_tuple() for brick in bricks]
    if not positions:
        return _zero()
    return brickedit.Vec3(*((min(p[k] for p in positions) + max(p[k] for p in positions)) / 2.0 for k in range(3)))


def _exact_axes(axes: Axes) -> Axes:
    """axes with float noise removed from the components which are 0, 1 or -1 (eg. cos(90°) is 6e-17, not 0), so
    quarter turns move bricks exactly. Positions must not be rounded instead: Brick Rigs tells the sides of the mirror
    plane apart by sign, even 1e-10 cm away from it."""
    return tuple(tuple(next((exact for exact in (0.0, 1.0, -1.0) if abs(c - exact) < EXACT_EPSILON), c) for c in axis)
                 for axis in axes)  # type: ignore[return-value]


def scale_properties(brick: brickedit.Brick, factor: float):
    """Multiplies the lengths of a brick (see SCALED_PROPERTIES) by factor."""
    for prop in SCALED_PROPERTIES:
        try:
            value = brick.get_property(prop)
        except brickedit.BrickError:
            continue  # The brick doesn't have it
        if isinstance(value, (brickedit.Vec2, brickedit.Vec3)):
            brick.set_property(prop, value * float(factor))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            brick.set_property(prop, float(value) * factor)


def round_length(value: float, rounding: int, step: float) -> float:
    """value rounded to a multiple of step (half up for ROUND_NEAREST). A length is never rounded to 0: it would
    make the brick disappear."""
    steps = value / step
    if abs(steps - floor(steps + 0.5)) <= ROUNDING_NOISE * max(1.0, abs(steps)):
        steps = float(floor(steps + 0.5))  # Already a multiple, give or take float noise
    n = floor(steps + 0.5) if rounding == ROUND_NEAREST else ceil(steps) if rounding == ROUND_UP else floor(steps)
    if n == 0 and value != 0:
        n = 1 if value > 0 else -1
    return round(n * step, 9)  # 3 * 0.1 is 0.30000000000000004


def round_properties(brick: brickedit.Brick, rounding: int, step: float):
    """Rounds the lengths of a brick (see ROUNDED_PROPERTIES) to multiples of step (cm)."""
    for prop in ROUNDED_PROPERTIES:
        try:
            value = brick.get_property(prop)
        except brickedit.BrickError:
            continue  # The brick doesn't have it
        if isinstance(value, (brickedit.Vec2, brickedit.Vec3)):
            brick.set_property(prop, type(value)(*(round_length(c, rounding, step) for c in value.as_tuple())))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            brick.set_property(prop, round_length(float(value), rounding, step))


def transform_bricks(bricks: Iterable[brickedit.Brick], transform: BrickTransform,
                     pivot: brickedit.Vec3 | None) -> None:
    """Applies transform to bricks, in place. pivot: point the bricks are scaled and turned about, as a whole. None:
    each brick is scaled and turned in place, about its own position. transform must be valid (see is_valid)."""
    rotation = _exact_axes(rotation_axes(transform.rotation)) if transform.rotates() else None
    scale = float(transform.scale)
    for brick in bricks:
        pos = brick.pos
        if rotation is not None or scale != 1.0:
            center: TupleVec3 = brick.pos.as_tuple() if pivot is None else pivot.as_tuple()
            relative = tuple((c - p) * scale for c, p in zip(brick.pos.as_tuple(), center))
            if rotation is not None:
                relative = local_to_world(rotation, relative)  # type: ignore[arg-type]
                brick.rot = axes_to_rotation(
                    tuple(local_to_world(rotation, axis) for axis in rotation_axes(brick.rot)))  # type: ignore[arg-type]
            pos = brickedit.Vec3(*(p + r for p, r in zip(center, relative)))
            if scale != 1.0:
                scale_properties(brick, scale)
        if transform.rounds():
            round_properties(brick, transform.rounding, float(transform.round_step))
        if transform.moves():
            pos = pos + transform.offset
        brick.pos = pos
