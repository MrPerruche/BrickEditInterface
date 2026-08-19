from ui.components.brick.grouping_methods.base_gm import BaseGM
from ui.components.vehicle.vehicle_data import VehicleData, FORBIDDEN_PREFIX
from ui.models import TooltipContents

import brickedit

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


GROUP_NAMING_TOOLTIP = TooltipContents("You can name any group (weld or editor) by creating a text brick (any type) and setting the text to\n<code>bei#&lt;my group name&gt;</code>")

class EditorGroupGM(BaseGM):
    @classmethod
    def get_name(cls):
        return "Split selection by editor groups"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return GROUP_NAMING_TOOLTIP


    def split(self, mw: 'BrickEditInterface', bricks: list[brickedit.Brick]) -> dict[str, list[brickedit.Brick]]:

        brvfile_data = VehicleData(brickedit.BRVFile(brickedit.FILE_MAIN_VERSION, bricks=bricks))
        unnamed_editor_group_count = len(brvfile_data.unnamed_editor_groups)

        result = {gid: bs for gid, bs in brvfile_data.editor_groups.items() if bs}
        result |= {f"{FORBIDDEN_PREFIX} Unnamed group {i+1:,} / {unnamed_editor_group_count:,}": bs for i, bs in enumerate(brvfile_data.unnamed_editor_groups)}
        if brvfile_data.not_in_editor_group:
            result[f"{FORBIDDEN_PREFIX} Not in any editor groups"] = brvfile_data.not_in_editor_group

        return result


class WeldGroupGM(BaseGM):
    @classmethod
    def get_name(cls):
        return "Split selection by weld groups"

    @classmethod
    def get_tooltip(cls) -> TooltipContents | None:
        return GROUP_NAMING_TOOLTIP


    def split(self, mw: 'BrickEditInterface', bricks: list[brickedit.Brick]) -> dict[str, list[brickedit.Brick]]:

        brvfile_data = VehicleData(brickedit.BRVFile(brickedit.FILE_MAIN_VERSION, bricks=bricks))
        unnamed_weld_group_count = len(brvfile_data.unnamed_weld_groups)

        result = {gid: bs for gid, bs in brvfile_data.weld_groups.items() if bs}
        result |= {f"{FORBIDDEN_PREFIX} Unnamed group {i+1:,} / {unnamed_weld_group_count:,}": bs for i, bs in enumerate(brvfile_data.unnamed_weld_groups)}
        if brvfile_data.not_in_weld_group:
            result[f"{FORBIDDEN_PREFIX} Not in any weld groups"] = brvfile_data.not_in_weld_group

        return result
