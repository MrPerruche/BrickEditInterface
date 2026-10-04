"""Structural edits of a BRVFile (removing and adding bricks) which keep it serializable. Qt free."""

from copy import deepcopy
from itertools import count
from typing import Hashable, Iterable

import brickedit

from ui.components.vehicle.brick_analysis import mirror_transform, axes_to_rotation, is_reference_property
from ui.components.vehicle.mirror_rules import get_mirror_rule, mirrored_properties


def remove_bricks(brvfile: brickedit.BRVFile, ref_ids: set[str]) -> int:
    """Removes the bricks whose ref.id is in ref_ids. References to them (input sources, owning seat...) held
    by the remaining bricks are removed too: serializing a reference to a missing brick fails.
    Returns the number of bricks removed."""
    before = len(brvfile.bricks)
    brvfile.bricks = [brick for brick in brvfile.bricks if brick.ref.id not in ref_ids]
    removed = before - len(brvfile.bricks)
    if removed:
        scrub_references(brvfile.bricks, ref_ids)
    return removed


def scrub_references(bricks: Iterable[brickedit.Brick], ref_ids: set[str]):
    """Removes every reference to ref_ids held by bricks' properties."""
    for brick in bricks:
        for prop, value in list(brick.ppatch.items()):
            if value is None or not is_reference_property(prop):
                continue
            if isinstance(value, tuple):
                kept = tuple(ref for ref in value if ref not in ref_ids)
                if len(kept) != len(value):
                    brick.set_property(prop, kept)
            elif value in ref_ids:
                brick.reset_property(prop)


def remap_references(bricks: Iterable[brickedit.Brick], mapping: dict[str, str]):
    """Makes every reference held by bricks' properties to a key of mapping point to its value instead."""
    if not mapping:
        return
    for brick in bricks:
        for prop, value in list(brick.ppatch.items()):
            if value is None or not is_reference_property(prop):
                continue
            if isinstance(value, tuple):
                remapped = tuple(mapping.get(ref, ref) for ref in value)
                if remapped != value:
                    brick.set_property(prop, remapped)
            elif value in mapping:
                brick.set_property(prop, mapping[value])


class IdAllocator:
    """Hands out ref ids (and group ids) unused by a vehicle. Ids are reassigned when the vehicle is saved and
    reloaded, they only have to be unique."""

    def __init__(self, brvfile: brickedit.BRVFile, prefix: str = "rbe"):
        self.prefix = prefix
        self.used: set[str] = set()
        for brick in brvfile.bricks:
            self.used.add(brick.ref.id)
            if brick.ref.weld is not None:
                self.used.add(brick.ref.weld)
            if brick.ref.editor is not None:
                self.used.add(brick.ref.editor)
        self._counter = count()

    def new(self, kind: str = "brick") -> str:
        while True:
            candidate = f"{self.prefix}_{kind}_{next(self._counter)}"
            if candidate not in self.used:
                self.used.add(candidate)
                return candidate


def copy_brick(brick: brickedit.Brick, ids: IdAllocator, keep_groups: bool,
               pos: brickedit.Vec3 | None = None, rot: brickedit.Vec3 | None = None,
               ppatch: dict[str, Hashable] | None = None, meta: brickedit.bt.BrickMeta | None = None) -> brickedit.Brick:
    """New brick identical to brick, except for what is given."""
    return brickedit.Brick(
        ref=brickedit.ID(
            ids.new(),
            brick.ref.weld if keep_groups else None,
            brick.ref.editor if keep_groups else None,
        ),
        meta=brick.meta() if meta is None else meta,
        pos=brick.pos if pos is None else pos,
        rot=brick.rot if rot is None else rot,
        ppatch=deepcopy(brick.ppatch if ppatch is None else ppatch),
    )


def mirror_brick(brick: brickedit.Brick, axis: int, plane_offset: float, ids: IdAllocator,
                 keep_groups: bool) -> brickedit.Brick:
    """New brick, mirror image of brick across the plane normal to axis at plane_offset (see mirror_rules)."""
    rule = get_mirror_rule(brick)
    pos, axes = mirror_transform(brick, axis, plane_offset, rule)
    meta = brick.meta()
    return copy_brick(
        brick, ids, keep_groups,
        pos=pos,
        rot=axes_to_rotation(axes),
        ppatch=mirrored_properties(brick, rule),
        meta=meta if rule.mirrored_type == meta.name() else brickedit.bt.bt_registry[rule.mirrored_type],
    )
