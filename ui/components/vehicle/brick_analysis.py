"""Vehicle-wide derived facts about bricks: duplicates and mirror coherence. Qt free.

Analyses are computed once per vehicle load and configuration (see VehicleData.get_analysis), never inside
a filter's is_allowed: they look at the whole vehicle, so recomputing them per brick would be O(n²).
Results are keyed by brick.ref.id, so they stay valid for deep copies of the loaded vehicle.

Rotations follow Unreal's FRotator, which is what Brick Rigs stores: rot.x is the roll, rot.y the pitch and
rot.z the yaw, in degrees. Positions are in centimeters.
"""

from dataclasses import dataclass
from enum import Enum
from itertools import permutations, product
from math import sin, cos, radians, degrees, atan2, sqrt, floor
from struct import pack, unpack
from typing import Hashable, Iterator

import brickedit

from ui.components.vehicle.mirror_rules import (
    get_mirror_rule, mirrored_properties, LocalFlip, MirrorRule, LOCAL_FLIPS, MirrorMode
)


TupleVec3 = tuple[float, float, float]
Axes = tuple[TupleVec3, TupleVec3, TupleVec3]

AXIS_NAMES = ("X", "Y", "Z")
AXIS_KEYS = ("x", "y", "z")  # In saved files

# Two directions are considered the same if they are less than ~1° apart
SAME_DIRECTION_COS = 0.99985
MIN_TOLERANCE = 1e-4

# Brick Rigs only links exact mirror images (see MirrorAnalysis): positions within 0.0001 cm on each axis, and
#  quaternions within 0.0001 on each component, about 0.01°. Defaults of the mirror condition and action.
GAME_POSITION_TOLERANCE = 1e-4
GAME_ANGLE_TOLERANCE = 0.01  # Degrees
MIN_ANGLE_TOLERANCE = 0.001  # Float precision of saved rotations


# ---------- Rotation math


def _dot(a: TupleVec3, b: TupleVec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def rotation_axes(rot: brickedit.Vec3) -> Axes:
    """World directions of a brick's local X, Y and Z axes (rows of Unreal's FRotationMatrix)."""
    sr, cr = sin(radians(rot.x)), cos(radians(rot.x))
    sp, cp = sin(radians(rot.y)), cos(radians(rot.y))
    sy, cy = sin(radians(rot.z)), cos(radians(rot.z))
    return (
        (cp * cy, cp * sy, sp),
        (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp),
        (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp),
    )


def axes_to_rotation(axes: Axes) -> brickedit.Vec3:
    """Inverse of rotation_axes (Unreal's FMatrix::Rotator). axes must be orthonormal and right-handed."""
    x_axis, y_axis, z_axis = axes
    pitch = degrees(atan2(x_axis[2], sqrt(x_axis[0] ** 2 + x_axis[1] ** 2)))
    yaw = degrees(atan2(x_axis[1], x_axis[0]))
    no_roll_y_axis = rotation_axes(brickedit.Vec3(0.0, pitch, yaw))[1]
    roll = degrees(atan2(_dot(z_axis, no_roll_y_axis), _dot(y_axis, no_roll_y_axis)))
    return brickedit.Vec3(_clean_angle(roll), _clean_angle(pitch), _clean_angle(yaw))


def _clean_angle(angle: float) -> float:
    """Rounds away float noise (eg. 89.99999999 -> 90.0, -0.0 -> 0.0) so mirrored bricks get tidy rotations."""
    rounded = round(angle, 6)
    return 0.0 if rounded == 0 else rounded


def same_orientation(a: Axes, b: Axes, min_cos: float = SAME_DIRECTION_COS) -> bool:
    """Whether each local axis of a and b are within the angle whose cosine is min_cos"""
    return all(_dot(a[i], b[i]) >= min_cos for i in range(3))


def _reflect(v: TupleVec3, axis: int) -> TupleVec3:
    return tuple(-c if i == axis else c for i, c in enumerate(v))  # type: ignore[return-value]


def reflect_axes(axes: Axes, axis: int) -> Axes:
    """Mirror image of a brick's local axes. The result is left-handed (not a rotation)."""
    return _reflect(axes[0], axis), _reflect(axes[1], axis), _reflect(axes[2], axis)


def mirror_position(pos: brickedit.Vec3, axis: int, plane_offset: float) -> brickedit.Vec3:
    coords = list(pos.as_tuple())
    coords[axis] = 2.0 * plane_offset - coords[axis]
    return brickedit.Vec3(*coords)


def mirror_axes(axes: Axes, axis: int, flip: LocalFlip) -> Axes:
    """Local axes of the mirror image of a brick (see mirror_rules)"""
    return flip.apply(reflect_axes(axes, axis))


def mirror_rotation(rot: brickedit.Vec3, axis: int, flip: LocalFlip = LOCAL_FLIPS[MirrorMode.NONE]) -> brickedit.Vec3:
    """Rotation of the mirror image of a brick. A mirror image can't be expressed as a rotation, so it's turned back
    into one by a reflection in the brick's own space, which depends on the brick type (see mirror_rules)."""
    return axes_to_rotation(mirror_axes(rotation_axes(rot), axis, flip))


def local_to_world(axes: Axes, v: TupleVec3) -> TupleVec3:
    """World direction of v, given in the space of a brick whose local axes are axes. Also rotates v by the rotation
    whose axes are axes (see brick_transform)."""
    return tuple(v[0] * axes[0][k] + v[1] * axes[1][k] + v[2] * axes[2][k] for k in range(3))  # type: ignore[return-value]


def mirror_transform(brick: brickedit.Brick, axis: int, plane_offset: float, rule: MirrorRule | None = None,
                     axes: Axes | None = None) -> tuple[brickedit.Vec3, Axes]:
    """Position and local axes of the mirror image of a brick across the plane normal to axis at plane_offset."""
    rule = get_mirror_rule(brick) if rule is None else rule
    axes = rotation_axes(brick.rot) if axes is None else axes
    image_axes = mirror_axes(axes, axis, rule.flip)
    pos = mirror_position(brick.pos, axis, plane_offset)
    if not any(rule.rotation_origin):
        return pos, image_axes
    # Measured in game (see mirror_rules.MirrorRule.rotation_origin)
    offset = local_to_world(image_axes, rule.rotation_origin)
    return brickedit.Vec3(pos.x + offset[0], pos.y + offset[1], pos.z + offset[2]), image_axes


def _brick_size(brick: brickedit.Brick) -> TupleVec3 | None:
    try:
        size = brick.get_property(brickedit.p.BRICK_SIZE)
    except brickedit.BrickError:
        return None
    return size.as_tuple() if isinstance(size, brickedit.Vec3) else None


def mirror_coherent(axes: Axes, size: TupleVec3 | None, other_axes: Axes, other_size: TupleVec3 | None,
                    axis: int, size_tolerance: float, flip: LocalFlip = LOCAL_FLIPS[MirrorMode.NONE],
                    min_cos: float = SAME_DIRECTION_COS, turned: bool = True) -> bool:
    """Whether other is oriented and sized like the mirror image of a brick (see mirror_axes): each local axis
    within the angle whose cosine is min_cos.

    turned: also accept other turned in a way that only looks the same if the brick is symmetric. Each local axis
    may be reversed, and for sized bricks the local axes may be swapped as long as the sizes are swapped with them
    (eg. a 30x60 plate rotated by 90° is also a 60x30 plate). Brick Rigs doesn't: it only links exact images."""
    expected = mirror_axes(axes, axis, flip)
    expected_size = None if size is None else flip.size(size)
    sized = expected_size is not None and other_size is not None
    orders = permutations(range(3)) if turned and sized else ((0, 1, 2),)
    for order in orders:
        dots = (_dot(expected[i], other_axes[order[i]]) for i in range(3))
        if all((abs(d) if turned else d) >= min_cos for d in dots) and (
            expected_size is None or other_size is None or
            all(abs(expected_size[i] - other_size[order[i]]) <= size_tolerance for i in range(3))
        ):
            return True
    return False


# ---------- Properties


def _freeze(value) -> Hashable:
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


_MISSING = object()

def _is_reference_property(prop: str) -> bool:
    meta = brickedit.p.pmeta_registry.get(prop)
    return isinstance(meta, type) and issubclass(meta, (brickedit.p.SourceBricksMeta, brickedit.p.SingleSourceBrickMeta))


_reference_property_cache: dict[str, bool] = {}

def is_reference_property(prop: str) -> bool:
    """Properties pointing to other bricks (input sources, owning seat...)."""
    cached = _reference_property_cache.get(prop)
    if cached is None:
        cached = _reference_property_cache[prop] = _is_reference_property(prop)
    return cached


def properties_key(brick: brickedit.Brick, ignored: frozenset[str] = frozenset(),
                   ppatch: dict[str, Hashable] | None = None) -> tuple:
    """Hashable summary of a brick's non-default properties. Two bricks of the same type have equal keys if
    and only if all their properties (except ignored ones) are equal. ppatch replaces the brick's own if given."""
    defaults = brick.meta().p
    items = []
    for prop, value in (brick.ppatch if ppatch is None else ppatch).items():
        if value is None or prop in ignored:
            continue
        if defaults.get(prop, _MISSING) == value:
            continue  # Explicitly set to its default value: same as not set
        items.append((prop, _freeze(value)))
    items.sort(key=lambda item: item[0])
    return tuple(items)


def brick_color(brick: brickedit.Brick) -> int | None:
    try:
        return brick.get_property(brickedit.p.BRICK_COLOR)
    except brickedit.BrickError:
        return None


# ---------- Spatial hashing


class _SpatialHash:
    """Finds items closer than tolerance (on every axis) to a position. Items are grouped by an arbitrary
    hashable key (eg. brick type): only items sharing the key are returned."""

    def __init__(self, tolerance: float):
        self.tolerance = max(tolerance, MIN_TOLERANCE)
        self.cell = max(10.0, self.tolerance * 4.0)
        self.cells: dict[tuple, list] = {}

    def _cell_coords(self, value: float) -> tuple[int, ...]:
        scaled = value / self.cell
        c = floor(scaled)
        offsets = [c]
        if (scaled - c) * self.cell <= self.tolerance:
            offsets.append(c - 1)
        if (c + 1 - scaled) * self.cell <= self.tolerance:
            offsets.append(c + 1)
        return tuple(offsets)

    def add(self, key: Hashable, pos: TupleVec3, item) -> None:
        cell = (key, floor(pos[0] / self.cell), floor(pos[1] / self.cell), floor(pos[2] / self.cell))
        self.cells.setdefault(cell, []).append((pos, item))

    def query(self, key: Hashable, pos: TupleVec3) -> Iterator:
        tol = self.tolerance
        for cx, cy, cz in product(self._cell_coords(pos[0]), self._cell_coords(pos[1]), self._cell_coords(pos[2])):
            for other_pos, item in self.cells.get((key, cx, cy, cz), ()):
                if (abs(other_pos[0] - pos[0]) <= tol and abs(other_pos[1] - pos[1]) <= tol
                        and abs(other_pos[2] - pos[2]) <= tol):
                    yield item


# ---------- Duplicates


class DuplicateComparison(Enum):
    EVERYTHING = 0
    IGNORE_COLOR = 1
    TYPE_ONLY = 2

    def display_name(self) -> str:
        """Short: shown in narrow combo boxes. Explained by the duplicate filter's tooltip."""
        return {
            DuplicateComparison.EVERYTHING: "Everything",
            DuplicateComparison.IGNORE_COLOR: "All but color",
            DuplicateComparison.TYPE_ONLY: "Type & transform",
        }[self]


@dataclass(frozen=True, slots=True)
class DuplicateInfo:
    occurrence: int  # 1 for the first brick (in file order) of its duplicate group, 2 for the next one...
    group_size: int  # 1 if the brick has no duplicate


class DuplicateAnalysis:
    """Bricks are duplicates if they have the same type, the same position (within tolerance), the same
    orientation (each local axis within angle_tolerance, in degrees) and (depending on comparison) the same
    properties. Groups are transitive.

    The occurrence index is computed over the whole vehicle, never relative to another filter: "is a duplicate"
    (occurrence > 1) combined with "beyond the first N" (occurrence > N) can't spare the wrong brick."""

    def __init__(self, bricks: list[brickedit.Brick], comparison: DuplicateComparison, tolerance: float,
                 angle_tolerance: float):
        self.comparison = comparison
        self.tolerance = max(tolerance, MIN_TOLERANCE)
        self.min_cos = cos(radians(max(angle_tolerance, MIN_ANGLE_TOLERANCE)))
        self.info: dict[str, DuplicateInfo] = {}
        self.group_count = 0  # Number of groups with at least 2 bricks
        self._analyze(bricks)

    def _key(self, brick: brickedit.Brick) -> Hashable:
        name = brick.meta().name()
        if self.comparison == DuplicateComparison.TYPE_ONLY:
            return name
        ignored = frozenset({brickedit.p.BRICK_COLOR}) if self.comparison == DuplicateComparison.IGNORE_COLOR else frozenset()
        return name, properties_key(brick, ignored)

    def _analyze(self, bricks: list[brickedit.Brick]):
        parent = list(range(len(bricks)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        spatial = _SpatialHash(self.tolerance)
        axes_list = [rotation_axes(b.rot) for b in bricks]

        for i, brick in enumerate(bricks):
            key = self._key(brick)
            pos = brick.pos.as_tuple()
            for j in spatial.query(key, pos):
                if same_orientation(axes_list[i], axes_list[j], self.min_cos):
                    root_i, root_j = find(i), find(j)
                    if root_i != root_j:
                        parent[max(root_i, root_j)] = min(root_i, root_j)
            spatial.add(key, pos, i)

        groups: dict[int, list[int]] = {}
        for i in range(len(bricks)):
            groups.setdefault(find(i), []).append(i)

        for members in groups.values():
            if len(members) > 1:
                self.group_count += 1
            for occurrence, i in enumerate(members, start=1):  # members are in file order
                self.info[bricks[i].ref.id] = DuplicateInfo(occurrence, len(members))

    def get(self, brick: brickedit.Brick) -> DuplicateInfo | None:
        return self.info.get(brick.ref.id)


# ---------- Mirrors


class MirrorSide(Enum):
    NEGATIVE = -1
    ON_PLANE = 0
    POSITIVE = 1


@dataclass(slots=True)
class MirrorInfo:
    side: MirrorSide
    # ref.id of the mirrored brick. Bricks on the mirror plane are their own counterpart, unless they're paired with a
    #  brick on the plane which is their mirror image (eg. two stacked panels)
    counterpart: str | None
    rotation_ok: bool = True  # Orientation and size (see mirror_coherent)
    color_ok: bool = True
    properties_ok: bool = True

    @property
    def missing(self) -> bool:
        return self.counterpart is None

    @property
    def has_issue(self) -> bool:
        return self.missing or not (self.rotation_ok and self.color_ok and self.properties_ok)


class MirrorAnalysis:
    """Pairs every brick with the brick of its mirrored type (the same type, or its left / right version) located at
    its mirrored position (within tolerance), and checks whether the pair is coherent (mirrored orientation, same
    color, same other properties once mirrored following the brick's MirrorRule, see mirror_rules).

    Pairing is one to one: if two identical bricks are stacked on one side and a single one is on the other, one
    of the two is reported as missing a counterpart. Perfect pairs are made first (like Brick Rigs, which only pairs
    perfect mirror images), then the remaining bricks are paired with their most coherent candidate.
    Properties pointing to other bricks (input sources...) are not compared.

    A brick on the mirror plane (within tolerance) is its own counterpart if it's its own mirror image. Otherwise it
    is paired like other bricks, eg. with a brick stacked on it which is its mirror image; without one, its
    orientation is reported as wrong. Like in Brick Rigs, a pair always has one brick below the plane and the other
    at or above it: two bricks stacked exactly on the plane (eg. at 0.0 and -0.0) are never paired. See
    ignore/MIRRORING.md.

    By default, the analysis is as strict as Brick Rigs: positions within 0.0001 cm (tolerance), rotations within
    0.01° (angle_tolerance), no turned symmetric bricks (turned, see mirror_coherent). Larger tolerances accept
    vehicles built by hand. The rotation of a brick on the plane is always checked with turned: Brick Rigs never
    pairs a brick with itself, and a symmetric brick across the plane is often its own mirror image once turned."""

    def __init__(self, bricks: list[brickedit.Brick], axis: int, plane_offset: float,
                 tolerance: float = GAME_POSITION_TOLERANCE, angle_tolerance: float = GAME_ANGLE_TOLERANCE,
                 turned: bool = False):
        self.axis = axis
        self.plane_offset = plane_offset
        self.tolerance = max(tolerance, MIN_TOLERANCE)
        self.min_cos = cos(radians(max(angle_tolerance, MIN_ANGLE_TOLERANCE)))
        self.turned = turned
        self.info: dict[str, MirrorInfo] = {}
        self._analyze(bricks)

    @staticmethod
    def cached(vehicle_data, axis: int, plane_offset: float, tolerance: float = GAME_POSITION_TOLERANCE,
               angle_tolerance: float = GAME_ANGLE_TOLERANCE, turned: bool = False) -> "MirrorAnalysis":
        """The analysis of vehicle_data's vehicle (a VehicleData), computed once per vehicle load and settings"""
        # Settings come from float32 fields or float constants: the same value must give the same key
        plane_offset, tolerance, angle_tolerance = (unpack("<f", pack("<f", v))[0]
                                                    for v in (plane_offset, tolerance, angle_tolerance))
        return vehicle_data.get_analysis(
            ("mirror", axis, plane_offset, tolerance, angle_tolerance, turned),
            lambda: MirrorAnalysis(vehicle_data.brvfile.bricks, axis, plane_offset, tolerance, angle_tolerance, turned)
        )

    def side_of(self, pos: brickedit.Vec3) -> MirrorSide:
        delta = pos.as_tuple()[self.axis] - self.plane_offset
        if abs(delta) <= self.tolerance:
            return MirrorSide.ON_PLANE
        return MirrorSide.POSITIVE if delta > 0 else MirrorSide.NEGATIVE

    def _analyze(self, bricks: list[brickedit.Brick]):
        axis = self.axis
        # Sizes are checked with the orientation: a mirrored brick may be turned by 90° with its size swapped
        ignored = frozenset({brickedit.p.BRICK_COLOR, brickedit.p.BRICK_SIZE})
        axes_list = [rotation_axes(b.rot) for b in bricks]
        sizes = [_brick_size(b) for b in bricks]
        colors = [brick_color(b) for b in bricks]
        props: list[tuple | None] = [None] * len(bricks)
        mirrored_props: list[tuple | None] = [None] * len(bricks)

        def comparable(i: int, ppatch: dict[str, Hashable] | None) -> tuple:
            key = properties_key(bricks[i], ignored, ppatch)
            return tuple(item for item in key if not is_reference_property(item[0]))

        def props_of(i: int) -> tuple:
            if props[i] is None:
                props[i] = comparable(i, None)
            return props[i]  # type: ignore[return-value]

        rules = [get_mirror_rule(b) for b in bricks]

        def mirrored_props_of(i: int) -> tuple:
            """Properties i's counterpart is expected to have"""
            if mirrored_props[i] is None:
                rule = rules[i]
                mirrored_props[i] = props_of(i) if not rule.properties else comparable(i, mirrored_properties(bricks[i], rule))
            return mirrored_props[i]  # type: ignore[return-value]

        spatial = _SpatialHash(self.tolerance)
        sides = []
        # Brick Rigs only pairs a brick below the plane with one at or above it, even within tolerance of the plane
        #  (two bricks stacked exactly on it, even at 0.0 and -0.0, are never paired)
        below = [brick.pos.as_tuple()[axis] < self.plane_offset for brick in bricks]
        own_counterpart = []  # Bricks on the plane which are their own mirror image
        for i, brick in enumerate(bricks):
            side = self.side_of(brick.pos)
            sides.append(side)
            # Only its orientation can break the symmetry of a brick on the plane
            own_counterpart.append(side == MirrorSide.ON_PLANE and rules[i].mirrored_type == brick.meta().name()
                                   and mirror_coherent(axes_list[i], sizes[i], axes_list[i], sizes[i], axis,
                                                       self.tolerance, rules[i].flip, self.min_cos, turned=True))
            if not own_counterpart[i]:
                spatial.add(brick.meta().name(), brick.pos.as_tuple(), i)

        paired = [False] * len(bricks)

        def candidates(i: int) -> Iterator[tuple[bool, bool, bool, int]]:
            """(rotation_ok, color_ok, properties_ok, -j) of every unpaired brick j at the mirrored position of i.
            Includes bricks on the plane: two bricks stacked on it can be each other's mirror image."""
            rule = rules[i]
            if any(rule.rotation_origin):
                target, _ = mirror_transform(bricks[i], axis, self.plane_offset, rule, axes_list[i])
            else:
                target = mirror_position(bricks[i].pos, axis, self.plane_offset)
            for j in spatial.query(rule.mirrored_type, target.as_tuple()):
                if j == i or paired[j] or below[j] == below[i]:
                    continue
                yield (mirror_coherent(axes_list[i], sizes[i], axes_list[j], sizes[j], axis, self.tolerance, rule.flip,
                                       self.min_cos, self.turned),
                       colors[i] == colors[j], mirrored_props_of(i) == props_of(j), -j)

        def pair(i: int, j: int, rotation_ok: bool, color_ok: bool, properties_ok: bool):
            paired[i] = paired[j] = True
            self.info[bricks[i].ref.id] = MirrorInfo(sides[i], bricks[j].ref.id, rotation_ok, color_ok, properties_ok)
            self.info[bricks[j].ref.id] = MirrorInfo(sides[j], bricks[i].ref.id, rotation_ok, color_ok, properties_ok)

        # Perfect pairs first: with bricks stacked on both sides, a brick mustn't take the mirror image of another
        no_candidate = [False] * len(bricks)  # Stays true: candidates can only get paired
        for i, brick in enumerate(bricks):
            if own_counterpart[i]:
                self.info[brick.ref.id] = MirrorInfo(sides[i], brick.ref.id)
            elif not paired[i]:
                scores = list(candidates(i))
                no_candidate[i] = not scores
                perfect = max((score for score in scores if all(score[:3])), default=None)
                if perfect is not None:
                    pair(i, -perfect[3], True, True, True)

        # Then the most coherent of the remaining candidates
        for i, brick in enumerate(bricks):
            if paired[i] or own_counterpart[i]:
                continue
            best = None if no_candidate[i] else max(candidates(i), default=None)
            if best is not None:
                pair(i, -best[3], *best[:3])
            elif sides[i] == MirrorSide.ON_PLANE and rules[i].mirrored_type == brick.meta().name():
                # Neither its own mirror image nor paired with one: its orientation breaks the symmetry
                self.info[brick.ref.id] = MirrorInfo(sides[i], brick.ref.id, rotation_ok=False)
            else:
                self.info[brick.ref.id] = MirrorInfo(sides[i], None)

    def get(self, brick: brickedit.Brick) -> MirrorInfo | None:
        return self.info.get(brick.ref.id)
