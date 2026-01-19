from PySide6.QtWidgets import QWidget


class BaseMenu(QWidget):
    """Base class for all menu pages in the application."""

    def __init__(self):
        super().__init__()

    def get_menu_name(self) -> str:
        """Return the display name of this menu."""
        raise NotImplementedError("Subclasses must implement get_menu_name()")

    def get_icon_path(self) -> str:
        """Return the path to the icon for this menu."""
        raise NotImplementedError("Subclasses must implement get_icon_path()")
