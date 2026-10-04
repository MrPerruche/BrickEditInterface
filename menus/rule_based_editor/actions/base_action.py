from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import Signal

from dataclasses import dataclass

from ui.widgets import Widget, Label
from ui.models import TooltipContents

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface
    from ui.components.vehicle.vehicle_data import VehicleData
    from systems.bei_files import ConfigReader


MAX_BRICKS = 50_000


def plural(count: int, word: str = "brick") -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


class ActionError(Exception):
    """The action can't be applied as configured. The message is shown to the user as is; nothing is saved."""


@dataclass
class ActionContext:
    mw: 'BrickEditInterface'
    brvfile: brickedit.BRVFile    # Copy of the loaded vehicle, edited in place by every action, then saved
    selected_ids: set[str]        # ref.id of the bricks this action applies to (see ActionResult.next_selection)
    vehicle_data: 'VehicleData'   # Data of brvfile before this action. Shares ref ids with it

    def selected_bricks(self) -> list[brickedit.Brick]:
        """Bricks of brvfile this action applies to, in file order"""
        return [brick for brick in self.brvfile.bricks if brick.ref.id in self.selected_ids]


@dataclass
class ActionResult:
    summary: str           # Eg. "Deleted 12 bricks." Shown in the menu and written in the backup's description
    changed: bool = True
    next_selection: set[str] | None = None  # ref.id of the bricks the next actions apply to. None: the same ones


class BaseAction(Widget):
    """Something done to the selected bricks. Its widget holds the action's settings. Actions are applied one after
    the other: each one applies to the bricks the previous one passed on (see ActionResult.next_selection)."""

    options_changed = Signal()

    LABEL_STRETCH = 4
    WIDGET_STRETCH = 11

    def __init__(self, mw: 'BrickEditInterface'):
        super().__init__()
        self.mw = mw
        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)

    def add_setting_row(self, text: str, widget: QWidget, tooltip: TooltipContents | None = None) -> Widget:
        """Adds a "label | widget" row (proportions of the image importer). Returns the row, which can be hidden."""
        row = Widget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = Label(text)
        if tooltip is not None:
            label.set_tooltip(tooltip)
        layout.addWidget(label, stretch=self.LABEL_STRETCH)
        layout.addWidget(widget, stretch=self.WIDGET_STRETCH)
        self.master_layout.addWidget(row)
        return row

    def emit_options_changed(self, *_):
        self.options_changed.emit()


    # --- To implement

    @classmethod
    def get_name(cls) -> str:
        raise NotImplementedError(f"Subclass {cls.__name__} must implement get_name()")

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return None

    def describe(self, count: int) -> str:
        """Short imperative description, used on the apply button. Eg. "Delete 12 bricks"."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement describe()")

    def removes_bricks(self) -> bool:
        """If True, the user is asked to confirm before applying."""
        return False

    def next_selection_hint(self) -> str | None:
        """Shown under the action when other actions follow it, if the next actions don't apply to the same bricks.
        Eg. "The next actions apply to the copies." Must match ActionResult.next_selection."""
        return None

    def on_selection_changed(self, bricks: list[brickedit.Brick]) -> None:
        """Called with the bricks matching the conditions (from the loaded vehicle, do not edit) whenever they
        change."""

    def apply(self, ctx: ActionContext) -> ActionResult:
        """Edits ctx.brvfile. Raises ActionError if the action can't be applied."""
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement apply()")


    # --- Saving (rule presets, see systems.bei_files)

    CONFIG_TYPE: str = ""
    """Stable id of the action in saved files. Never change it once released."""

    def get_config(self) -> dict:
        """The action's settings, TOML compatible."""
        return {}

    def apply_config(self, config: 'ConfigReader') -> None:
        """Restores settings saved by get_config. Raises BeiFileError if a value is invalid."""

    def config_warning(self) -> str | None:
        """Why the settings can't be saved entirely, if they can't. Shown before saving a preset."""
        return None
