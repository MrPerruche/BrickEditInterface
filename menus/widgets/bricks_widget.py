from .square_widget import SquareWidget
from .float_line_edit import SafeMathLineEdit
from .property_widgets import PropertyWidget

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QLabel, QPushButton, QLineEdit, QMessageBox
from PySide6.QtGui import QIcon
from brickedit.src.brickedit import *
from utils import parse_float_tuple
from custom_validators import TupleFloatValidator

from copy import deepcopy


class UnknownBrickMeta(bt.BrickMeta):
    def base_properties(self):
        return {}  # Not even base default properties, we do now know what we're dealing with.



class BrickWidget(SquareWidget):

    def __init__(self, idx: int, brick: Brick, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.brick = brick
        self.og_brick = deepcopy(brick)

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

        # Index
        self.top_layout = QHBoxLayout()
        self.brick_idx_label = QLabel(f"[{self.idx}]")
        
        # Internal name
        self.brick_type_le = QLineEdit()
        self.brick_type_le.setText(self.brick.meta().name())
        self.brick_type_le.editingFinished.connect(self.recieve_new_internal_name)
        self.brick_type_le_last_in = self.brick.meta().name()
        self.top_layout.addWidget(self.brick_type_le)

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

        # Position
        self.position_layout = QHBoxLayout()
        self.pos_x_spin = SafeMathLineEdit(self.brick.pos.x)
        self.pos_y_spin = SafeMathLineEdit(self.brick.pos.y)
        self.pos_z_spin = SafeMathLineEdit(self.brick.pos.z)
        self.position_layout.addWidget(self.pos_x_spin)
        self.position_layout.addWidget(self.pos_y_spin)
        self.position_layout.addWidget(self.pos_z_spin)
        self.master_layout.addLayout(self.position_layout)

        # Rotation
        self.rotation_layout = QHBoxLayout()
        self.rot_x_spin = SafeMathLineEdit(self.brick.rot.x)
        self.rot_y_spin = SafeMathLineEdit(self.brick.rot.y)
        self.rot_z_spin = SafeMathLineEdit(self.brick.rot.z)
        self.rotation_layout.addWidget(self.rot_x_spin)
        self.rotation_layout.addWidget(self.rot_y_spin)
        self.rotation_layout.addWidget(self.rot_z_spin)
        self.master_layout.addLayout(self.rotation_layout)

        # Properties
        self.properties_layout = QVBoxLayout()
        self.properties_layout.setContentsMargins(0, 0, 0, 0)
        self.properties_layout.setSpacing(0)
        self.master_layout.addLayout(self.properties_layout)
        self.property_widgets = []
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
        self.brick_widgets = [BrickWidget(i, brick) for i, brick in enumerate(bricks)]
        for brick_widget in self.brick_widgets:
            self.master_layout.addWidget(brick_widget)

        # No bricks? No label
        if not bricks:
            self.master_layout.addWidget(self.no_bricks_label)
