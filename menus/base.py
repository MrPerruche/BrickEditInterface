from PySide6.QtWidgets import QWidget, QVBoxLayout
from .widgets import LargeLabel


class BaseMenu(QWidget):
    """Base class for all menu pages in the application."""

    def __init__(self, header=True):
        super().__init__()
        self.master_layout = QVBoxLayout(self)
        if header:
            self.header_label = LargeLabel(self.get_menu_name(), 2)
            self.master_layout.addWidget(self.header_label)
        self.setLayout(self.master_layout)

    def get_menu_name(self) -> str:
        """Return the display name of this menu."""
        raise NotImplementedError("Subclasses must implement get_menu_name()")

    def get_icon_path(self) -> str:
        """Return the path to the icon for this menu."""
        raise NotImplementedError("Subclasses must implement get_icon_path()")
