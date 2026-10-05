"""Presets: conditions and actions, one click away. Using a preset only fills the menu in: the user reviews the
selection and applies it themselves (duplicate and mirror detection are heuristics and can be wrong).

Built-in presets and the user's own presets (.beirules files, see systems.bei_files) are the same thing: the
content of a .beirules file. Content of a preset (format version 1):

    name = "Remove exact duplicates"
    description = "..."
    invert = false                  # Invert selection
    [[conditions]]                  # Any number, in order
    type = "duplicate"              # BaseFilter.CONFIG_TYPE
    mode = "must"                   # must, must_not, should, should_not
    ...                             # The filter's settings (BaseFilter.get_config)
    [[actions]]                     # At least one, in order
    type = "delete"                 # BaseAction.CONFIG_TYPE
    ...                             # The action's settings (BaseAction.get_config)
"""

from dataclasses import dataclass
from pathlib import Path

from ui.components.brick_filter.filters import FilterMode, BaseFilter, filters_by_config_type
from ui.components.vehicle.brick_analysis import GAME_POSITION_TOLERANCE, GAME_ANGLE_TOLERANCE

from brickedit import p
from systems.bei_files import BeiFileFormat, BeiFileError, ConfigReader, FileLibrary, enum_key

from menus.rule_based_editor.actions import BaseAction, actions_by_config_type

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


PRESET_FORMAT = BeiFileFormat(kind="rule_preset", extension=".beirules", version=1, description="rule preset")
PRESET_FOLDER = "rule_presets"  # In BEI's config folder
MAX_NAME_LENGTH = 60
MAX_DESCRIPTION_LENGTH = 500


@dataclass(frozen=True)
class Preset:
    name: str
    description: str
    content: dict             # Checked by decode_preset
    path: Path | None = None  # File of a user preset. None for built-in presets

    @property
    def is_builtin(self) -> bool:
        return self.path is None


def _check_entries(tables: list[ConfigReader], registry: dict, what: str):
    for table in tables:
        entry_type = table.get_str("type")
        if entry_type not in registry:
            raise BeiFileError(f"{table.where}: unknown {what} \"{entry_type}\". This preset may have been made with "
                               "a newer version of BrickEdit-Interface.")


def decode_preset(content: dict, version: int, path: Path | None = None) -> Preset:
    """Checks a preset's content (types, structure) without building anything. Raises BeiFileError."""
    reader = ConfigReader(content, "Preset")
    name = reader.get_str("name").strip()
    if not name:
        raise BeiFileError("The preset has no name.")
    reader.get_bool("invert")
    conditions = reader.get_tables("conditions")
    _check_entries(conditions, filters_by_config_type, "condition")
    for condition in conditions:
        condition.get_enum("mode", FilterMode, FilterMode.MUST)
    actions = reader.get_tables("actions")
    if not actions:
        raise BeiFileError("The preset has no action.")
    _check_entries(actions, actions_by_config_type, "action")
    return Preset(name[:MAX_NAME_LENGTH], reader.get_str("description")[:MAX_DESCRIPTION_LENGTH], content, path)


# ----- Building widgets from a preset, and the other way around


def preset_invert(preset: Preset) -> bool:
    return ConfigReader(preset.content, "Preset").get_bool("invert")


def build_filters(mw: 'BrickEditInterface', preset: Preset) -> list[BaseFilter]:
    """New filters set up like the preset's conditions. Raises BeiFileError (no filter is left behind)."""
    filters: list[BaseFilter] = []
    try:
        for condition in ConfigReader(preset.content, "Preset").get_tables("conditions"):
            filter_cls = filters_by_config_type[condition.get_str("type")]
            new_filter = filter_cls.new(mw, condition.get_enum("mode", FilterMode, FilterMode.MUST))
            filters.append(new_filter)
            new_filter.apply_config(condition)
    except BaseException:
        for f in filters:
            f.deleteLater()
        raise
    return filters


def preset_actions(preset: Preset) -> list[tuple[type[BaseAction], ConfigReader]]:
    """(action class, settings) of each of the preset's actions"""
    return [(actions_by_config_type[action.get_str("type")], action)
            for action in ConfigReader(preset.content, "Preset").get_tables("actions")]


def check_preset_settings(mw: 'BrickEditInterface', preset: Preset):
    """Builds the preset's conditions and actions and throws them away: raises BeiFileError if a setting is invalid.
    decode_preset only checks the structure, this is for files coming from elsewhere (import)."""
    for f in build_filters(mw, preset):
        f.deleteLater()
    for action_cls, config in preset_actions(preset):
        action = action_cls(mw)
        try:
            action.apply_config(config)
        finally:
            action.deleteLater()


def make_preset_content(name: str, description: str, invert: bool, filters: list[BaseFilter],
                        actions: list[BaseAction]) -> dict:
    """Content of a .beirules file holding these conditions and actions. Filters which can't be saved are left out
    (see unsaved_filters)."""
    return {
        "name": name,
        "description": description,
        "invert": invert,
        "conditions": [{"type": f.CONFIG_TYPE, "mode": enum_key(f.mode)} | f.get_config()
                       for f in filters if f.CONFIG_TYPE is not None],
        "actions": [{"type": action.CONFIG_TYPE} | action.get_config() for action in actions],
    }


def unsaved_filters(filters: list[BaseFilter]) -> list[BaseFilter]:
    return [f for f in filters if f.CONFIG_TYPE is None]


def user_presets() -> FileLibrary[Preset]:
    return FileLibrary(PRESET_FORMAT, PRESET_FOLDER, decode_preset)


# ----- Built-in presets


# Highlights bricks without changing them: a slightly bigger purple glass copy around each one, all of them in a new
#  editor group so they're easy to remove
HIGHLIGHT = [
    {"type": "copy", "copies": 1, "offset": [0.0, 0.0, 0.0], "copy_groups": False},
    {"type": "edit_properties", "properties": [
        {"property": p.BRICK_COLOR, "value": "800080FF"},
        {"property": p.BRICK_MATERIAL, "value": p.BrickMaterial.FROSTED_GLASS},
        {"property": p.BRICK_SIZE, "formula": ["x+1", "y+1", "z+1"]},
        {"property": p.SPINNER_SIZE, "formula": ["x+max(1, 1 if y == 0 else x/y)", "y+1"]},
    ]},
    {"type": "group", "group_type": "editor", "move_to": "new"},
]
HIGHLIGHT_NOTE = ""  # " Highlights are glass copies, grouped together so they're easy to remove."


def _builtin(name: str, description: str, conditions: list[dict], actions: list[dict]) -> Preset:
    return decode_preset({"name": name, "description": description, "invert": False,
                          "conditions": conditions, "actions": actions}, PRESET_FORMAT.version)


# Mirror presets use Brick Rigs' own tolerances: only exact mirror images count, like in game
# STRICT_NOTE = " Exact mirrors only: raise the tolerances for hand-built vehicles."


def _mirror_status(status: str, side: str = "both", mode: str = "must") -> dict:
    return {"type": "mirror", "mode": mode, "status": status, "axis": "y", "plane": 0.0, "side": side,
            "tolerance": GAME_POSITION_TOLERANCE, "angle_tolerance": GAME_ANGLE_TOLERANCE, "turned_bricks": False}


def _mirror(counterparts: str) -> dict:
    return {"type": "mirror", "axis": "y", "plane": 0.0, "counterparts": counterparts,
            "tolerance": GAME_POSITION_TOLERANCE}


BLANK_PRESET = _builtin(
    "Blank", "Default settings.",
    [], [{"type": "delete"}],
)

BUILTIN_PRESETS: list[Preset] = [
    BLANK_PRESET,
    _builtin(
        "Remove exact duplicates",
        "Deletes duplicate bricks, keeping the first of each stack.",
        [{"type": "duplicate", "mode": "must", "match": "copies", "compare": "everything"}],
        [{"type": "delete"}],
    ),
    _builtin(
        "Remove stacked bricks",
        "Deletes duplicate bricks, keeping the first of each stack, and does not care about color "
        "or properties.",
        [{"type": "duplicate", "mode": "must", "match": "copies", "compare": "type_only"}],
        [{"type": "delete"}],
    ),
    _builtin(
        "Highlight duplicates",
        "Highlights magenta the first brick of each stack of duplicates (one highlight per stack). Ignores "
        "color." + HIGHLIGHT_NOTE,
        [{"type": "duplicate", "mode": "must", "match": "first_only", "compare": "ignore_color"}],
        HIGHLIGHT,
    ),
    _builtin(
        "Highlight mirror issues",
        "Highlights magenta every brick with a missing or imperfect counterpart (Y axis)." + HIGHLIGHT_NOTE,
        [_mirror_status("any_issue")],
        HIGHLIGHT,
    ),
    _builtin(
        "Mirror the - side onto the + side",
        "Mirrors - side bricks without a counterpart onto the + side (Y axis).",
        [_mirror_status("missing", "negative")],
        [_mirror("skip")],
    ),
    _builtin(
        "Mirror the + side onto the - side",
        "Mirrors + side bricks without a counterpart onto the - side (Y axis).",
        [_mirror_status("missing", "positive")],
        [_mirror("skip")],
    ),
    _builtin(
        "Fix badly mirrored bricks (- side wins)",
        "Re-mirrors - side bricks whose + side counterpart is imperfect (Y axis).",
        [_mirror_status("any_issue", "negative"), _mirror_status("missing", mode="must_not")],
        [_mirror("replace")],
    ),
    _builtin(
        "Fix badly mirrored bricks (+ side wins)",
        "Re-mirrors + side bricks whose - side counterpart is imperfect (Y axis).",
        [_mirror_status("any_issue", "positive"), _mirror_status("missing", mode="must_not")],
        [_mirror("replace")],
    ),
    _builtin(
        "Remove bricks without counterpart",
        "Deletes + side bricks without a counterpart on the - side (Y axis).",
        [_mirror_status("missing", "positive")],
        [{"type": "delete"}],
    ),
]
