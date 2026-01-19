from .square_widget import SquareWidget
from .float_line_edit import SafeMathLineEdit

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QLabel

from brickedit.src.brickedit import *


class BrickWidget(SquareWidget):

    def __init__(self, brick: Brick, parent=None):
        super().__init__(parent)
        self.brick = brick
        print(brick)

        self.master_layout = QVBoxLayout(self)
        self.setLayout(self.master_layout)

        self.brick_internal_name_label = QLabel(f"Internal name: {self.brick.meta().name()}")
        self.master_layout.addWidget(self.brick_internal_name_label)

        self.position_layout = QHBoxLayout()
        self.pos_x_spin = SafeMathLineEdit(self.brick.pos.x)
        self.pos_y_spin = SafeMathLineEdit(self.brick.pos.y)
        self.pos_z_spin = SafeMathLineEdit(self.brick.pos.z)
        self.position_layout.addWidget(self.pos_x_spin)
        self.position_layout.addWidget(self.pos_y_spin)
        self.position_layout.addWidget(self.pos_z_spin)
        self.master_layout.addLayout(self.position_layout)

        self.master_layout.addWidget(self.brick_internal_name_label)


class BrickListWidget(SquareWidget):

    def __init__(self, bricks: list[Brick], parent=None):
        super().__init__(parent)

        self.master_layout = QVBoxLayout(self)
        # self.master_layout.setContentsMargins(0, 0, 0, 0)
        # self.master_layout.setSpacing(0)
        self.setLayout(self.master_layout)

        self.no_bricks_label = QLabel("No bricks selected")

        self.update_brick_widgets(bricks)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def update_brick_widgets(self, bricks: list[Brick]):
        # Delete old widgets
        self.clear_layout(self.master_layout)

        # Redo widgets
        self.brick_widgets = [BrickWidget(brick) for brick in bricks]
        for brick_widget in self.brick_widgets:
            self.master_layout.addWidget(brick_widget)

        # No bricks? No label
        if not bricks:
            self.master_layout.addWidget(self.no_bricks_label)
