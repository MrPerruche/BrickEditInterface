import re
from brickedit import p


KNOWN_PROPERTY_TO_DISPLAY_NAME: dict[str, str] = {
    p.B_FLUID_DYNAMIC: "Fluid Dynamic Surface"
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
