from PySide6.QtGui import QIcon

from ui.components import Tutorial
from menus import base


class RuleBasedEditor(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)


    def get_menu_name(self) -> str:
        """Return the display name of this menu."""
        # NOTE: TUTORIAL USE A DIFFERENT NAME. IF MENU NAME MUST BE CHANGED, UPDATE TUTORIAL MANUALLY!
        return "Rule Based Editor"

    def _make_menu_info(self) -> base.MenuInfo:
        """Return the icon for this menu."""
        return base.MenuInfo(QIcon(":/assets/icons/RuleBasedEditor.png"), True,
            tutorial=Tutorial("Rule Based Editor", self.mw)
                .add_text("WIP")
        )
