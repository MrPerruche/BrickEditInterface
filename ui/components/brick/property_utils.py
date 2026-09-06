import re
from brickedit import p


KNOWN_PROPERTY_TO_DISPLAY_NAME: dict[str, str] = {
    # p.BRICK_COLOR: "Color",
    # p.BRICK_MATERIAL: "Material",
    # p.BRICK_PATTERN: "Pattern",
    # p.BRICK_SIZE: "Size",
    # p.AMMO_TYPE: "Ammunition",
    # p.B_ACCUMULATED: "Accumulate unput",
    # p.B_DRIVEN: "Is driven",
    # p.B_INVERT_DRIVE: "Invert direction",
    # p.B_TANK_DRIVE: "Tank-style steering",
    # p.CAMERA_NAME: "Camera label",
    # p.CONE_ANGLE: "Cone angle",
    # p.CONNECTOR_SPACING: "Connector gap",
    # p.FLASH_SEQUENCE: "Flash pattern",
    # p.FUEL_TYPE: "Fuel",
    # p.GEAR_RATIO: "Gear reduction ratio",
    # p.MIN_LIMIT: "Max contraction",
    # p.MAX_LIMIT: "Max extension",
    # p.NUM_FRACTIONAL_DIGITS: "Decimal digits",
    # p.OWNING_SEAT: "Assigned seat",
    # p.SPAWN_SCALE: "Input scale",
    # p.SPEED_FACTOR: "Speed",

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
