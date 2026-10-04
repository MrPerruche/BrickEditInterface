"""Property edits as data, to save the brick property editor's edits (eg. in the "Edit properties" action of rule
presets) and apply them again to other bricks.

An edit is what a property widget changes (BasePropertyWidget.get_edit / apply_edit), in one of these forms:

    {"value": v}                 Sets the property to v (TOML form, see below). Any widget.
    {"formula": [f, ...]}        One formula per channel, evaluated for each brick (eg. ["x * 2", "y", "z"]). Number,
                                 vector and color properties. Colors add "color_space": "rgb" or "hsv".
    {"invert": true}             Inverts an on/off property.

Values: numbers, [x, y] / [x, y, z] lists, true / false, text, "RRGGBBAA" colors, and "0A FF" hexadecimal bytes for
properties BEI doesn't know. Formulas and inverting need a widget in formula mode: PropertySet shows the properties
having one in formula mode, whatever the selection. A value edit can be applied in both modes.

Edits come from files made by anyone: read_edit checks them fully before they're used.
"""

from ui.components.brick.property_widgets import BasePropertyWidget
from systems.bei_files import ConfigReader, BeiFileError

EDIT_KEYS = ("value", "formula", "invert", "color_space")


def needs_formula_mode(edit: dict) -> bool:
    return "formula" in edit or "invert" in edit


def check_edit(widget_cls: type[BasePropertyWidget], edit: dict) -> None:
    """Raises ValueError if edit can't be applied by a widget of widget_cls, in every mode it may be applied in"""
    example = widget_cls.get_example_value()
    for formula_mode in (True,) if needs_formula_mode(edit) else (False, True):
        widget = widget_cls("", (example,), formula_mode, None if formula_mode else example, show_text=False)
        try:
            widget.apply_edit(edit)
        finally:
            widget.deleteLater()


def read_edit(table: ConfigReader, widget_cls: type[BasePropertyWidget] | None, name: str) -> dict:
    """The edit of a table read from a file (its other keys are ignored). Raises BeiFileError if it's invalid.
    widget_cls: the class of the property's widget (None: the property can't be edited)."""
    if widget_cls is None:
        raise BeiFileError(f"{table.where}: \"{name}\" can't be edited.")
    edit = {key: table.data[key] for key in EDIT_KEYS if key in table.data}
    try:
        check_edit(widget_cls, edit)
    except ValueError as e:
        raise BeiFileError(f"{table.where}: \"{name}\": {e}.") from None
    return edit
