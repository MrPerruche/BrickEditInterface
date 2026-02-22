from .square_widget import SquareWidget
from .expression_widget import ExpressionWidget, ExpressionType, ExpressionSymbol
from .property_widgets import PropertyWidget, DynamicPropertyWidget, UnknownPropertyWidget, UnknownDynamicPropertyWidget
from .tabmenu import TabMenu

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QMessageBox, QSizePolicy
from PySide6.QtGui import QIcon
from brickedit import *

from utils import all_equal, clear_layout

from copy import deepcopy
from enum import Enum


class UnknownBrickMeta(bt.BrickMeta):
    def base_properties(self):
        return {}  # Not even base default properties, we do now know what we're dealing with.



class BrickWidget(SquareWidget):

    def __init__(self, side_info: str | int, idx: list[int], bricks: list[Brick], parent=None):
        super().__init__(parent)
        self.side_info = side_info if isinstance(side_info, str) else str(side_info)
        self.idx = idx
        self.bricks = deepcopy(bricks)
        self.og_bricks = deepcopy(bricks)

        self.master_layout = QVBoxLayout()  # no parent
        self.setLayout(self.master_layout)  # explicitly assign
        self.build_widget()



    def build_widget(self):

        # ==============================
        # Internal name and reset button
        # ==============================

        clear_layout(self.master_layout)
        self.top_layout = QHBoxLayout()
        
        # Assert all internal names are equal
        self.names_equal = all_equal(self.bricks, lambda x: x.meta().name())
        assert all_equal(self.bricks, lambda x: type(x.meta())), "All brick type classes must be equal"
        
        # Internal name
        self.brick_type_le = QLineEdit()
        if self.names_equal:
            self.brick_type_le.setText(self.bricks[0].meta().name())
            self.brick_type_le.editingFinished.connect(self.recieve_new_internal_name)
            self.brick_type_le_last_in = self.bricks[0].meta().name()
        else:
            self.brick_type_le.setText(type(self.bricks[0].meta()).__name__)
            self.brick_type_le.setEnabled(False)
            self.brick_type_le_last_in = type(self.bricks[0].meta()).__name__
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

        # Position
        self.position_layout = QHBoxLayout()
        self.pos_x_spin = (
            ExpressionWidget(self.bricks[0].pos.x, ExpressionType.FLOAT)
            if all_equal(self.bricks, lambda x: x.pos.x) else
            ExpressionWidget("x", ExpressionType.MATH_EXPR)
        )
        self.pos_y_spin = (
            ExpressionWidget(self.bricks[0].pos.y, ExpressionType.FLOAT)
            if all_equal(self.bricks, lambda x: x.pos.y) else
            ExpressionWidget("x", ExpressionType.MATH_EXPR)
        )
        self.pos_z_spin = (
            ExpressionWidget(self.bricks[0].pos.z, ExpressionType.FLOAT)
            if all_equal(self.bricks, lambda x: x.pos.z) else
            ExpressionWidget("x", ExpressionType.MATH_EXPR)
        )
        self.position_layout.addWidget(self.pos_x_spin)
        self.position_layout.addWidget(self.pos_y_spin)
        self.position_layout.addWidget(self.pos_z_spin)
        self.master_layout.addLayout(self.position_layout)

        # Rotation
        self.rotation_layout = QHBoxLayout()
        self.rot_x_spin = (
            ExpressionWidget(self.bricks[0].rot.x, ExpressionType.FLOAT)
            if all_equal(self.bricks, lambda x: x.rot.x) else
            ExpressionWidget("x", ExpressionType.MATH_EXPR)
        )
        self.rot_y_spin = (
            ExpressionWidget(self.bricks[0].rot.y, ExpressionType.FLOAT)
            if all_equal(self.bricks, lambda x: x.rot.y) else
            ExpressionWidget("x", ExpressionType.MATH_EXPR)
        )
        self.rot_z_spin = (
            ExpressionWidget(self.bricks[0].rot.z, ExpressionType.FLOAT)
            if all_equal(self.bricks, lambda x: x.rot.z) else
            ExpressionWidget("x", ExpressionType.MATH_EXPR)
        )
        self.rotation_layout.addWidget(self.rot_x_spin)
        self.rotation_layout.addWidget(self.rot_y_spin)
        self.rotation_layout.addWidget(self.rot_z_spin)
        self.master_layout.addLayout(self.rotation_layout)

        # Properties
        self.properties_layout = QVBoxLayout()
        self.properties_layout.setContentsMargins(0, 0, 0, 0)
        self.properties_layout.setSpacing(0)
        self.master_layout.addLayout(self.properties_layout)
        self.property_widgets: list[PropertyWidget | DynamicPropertyWidget] = []

        for prop in self.bricks[0].get_all_properties().keys():
            all_prop_equal = all_equal(self.bricks, lambda x: x.get_property(prop))
            if all_prop_equal:
                pw = PropertyWidget.from_property(prop, self.bricks[0].get_property(prop))
            else:
                pw = DynamicPropertyWidget.from_property(prop)
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


    def get_modified_bricks(self):

        bricks = []

        for i in range(len(self.bricks)):
            idx = self.idx[i]
            brick = self.bricks[i]
            # Update pos and rot
            posx = self.pos_x_spin.value([ExpressionSymbol("x", lambda: brick.pos.x, None)])
            posy = self.pos_y_spin.value([ExpressionSymbol("x", lambda: brick.pos.y, None)])
            posz = self.pos_z_spin.value([ExpressionSymbol("x", lambda: brick.pos.z, None)])
            rotx = self.rot_x_spin.value([ExpressionSymbol("x", lambda: brick.rot.x, None)])
            roty = self.rot_y_spin.value([ExpressionSymbol("x", lambda: brick.rot.y, None)])
            rotz = self.rot_z_spin.value([ExpressionSymbol("x", lambda: brick.rot.z, None)])
            brick.pos = Vec3(posx, posy, posz)
            brick.rot = Vec3(rotx, roty, rotz)

            # Update properties
            for pw in self.property_widgets:
                if isinstance(pw, (UnknownPropertyWidget, UnknownDynamicPropertyWidget)):
                    continue
                if isinstance(pw, PropertyWidget):
                    brick.set_property(pw.name, pw.get_value())
                else:  # DynamicPropertyWidget
                    brick.set_property(pw.name, pw.get_value(brick))

            bricks.append((idx, brick))

        return bricks




class BrickListWidget(SquareWidget):

    def __init__(self, bricks: list[Brick], parent=None):
        super().__init__(parent)

        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.tabs = TabMenu(vertical=True)
        self.tabs.setContentsMargins(0, 0, 0, 0)
        self.tabs.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.master_layout.addWidget(self.tabs)
        self.tabs.add_menu(0, "Individual", QVBoxLayout())
        self.tabs[0].setContentsMargins(0, 0, 0, 0)
        self.tabs.add_menu(1, "Per type", QVBoxLayout())
        self.tabs[1].setContentsMargins(0, 0, 0, 0)
        self.tabs.add_menu(2, "Per class", QVBoxLayout())
        self.tabs[2].setContentsMargins(0, 0, 0, 0)

        self.tabs[0].addWidget(QLabel("Menu not initialized."))
        self.tabs[1].addWidget(QLabel("Menu not initialized."))
        self.tabs[2].addWidget(QLabel("Menu not initialized."))

        self.brick_widgets_individual = []
        self.brick_widgets_per_type = []
        self.brick_widgets_per_class = []
        self.update_bricks_widgets(bricks)

        # self.master_layout.addStretch()





    def update_bricks_widgets(self, bricks: list[tuple[int, Brick]]):
        bricks = deepcopy(bricks)
        self.update_individual_widgets(bricks)
        self.update_per_type_widgets(bricks)
        self.update_per_class_widgets(bricks)



    def update_individual_widgets(self, bricks: list[tuple[int, Brick]]):
        self.brick_widgets_individual = []
        clear_layout(self.tabs[0])

        # Quick check if none
        if not bricks:
            no_l = QLabel("No bricks selected")
            no_l.setEnabled(False)
            self.tabs[0].addWidget(no_l)
            return

        for i, brick in bricks:
            bw = BrickWidget(str(i), [i], [brick])
            self.brick_widgets_individual.append(bw)
            self.tabs[0].addWidget(bw)



    def update_per_type_widgets(self, bricks: list[tuple[int, Brick]]):
        self.brick_widgets_per_type = []
        clear_layout(self.tabs[1])
        type_to_pairs: dict[str, Any] = {}

        # Quick check if none
        if not bricks:
            no_l = QLabel("No bricks selected")
            no_l.setEnabled(False)
            self.tabs[1].addWidget(no_l)
            return

        # Sort by type
        for i, brick in bricks:
            type = brick.meta().name()
            if type not in type_to_pairs:
                type_to_pairs[type] = []
            type_to_pairs[type].append((i, brick))

        # Create a widget for reach type
        for type, pairs in type_to_pairs.items():
            bw = BrickWidget(
                str(len(pairs)),
                [pair[0] for pair in pairs],
                [pair[1] for pair in pairs]
            )
            self.brick_widgets_per_type.append(bw)
            self.tabs[1].addWidget(bw)



    def update_per_class_widgets(self, bricks: list[tuple[int, Brick]]):
        self.brick_widgets_per_class = []
        clear_layout(self.tabs[2])
        class_to_pairs: dict[type, Any] = {}

        # Quick check if none
        if not bricks:
            no_l = QLabel("No bricks selected")
            no_l.setEnabled(False)
            self.tabs[2].addWidget(no_l)
            return

        # Sort by type
        for i, brick in bricks:
            class_ = type(brick.meta())
            if class_ not in class_to_pairs:
                class_to_pairs[class_] = []
            class_to_pairs[class_].append((i, brick))

        # Create a widget for reach type
        for class_, pairs in class_to_pairs.items():
            bw = BrickWidget(
                str(len(pairs)),
                [pair[0] for pair in pairs],
                [pair[1] for pair in pairs]
            )
            self.brick_widgets_per_class.append(bw)
            self.tabs[2].addWidget(bw)



    def get_modified_bricks(self) -> list[tuple[int, Brick]]:
        target = [self.brick_widgets_individual, self.brick_widgets_per_type, self.brick_widgets_per_class]\
            [self.tabs.current_index()]

        result = []
        for bw in target:
            result.extend(bw.get_modified_bricks())
        return result