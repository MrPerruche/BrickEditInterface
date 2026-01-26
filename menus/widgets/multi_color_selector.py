from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QMessageBox
)
from PySide6.QtGui import QIcon, QColor
from PySide6.QtCore import Qt

from .square_widget import SquareWidget
from .color_selector import ColorSelectorWidget
from .float_line_edit import SafeMathLineEdit

from utils import clear_layout



class MultiColorSelectorWidget(SquareWidget):
    """A widget for selecting multiple colors with a scrollable layout."""

    MAX_COLORS = 20

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setSpacing(6)

        # --- Top Bar ---
        self.top_layout = QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(6)

        # Label
        self.label = QLabel("Selected colors:")
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignVCenter)
        self.top_layout.addWidget(self.label)
        self.top_layout.addStretch()

        # Add button
        self.add_button = QPushButton()
        self.add_button.setIcon(QIcon.fromTheme("list-add"))
        self.add_button.setFixedSize(32, 32)
        self.add_button.clicked.connect(self.add_new_color)  # optional
        self.top_layout.addWidget(self.add_button)

        self.root_layout.addLayout(self.top_layout)

        # --- Scroll Area for color selectors ---
        self.scroll_inner = QWidget()
        self.scroll_layout = QHBoxLayout(self.scroll_inner)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(6)

        # Default color widgets
        self.color_widgets: list[ColorSelectorWidget] = [
            ColorSelectorWidget(0, True, True, True, color=QColor(16, 16, 204)),
            ColorSelectorWidget(100, True, True, True, color=QColor(204, 16, 32))
        ]

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_inner)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.root_layout.addWidget(self.scroll_area)



        self.rebuild_elements_layout()


    def rebuild_elements_layout(self):
        clear_layout(self.scroll_layout)

        for i, widget in enumerate(self.color_widgets):
            is_first = i == 0
            is_last = i == len(self.color_widgets) - 1

            widget.set_removable(not is_first and not is_last)
            widget.set_position_modifiable(not is_first and not is_last)
            widget.set_duplicatable(not is_last)

            # --- Disconnect previous callbacks if they exist ---
            if hasattr(widget, "_on_duplicate"):
                widget.duplicate_button.clicked.disconnect(widget._on_duplicate)
            if hasattr(widget, "_on_remove"):
                widget.remove_button.clicked.disconnect(widget._on_remove)

            # --- Create and store new callbacks ---
            widget._on_duplicate = (
                lambda i=i, w=widget: self.add_new_color(
                    color=w.color,
                    pos=w.position_le.value(),
                    idx=i + 1
                )
            )
            widget._on_remove = lambda _=False, i=i: self.remove_color(idx=i)

            widget.duplicate_button.clicked.connect(widget._on_duplicate)
            widget.remove_button.clicked.connect(widget._on_remove)

            self.scroll_layout.addWidget(widget)



    def add_new_color(self, *args, color = None, pos = None, idx = None):
        if len(self.color_widgets) >= self.MAX_COLORS:
            QMessageBox.warning(self, "Too many colors", f"You can only select up to {self.MAX_COLORS} colors.")
            return
        self.add_color(color=color, pos=pos, idx=idx)


    def add_color(self, color: QColor | None = None, pos=None, idx=None):
        color = color or QColor(128, 128, 128)

        last_pos = self.color_widgets[-1].position_le.value()
        before_last_pos = self.color_widgets[-2].position_le.value()
        position = pos if pos is not None else (last_pos + before_last_pos) / 2

        widget = ColorSelectorWidget(position, True, True, True, color=color)

        insert_idx = idx if idx is not None else len(self.color_widgets) - 1
        self.color_widgets.insert(insert_idx, widget)

        self.rebuild_elements_layout()
        return widget


    def remove_color(self, *args, idx):
        widget = self.color_widgets.pop(idx)
        widget.setParent(None)
        widget.deleteLater()

        self.rebuild_elements_layout()


    def get_colors(self) -> list[QColor]:
        """Return the list of selected colors."""
        return [w.color for w in self.color_widgets]

    def get_colors_pos(self) -> list[tuple[QColor, float]]:
        """Return the list of selected colors and their positions."""
        return [(w.color, w.position_le.value()) for w in self.color_widgets]
