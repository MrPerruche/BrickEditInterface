from ui.models import TooltipContents

from dataclasses import dataclass

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface



class BaseGM:

    @classmethod
    def get_name(cls):
        return NotImplementedError(f"Subclass {cls.__name__} must implement get_name()")

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return None

    def split(self, mw: 'BrickEditInterface', bricks: list[brickedit.Brick]) -> dict[str, list[brickedit.Brick]]:
        raise NotImplementedError(f"Subclass {self.__class__.__name__} must implement split()")
