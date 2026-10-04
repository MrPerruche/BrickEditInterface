from menus.rule_based_editor.actions.base_action import BaseAction, ActionContext, ActionResult, ActionError, plural
from menus.rule_based_editor.actions.delete_action import DeleteAction
from menus.rule_based_editor.actions.edit_properties_action import EditPropertiesAction
from menus.rule_based_editor.actions.paint_action import PaintAction
from menus.rule_based_editor.actions.group_action import GroupAction
from menus.rule_based_editor.actions.transform_action import TransformAction
from menus.rule_based_editor.actions.change_type_action import ChangeTypeAction
from menus.rule_based_editor.actions.mirror_action import MirrorAction
from menus.rule_based_editor.actions.copy_action import CopyAction
from menus.rule_based_editor.actions.select_action import SelectAction

# Order of the action type combo box. The first one is the default
action_classes: list[type[BaseAction]] = [
    DeleteAction,
    EditPropertiesAction,
    PaintAction,
    GroupAction,
    TransformAction,
    ChangeTypeAction,
    MirrorAction,
    CopyAction,
    SelectAction,
]

actions_by_config_type: dict[str, type[BaseAction]] = {cls.CONFIG_TYPE: cls for cls in action_classes}
assert len(actions_by_config_type) == len(action_classes) and "" not in actions_by_config_type, "Action CONFIG_TYPEs must be unique"
