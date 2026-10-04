"""How bricks are mirrored, following Brick Rigs' own rules.

Mirroring a brick reflects its position and local axes across the mirror plane. Reflected axes are left-handed, so
they aren't a rotation: Brick Rigs turns them back into one with a reflection in the brick's own space (LocalFlip),
chosen by the brick type's mirror mode, from the game's data (mirror_data.py, see ignore/extract_mirror_data.py):

    NONE             Flips the local Y axis. Most bricks: they face X and are symmetric left to right.
    Y_FORWARD        Flips the local X axis. Bricks facing Y: some axles, mudguards, spinners, text bricks...
    XY_SYMMETRY      Swaps the local X and Y axes. Corners, symmetric across their diagonal.
    XY_NEG_SYMMETRY  Swaps the local X and Y axes and reverses both. Symmetric across their other diagonal.
    Z_FORWARD        Unused by the game's bricks. Assumed to flip the local Y axis.

The flip only depends on the brick type, not on its rotation or on the mirror axis (checked on ~90000 mirrored
bricks of saved vehicles). On top of that:
- Left and right versions of a brick (eg. Wing_2x2x1s_L and Wing_2x2x1s_R) are each other's mirror image.
- A few bricks are moved by their rotation origin when mirrored (two actuator parts).
- Brick sizes and connector spacings follow the local flip (eg. a 30x60 corner becomes 60x30), and spinner angles
  are inverted. See the property rules below.

All of this was checked against Brick Rigs' own mirror images of every brick type (ignore/mirror_ground_truth.py),
which also showed what the game does NOT change: light directions, seat exit locations, axles' drive inversion,
wheels' tank steering inversion, and actuator, flap and thruster settings.

Corrections and new quirks go below (MODE_OVERRIDES, PROPERTIES_BY_CLASS, PROPERTIES_BY_TYPE). Only add rules checked
in game.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Hashable, Mapping

import brickedit
from brickedit import bt, p

from ui.components.vehicle.mirror_data import MIRROR_MODES, MIRROR_ROTATION_ORIGINS


TupleVec3 = tuple[float, float, float]


class MirrorMode(Enum):
    NONE = 0
    Y_FORWARD = 1
    Z_FORWARD = 2
    XY_SYMMETRY = 3
    XY_NEG_SYMMETRY = 4


@dataclass(frozen=True)
class LocalFlip:
    """A reflection in a brick's own space, turning the reflected local axes of a brick into the local axes of its
    mirror image. axes[j] = (i, sign): the image's local axis j is sign times the reflected local axis i."""

    axes: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]

    def apply(self, reflected: tuple[TupleVec3, TupleVec3, TupleVec3]) -> tuple[TupleVec3, TupleVec3, TupleVec3]:
        return tuple(tuple(sign * c for c in reflected[i]) for i, sign in self.axes)  # type: ignore[return-value]

    def size(self, size: TupleVec3) -> TupleVec3:
        return tuple(size[i] for i, _ in self.axes)  # type: ignore[return-value]

    def direction(self, axis: int, sign: int) -> tuple[int, int]:
        """Mirror image of a local direction (axis, sign), in the image's local space"""
        for j, (i, s) in enumerate(self.axes):
            if i == axis:
                return j, s * sign
        raise ValueError(f"Invalid axis {axis}")


LOCAL_FLIPS: dict[MirrorMode, LocalFlip] = {
    MirrorMode.NONE: LocalFlip(((0, 1), (1, -1), (2, 1))),
    MirrorMode.Y_FORWARD: LocalFlip(((0, -1), (1, 1), (2, 1))),
    MirrorMode.Z_FORWARD: LocalFlip(((0, 1), (1, -1), (2, 1))),  # Unverified, no brick uses it
    MirrorMode.XY_SYMMETRY: LocalFlip(((1, 1), (0, 1), (2, 1))),
    MirrorMode.XY_NEG_SYMMETRY: LocalFlip(((1, -1), (0, -1), (2, 1))),
}


# ---------- Property transforms: (value, local flip) -> mirrored value


PropertyTransform = Callable[[Hashable, LocalFlip], Hashable]


def negate(value, flip: LocalFlip):
    """Mirrored value of a signed number or vector (eg. an angle)"""
    return -value if not isinstance(value, brickedit.Vec2 | brickedit.Vec3) else value * -1.0


def local_size(value, flip: LocalFlip):
    return brickedit.Vec3(*flip.size(value.as_tuple())) if isinstance(value, brickedit.Vec3) else value


def connector_spacing(value, flip: LocalFlip):
    """Connector spacing holds 2 bits per face: +X, -X, +Y, -Y, +Z, -Z, from the lowest bits. (Whether + or - comes
    first doesn't matter here: a reflection maps both faces of an axis to both faces of an axis.)"""
    if not isinstance(value, int) or isinstance(value, bool):
        return value
    result = value & ~0xFFF
    for axis in range(3):
        for half, sign in ((0, 1), (1, -1)):
            face_bits = (value >> (2 * (2 * axis + half))) & 0b11
            new_axis, new_sign = flip.direction(axis, sign)
            result |= face_bits << (2 * (2 * new_axis + (0 if new_sign > 0 else 1)))
    return result


def unchanged(value, flip: LocalFlip):
    """Cancels a rule of LOCAL_PROPERTIES for a class or type"""
    return value


# ---------- Rules


# Properties in the brick's own space, mirrored for every brick having them
LOCAL_PROPERTIES: dict[str, PropertyTransform] = {
    p.BRICK_SIZE: local_size,
    p.CONNECTOR_SPACING: connector_spacing,
}

PROPERTIES_BY_CLASS: dict[type[bt.BrickMeta], dict[str, PropertyTransform]] = {
    # Spinners' connector spacing doesn't follow the usual faces and is kept as is
    bt.SpinnerBrickMeta: {p.SPINNER_ANGLE: negate, p.CONNECTOR_SPACING: unchanged},
}

PROPERTIES_BY_TYPE: dict[str, dict[str, PropertyTransform]] = {
    # 'SomeBrickType': {p.SOME_PROPERTY: negate},
}

MODE_OVERRIDES: dict[str, MirrorMode] = {
    # 'SomeBrickType': MirrorMode.Y_FORWARD,  # Corrects or completes mirror_data.MIRROR_MODES
}

MIRRORED_TYPE_OVERRIDES: dict[str, str] = {
    # 'SomeLeftBrick': 'SomeRightBrick', 'SomeRightBrick': 'SomeLeftBrick',  # Pairs not named with L / R
}

_SIDES = {"L": "R", "R": "L"}


def other_side_type(name: str) -> str | None:
    """Name of the left version of a right brick type and vice versa (an "L" or "R" part of the name, eg.
    Door_L_3x1x1 / Door_R_3x1x1, or MIRRORED_TYPE_OVERRIDES), if it exists"""
    if name in MIRRORED_TYPE_OVERRIDES:
        return MIRRORED_TYPE_OVERRIDES[name]
    parts = name.split("_")
    swapped = [_SIDES.get(part, part) for part in parts]
    if swapped == parts:
        return None
    other = "_".join(swapped)
    return other if other in bt.bt_registry else None


@dataclass(frozen=True)
class MirrorRule:
    mode: MirrorMode
    mirrored_type: str
    """Type name of the mirror image: the brick's own, or its left / right counterpart"""
    rotation_origin: TupleVec3
    """Brick Rigs' MirrorRotationOrigin (local, cm). Measured in game: the mirror image is moved by this vector,
    turned like the image (only checked for origins along the flipped local axis, the only ones in the game)."""
    properties: Mapping[str, PropertyTransform]
    """Properties whose value changes when the brick is mirrored, and how"""

    @property
    def flip(self) -> LocalFlip:
        return LOCAL_FLIPS[self.mode]


_rules: dict[str, MirrorRule] = {}


def _make_rule(meta: bt.BrickMeta) -> MirrorRule:
    name = meta.name()
    mode = MODE_OVERRIDES.get(name)
    if mode is None:
        # A mode added by a game update and unknown here yet (ignore/extract_mirror_data.py warns about it)
        mode = MirrorMode.__members__.get(MIRROR_MODES.get(name, ""), MirrorMode.NONE)
    properties = {prop: transform for prop, transform in LOCAL_PROPERTIES.items() if prop in meta.p}
    properties |= PROPERTIES_BY_CLASS.get(type(meta), {})
    properties |= PROPERTIES_BY_TYPE.get(name, {})
    return MirrorRule(
        mode=mode,
        mirrored_type=other_side_type(name) or name,
        rotation_origin=MIRROR_ROTATION_ORIGINS.get(name, (0.0, 0.0, 0.0)),
        properties=properties,
    )


def get_mirror_rule(brick: brickedit.Brick) -> MirrorRule:
    meta = brick.meta()
    rule = _rules.get(meta.name())
    if rule is None:
        rule = _rules[meta.name()] = _make_rule(meta)
    return rule


def mirrored_properties(brick: brickedit.Brick, rule: MirrorRule | None = None) -> dict[str, Hashable]:
    """The ppatch of the mirror image of brick (a new dict, brick is not modified)."""
    rule = get_mirror_rule(brick) if rule is None else rule
    ppatch = dict(brick.ppatch)
    flip = rule.flip
    for prop, transform in rule.properties.items():
        try:
            value = brick.get_property(prop)
        except brickedit.BrickError:
            continue  # This type doesn't have the property
        if value is None:
            continue
        mirrored = transform(value, flip)
        if mirrored != value or prop in ppatch:
            ppatch[prop] = mirrored
    return ppatch
