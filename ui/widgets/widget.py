from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from ui.theme import Theme
from ui.models import TooltipContents

class Widget(QWidget):
    def __init__(self, parent=None, do_not_set_attributes: bool = False):
        super().__init__(parent)
        
        if not do_not_set_attributes:
            self.setAttribute(Qt.WA_StyledBackground, True)
            
        # OLD METHOD FOR REGISTRING THEME:
        # theme_manager.theme_changed.connect(self._apply_theme)
        # self._apply_theme(theme_manager.current())

    def set_tooltip(self, tooltip: TooltipContents | None):
        if tooltip is None:
            self.setToolTip("")
        else:
            self.setToolTip(tooltip.richtext())

    def _apply_theme(self, theme: Theme) -> None:
        pass
