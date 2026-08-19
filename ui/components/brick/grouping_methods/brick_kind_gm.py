from ui.components.brick.grouping_methods.base_gm import BaseGM
from ui.models import TooltipContents

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class TypeGM(BaseGM):
    @classmethod
    def get_name(cls):
        return "Split selection by type"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("\"Brick types\" refer to the specific brick types (eg. Scalable Cubes, Scalable Wedges etc.) while \"brick classes\" refer to similar brick types (eg. Scalables, Lights etc.)")

    def split(self, mw: 'BrickEditInterface', bricks: list[brickedit.Brick]) -> dict[str, list[brickedit.Brick]]:
        result = {}
        for b in bricks:
            result.setdefault(b.meta().name(), []).append(b)
        return result


class ClassGM(BaseGM):
    @classmethod
    def get_name(cls):
        return "Split selection by class"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return TooltipContents("\"Brick types\" refer to the specific brick types (eg. Scalable Cubes, Scalable Wedges etc.) while \"brick classes\" refer to similar brick types (eg. Scalables, Lights etc.)")

    def split(self, mw: 'BrickEditInterface', bricks: list[brickedit.Brick]) -> dict[str, list[brickedit.Brick]]:
        result = {}
        for b in bricks:
            result.setdefault(b.meta().__class__.__name__, []).append(b)
        return result
