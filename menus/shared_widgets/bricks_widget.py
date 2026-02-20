from .square_widget import SquareWidget
from .expression_widget import ExpressionWidget, ExpressionType
from .property_widgets import PropertyWidget, UnknownPropertyWidget
from .tabmenu import TabMenu

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox, QSizePolicy
from PySide6.QtGui import QIcon
from brickedit import *

from utils import clear_layout

from copy import deepcopy
from enum import Enum


class UnknownBrickMeta(bt.BrickMeta):
    def base_properties(self):
        return {}  # Not even base default properties, we do now know what we're dealing with.


class BrickWidgetMode(Enum):
    INDIVIDUAL_BRICK = 0
    TYPE_REPRESENTATION = 1


class BrickWidget(SquareWidget):

    def __init__(self, side_info: str | int, brick: Brick, brick_mode: BrickWidgetMode, parent=None):
        super().__init__(parent)
        self.side_info = side_info if isinstance(side_info, str) else str(side_info)
        self.brick = deepcopy(brick)
        self.og_brick = deepcopy(brick)
        self.brick_mode = brick_mode

        self.master_layout = QVBoxLayout()  # no parent
        self.setLayout(self.master_layout)  # explicitly assign
        self.build_widget()


    def clear_layout(self, layout=None):
        if layout is None:
            layout = self.master_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                self.clear_layout(item.layout())



    def build_widget(self):

        # ==============================
        # Internal name and reset button
        # ==============================

        self.clear_layout()
        self.top_layout = QHBoxLayout()
        
        # Internal name
        self.brick_type_le = QLineEdit()
        self.brick_type_le.setText(self.brick.meta().name())
        self.brick_type_le.editingFinished.connect(self.recieve_new_internal_name)
        self.brick_type_le_last_in = self.brick.meta().name()
        self.top_layout.addWidget(self.brick_type_le)

        # Index
        self.brick_idx_label = QLabel(f"[{self.side_info}]")
        self.top_layout.addWidget(self.brick_idx_label)

        # Reset
        self.reset_brick_button_icon = QIcon.fromTheme("view-refresh")
        self.reset_brick_button = QPushButton()
        self.reset_brick_button.setIcon(self.reset_brick_button_icon)
        self.reset_brick_button.clicked.connect(self.build_widget)
        self.top_layout.addWidget(self.reset_brick_button)

        self.master_layout.addLayout(self.top_layout)

        # ====================
        # Local space settings
        # ====================

        if self.brick_mode == BrickWidgetMode.INDIVIDUAL_BRICK:
            expr_types = ExpressionType.FLOAT
        else:
            expr_types = ExpressionType.MATH_EXPR

        # Position
        self.position_layout = QHBoxLayout()
        self.pos_x_spin = ExpressionWidget(self.brick.pos.x, expr_types)
        self.pos_y_spin = ExpressionWidget(self.brick.pos.y, expr_types)
        self.pos_z_spin = ExpressionWidget(self.brick.pos.z, expr_types)
        self.position_layout.addWidget(self.pos_x_spin)
        self.position_layout.addWidget(self.pos_y_spin)
        self.position_layout.addWidget(self.pos_z_spin)
        self.master_layout.addLayout(self.position_layout)

        # Rotation
        self.rotation_layout = QHBoxLayout()
        self.rot_x_spin = ExpressionWidget(self.brick.rot.x, expr_types)
        self.rot_y_spin = ExpressionWidget(self.brick.rot.y, expr_types)
        self.rot_z_spin = ExpressionWidget(self.brick.rot.z, expr_types)
        self.rotation_layout.addWidget(self.rot_x_spin)
        self.rotation_layout.addWidget(self.rot_y_spin)
        self.rotation_layout.addWidget(self.rot_z_spin)
        self.master_layout.addLayout(self.rotation_layout)

        # Properties
        self.properties_layout = QVBoxLayout()
        self.properties_layout.setContentsMargins(0, 0, 0, 0)
        self.properties_layout.setSpacing(0)
        self.master_layout.addLayout(self.properties_layout)
        self.property_widgets: list[PropertyWidget] = []
        for prop, val in self.brick.get_all_properties().items():
            pw = PropertyWidget.from_property(prop, val)
            self.property_widgets.append(pw)
            self.properties_layout.addWidget(pw)



    def recieve_new_internal_name(self):
        return self.new_internal_name(self.brick_type_le.text())



    def new_internal_name(self, new_name):

        # Get the meta
        brick_meta = bt.bt_registry.get(new_name)

        # If none, warn. Ask for confirmation
        if brick_meta is None:
            # Warning
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Unknown internal name")
            dlg.setText(f"This internal name is not known by BrickEdit: {new_name}")
            dlg.setIcon(QMessageBox.Warning)
            dlg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
            result = dlg.exec()
            # result = QMessageBox.warning(self, "Unknown internal name", f"This internal name is not known by BrickEdit: {new_name}\nPress cancel to undo or OK to confirm")
            # Undo changes
            if result == QMessageBox.Cancel:
                self.brick_type_le.setText(self.brick_type_le_last_in)
                return
            # Create a new brick type
            else:
                brick_meta = UnknownBrickMeta(new_name)

        # Now we have a valid meta. We can recreate the brick
        self.brick = Brick(self.brick.ref, brick_meta, self.brick.pos, self.brick.rot, self.brick.ppatch)
        self.brick_type_le_last_in = new_name
        self.brick_type_le.setText(new_name)


    def get_modified_brick(self):
        # Update pos and rot
        self.brick.pos = Vec3(self.pos_x_spin.value(), self.pos_y_spin.value(), self.pos_z_spin.value())
        self.brick.rot = Vec3(self.rot_x_spin.value(), self.rot_y_spin.value(), self.rot_z_spin.value())

        # Update properties
        for pw in self.property_widgets:
            if isinstance(pw, UnknownPropertyWidget):
                continue
            self.brick.set_property(pw.name, pw.get_value())

        return self.brick




class LegacyBrickListWidget(SquareWidget):

    def __init__(self, bricks: list[Brick], parent=None):
        super().__init__(parent)

        self.master_layout = QVBoxLayout(self)
        # self.master_layout.setContentsMargins(0, 0, 0, 0)
        # self.master_layout.setSpacing(0)
        self.setLayout(self.master_layout)

        self.no_bricks_label = QLabel("No bricks selected")

        self.brick_widgets = []
        self.update_brick_widgets(bricks)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def update_brick_widgets(self, bricks: list[tuple[int, Brick]]):
        # Delete old widgets
        self.clear_layout(self.master_layout)

        # Redo widgets
        self.brick_widgets = [BrickWidget(i, brick) for i, brick in bricks]
        for brick_widget in self.brick_widgets:
            self.master_layout.addWidget(brick_widget)

        # No bricks? No label
        if not bricks:
            self.master_layout.addWidget(self.no_bricks_label)


class BrickListWidget(SquareWidget):

    def __init__(self, bricks: list[Brick], parent=None):
        super().__init__(parent)

        self.master_layout = QVBoxLayout(self)
        self.setLayout(self.master_layout)

        self.tabs = TabMenu()
        self.tabs.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.master_layout.addWidget(self.tabs)
        self.tabs.add_menu(0, "Individual", QVBoxLayout())
        self.tabs.add_menu(1, "Per type", QVBoxLayout())

        self.tabs[0].addWidget(QLabel("Test 1"))
        self.tabs[1].addWidget(QLabel("Test 2"))

        self.update_bricks_widgets(bricks)

        # self.master_layout.addStretch()

    def update_bricks_widgets(self, bricks: list[tuple[int, Brick]]):
        
