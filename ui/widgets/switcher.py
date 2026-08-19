from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

from ui.widgets import Widget, ToolButton, Label
from ui.models import TooltipContents

from utils import wipe_layout

from dataclasses import dataclass


@dataclass
class SwitcherEntry:
    text: str
    tooltip: TooltipContents | None = None
    layout: QLayout | None = None
    auto_add_layout: bool = True
    _widget: Widget | None = None

    def __init__(self, text: str, tooltip: TooltipContents | None = None, layout: QLayout | None = None, auto_add_layout: bool = True):
        assert isinstance(text, str), "Invalid text type"  # TODO Remove when done refactoring
        self.text = text
        self.tooltip = tooltip
        self.layout = layout
        self.auto_add_layout = auto_add_layout

        if layout is not None:
            self._widget = Widget()
            self._widget.setContentsMargins(0, 0, 0, 0)
            self._widget.setLayout(layout)
        else:
            self._widget = None

    def get_widget(self) -> Widget | None:
        return self._widget



class Switcher(Widget):

    index_changed = Signal(int)

    left_arrow_icon = None
    right_arrow_icon = None

    def __init__(self, items: list[str | SwitcherEntry], idx: int = 0, looping: bool = False, parent=None):
        super().__init__(parent)
        self.items: list[SwitcherEntry] = [item if isinstance(item, SwitcherEntry) else SwitcherEntry(item) for item in items]
        self.idx = idx
        self.looping = looping
        self.enabled = True

        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.core_switcher_layout = QHBoxLayout()
        self.core_switcher_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.core_switcher_layout)

        # CORE SWITCHER

        if Switcher.left_arrow_icon is None:
            Switcher.left_arrow_icon = QIcon(":/assets/icons/ArrowLeftSmallIcon.png")
            Switcher.right_arrow_icon = QIcon(":/assets/icons/ArrowRightSmallIcon.png")

        self.left_arrow = ToolButton(self.left_arrow_icon, tint_icon = True, parent=self)
        self.left_arrow.clicked.connect(lambda: self.move_index(-1))
        self.right_arrow = ToolButton(self.right_arrow_icon, tint_icon = True, parent=self)
        self.right_arrow.clicked.connect(lambda: self.move_index(1))

        self.label = Label(center_text=True)

        self.core_switcher_layout.addWidget(self.left_arrow)
        self.core_switcher_layout.addWidget(self.label, stretch=1)
        self.core_switcher_layout.addWidget(self.right_arrow)

        # LAYOUTS

        self.layouts_layout = QVBoxLayout()
        self.layouts_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.layouts_layout)


        # END INIT
        self.rebuild_layouts()
        self.set_index(self.idx)


    def rebuild_layouts(self):
        wipe_layout(self.layouts_layout)

        for item in self.items:
            if item.layout is None or not item.auto_add_layout:
                continue
            widget = item.get_widget()
            widget.hide()
            self.layouts_layout.addWidget(widget)



    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.left_arrow.set_enabled(enabled)
        self.right_arrow.set_enabled(enabled)
        self.label.set_muted(not enabled)


    def get_idx(self) -> int | None:
        return self.idx if self.items else None


    def get_layout(self, idx: int) -> QLayout | None:

        if not self.items:
            return None

        if self.looping:
            idx = idx % len(self.items)
        else:
            idx = 0 if idx < 0 else idx if idx < len(self.items) else len(self.items) - 1

        return self.items[idx].layout


    def set_items(self, items: list[str | SwitcherEntry], idx: int | None = None):
        self.items = [item if isinstance(item, SwitcherEntry) else SwitcherEntry(item) for item in items]
        idx = idx if idx is not None else self.idx
        self.rebuild_layouts()
        self.set_index(idx)  # Will update the label


    def move_index(self, delta):
        self.set_index(self.idx + delta)


    def set_index(self, idx):
        if not self.items:
            self.idx = 0
            self.label.set_text("None")
            self.label.set_tooltip(None)
            self.label.set_muted(True)
            self.left_arrow.set_enabled(False)
            self.right_arrow.set_enabled(False)
            self.index_changed.emit(self.idx)
            return

        # Update index
        if self.looping:
            self.idx = idx % len(self.items)
        else:
            self.idx = max(0, min(idx, len(self.items) - 1))

        # Hide current
        current_widget = self.items[self.idx].get_widget()
        if current_widget is not None:
            current_widget.hide()

        # Update label
        item = self.items[self.idx]
        self.label.set_text(item.text)
        self.label.set_tooltip(item.tooltip)
        self.label.set_muted(not self.enabled)

        # Update buttons
        self.left_arrow.set_enabled(
            self.enabled and (self.looping or self.idx != 0)
        )
        self.right_arrow.set_enabled(
            self.enabled and (self.looping or self.idx != len(self.items) - 1)
        )

        # Show new widget
        current_widget = item.get_widget()
        if current_widget is not None:
            current_widget.show()

        self.index_changed.emit(self.idx)
