from ui.components.brick.grouping_methods.base_gm import BaseGM
from ui.models import TooltipContents

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class NoGroupingGM(BaseGM):
    @classmethod
    def get_name(cls):
        return "Split selection by individual bricks"

    def split(self, mw: 'BrickEditInterface', bricks: list[brickedit.Brick]) -> dict[str, list[brickedit.Brick]]:
        brick_count = len(bricks)
        return {f"{i+1:,} / {brick_count:,}": [b] for i, b in enumerate(bricks)}


class MergeAllGM(BaseGM):
    @classmethod
    def get_name(cls):
        return "Do not split selection"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("Edit all selected bricks simultaneously")

    def split(self, mw: 'BrickEditInterface', bricks: list[brickedit.Brick]) -> dict[str, list[brickedit.Brick]]:
        return {"Cannot split selection.": bricks}
