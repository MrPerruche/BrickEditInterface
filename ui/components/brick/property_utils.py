import re
from functools import cache
from collections.abc import Iterable
from brickedit import p

from ui.components.brick.materials import MATERIAL_DISPLAY_NAMES


KNOWN_PROPERTY_TO_DISPLAY_NAME: dict[str, str] = {
    p.BRICK_COLOR: "Color",
    p.BRICK_MATERIAL: "Material",
    p.BRICK_PATTERN: "Pattern",
    p.BRICK_SIZE: "Size",
    p.AMMO_TYPE: "Ammunition",
    p.B_ACCUMULATED: "Accumulate unput",
    p.B_DRIVEN: "Is driven",
    p.B_INVERT_DRIVE: "Invert direction",
    p.B_TANK_DRIVE: "Tank-style steering",
    p.CAMERA_NAME: "Camera label",
    p.CONE_ANGLE: "Cone angle",
    p.CONNECTOR_SPACING: "Connector gap",
    p.FLASH_SEQUENCE: "Flash pattern",
    p.FUEL_TYPE: "Fuel",
    p.GEAR_RATIO: "Gear reduction ratio",
    p.MIN_LIMIT: "Max contraction",
    p.MAX_LIMIT: "Max extension",
    p.NUM_FRACTIONAL_DIGITS: "Decimal digits",
    p.OWNING_SEAT: "Assigned seat",
    p.SPAWN_SCALE: "Input scale",
    p.SPEED_FACTOR: "Speed",

    p.B_FLUID_DYNAMIC: "Fluid dynamic surface"
}

def get_or_make_property_display_name(property_name: str) -> str:

    hardcoded_name = KNOWN_PROPERTY_TO_DISPLAY_NAME.get(property_name, None)
    if hardcoded_name is not None:
        return hardcoded_name

    # Remove bAbcdef (booleans)
    if len(property_name) >= 2 and property_name[0] == 'b' and property_name[1].isupper():
        property_name = property_name[1: ]

    # Split PascalCase
    property_name = (re.sub(r'(?<!^)(?=[A-Z])', ' ', property_name.replace('_', ' ')).title()).replace('.', '')

    return property_name


# ----- Enum properties (p.EnumMeta, eg. BrickMaterial): values are internal names, typed in a SuggestionLineEdit


# Hand-written names of enum values, shown next to them in suggestions (and searched). Never generated ones: internal
#  names are what users see in Brick Rigs' files and formulas
ENUM_VALUE_HINTS: dict[str, dict[str, str]] = {
    p.BRICK_MATERIAL: MATERIAL_DISPLAY_NAMES,
}
UNKNOWN_ENUM_VALUE_HINT = "modded"


@cache
def enum_values(prop: str) -> tuple[str, ...]:
    """Every value an enum property is known to take: the constants of its brickedit class (eg. p.BrickMaterial.STEEL),
    sorted. Cached: found by looking through the class's attributes."""
    meta_cls = p.pmeta_registry.get(prop)
    if not isinstance(meta_cls, type):
        return ()
    values = {getattr(meta_cls, name) for name in dir(meta_cls) if name.isupper()}
    return tuple(sorted((v for v in values if isinstance(v, str)), key=str.casefold))


def enum_suggestions(prop: str, other_values: Iterable = ()) -> list[tuple[str, str]]:
    """(value, hint) suggested for an enum property: its known values, then other_values (eg. those of the edited
    bricks) brickedit doesn't know, as modded ones. Empty values aren't suggested (nothing to type)."""
    hints = ENUM_VALUE_HINTS.get(prop, {})
    known = enum_values(prop)
    suggestions = [(value, hints.get(value, "")) for value in known if value]
    known_set = set(known)
    suggestions += [(value, UNKNOWN_ENUM_VALUE_HINT) for value in dict.fromkeys(other_values)
                    if isinstance(value, str) and value and value not in known_set]
    return suggestions
