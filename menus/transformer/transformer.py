from PySide6.QtWidgets import QLabel, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtGui import QIcon

from ..shared_widgets import VehicleWidget, VehicleWidgetMode, LargeLabel, ExpressionWidget, ExpressionType
from menus import base

from brickedit import *
from utils import try_serialize

from copy import deepcopy
from os import path, makedirs


class VehicleUpscalerMenu(base.BaseMenu):
    """Menu for upscaling vehicle properties."""

    def __init__(self, mw):
        super().__init__(mw)

        self.vehicle_selector = VehicleWidget(VehicleWidgetMode.SELECTION, [self.update_vehicle_is_reloaded])
        self.master_layout.addWidget(self.vehicle_selector)

        # Info label
        self.info_label = QLabel("Actions are performed in the UI order. The vehicle is first moved, then rotated, then scaled")
        self.info_label.setWordWrap(True)
        self.master_layout.addWidget(self.info_label)


        self.disabled_if_vehicle_not_loaded = []


        # Position modificiation
        self.pos_label = LargeLabel("Position", 4)
        self.master_layout.addWidget(self.pos_label)
        self.pos_layout = QHBoxLayout()
        self.master_layout.addLayout(self.pos_layout)
        self.pos_offset_label = QLabel("Offset:")
        self.pos_layout.addWidget(self.pos_offset_label, 10)
        self.disabled_if_vehicle_not_loaded.append(self.pos_offset_label)
        self.pos_x_le = ExpressionWidget(0, ExpressionType.FLOAT)
        self.pos_y_le = ExpressionWidget(0, ExpressionType.FLOAT)
        self.pos_z_le = ExpressionWidget(0, ExpressionType.FLOAT)
        self.pos_layout.addWidget(self.pos_x_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.pos_x_le)
        self.pos_layout.addWidget(self.pos_y_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.pos_y_le)
        self.pos_layout.addWidget(self.pos_z_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.pos_z_le)


        # Scale
        self.scale_label = LargeLabel("Scale", 4)
        self.master_layout.addWidget(self.scale_label)
        self.rot_connection_warning = QLabel("Warning: modifying these settings will likely mess up connections.\nThis will not affect welded bricks.")
        self.rot_connection_warning.setWordWrap(True)
        self.master_layout.addWidget(self.rot_connection_warning)
        # Scale modification
        self.scale_mult_layout = QHBoxLayout()
        self.master_layout.addLayout(self.scale_mult_layout)
        # Multiplier
        self.scale_mult_label = QLabel("Multiply by:")
        self.scale_mult_layout.addWidget(self.scale_mult_label, 10)
        self.disabled_if_vehicle_not_loaded.append(self.scale_mult_label)
        self.scale_mult_le = ExpressionWidget(1, ExpressionType.DOUBLE)
        self.scale_mult_le.editingFinished.connect(lambda: self.scale_input_updated(True))
        self.scale_mult_layout.addWidget(self.scale_mult_le, 30)
        
        self.disabled_if_vehicle_not_loaded.append(self.scale_mult_le)
        # Divisor
        self.scale_div_layout = QHBoxLayout()
        self.master_layout.addLayout(self.scale_div_layout)
        self.scale_div_label = QLabel("Divide by:")
        self.scale_div_layout.addWidget(self.scale_div_label, 10)
        self.disabled_if_vehicle_not_loaded.append(self.scale_div_label)
        self.scale_div_le = ExpressionWidget(1, ExpressionType.DOUBLE)
        self.scale_div_le.editingFinished.connect(lambda: self.scale_input_updated(False))
        self.scale_div_layout.addWidget(self.scale_div_le, 30)
        self.disabled_if_vehicle_not_loaded.append(self.scale_div_le)


        # Save button
        self.save_button = QPushButton("Save changes")
        self.save_button.clicked.connect(self.save_changes)
        self.master_layout.addWidget(self.save_button)


        self.update_vehicle_is_reloaded()

        self.master_layout.addStretch()

    def scale_input_updated(self, mult_has_priority: bool):
        if mult_has_priority:
            self.scale_div_le.blockSignals(True)
            self.scale_div_le.setText(str(1 / float(self.scale_mult_le.get_text())))
            self.scale_div_le.blockSignals(False)
        else:
            self.scale_mult_le.blockSignals(True)
            self.scale_mult_le.setText(str(1 / float(self.scale_div_le.get_text())))
            self.scale_mult_le.blockSignals(False)


    def update_vehicle_is_reloaded(self):
        if self.vehicle_selector.brv_file is None:
            for widget in self.disabled_if_vehicle_not_loaded:
                widget.setDisabled(True)
            return
        # else:
        for widget in self.disabled_if_vehicle_not_loaded:
            widget.setDisabled(False)


    def save_changes(self):
        if self.vehicle_selector.brv_file is None:
            QMessageBox.warning(self, "No vehicle selected", "No vehicle selected. Please select a vehicle before saving changes.")
            return
        vehicle_dir = path.dirname(self.vehicle_selector.brv_file)
        self.main_window.backups.full_backup_procedure(vehicle_dir, f"Modified using the {self.get_menu_name()}.")

        # Save (and make sure the path exists)
        makedirs(path.dirname(self.vehicle_selector.brv_file), exist_ok=True)
        
        
        # Modify the brv
        brv = deepcopy(self.vehicle_selector.brv)
        
        off_x = float(self.pos_x_le.get_text())
        off_y = float(self.pos_y_le.get_text())
        off_z = float(self.pos_z_le.get_text())
        scale = float(self.scale_mult_le.get_text())
        
        must_offset = (off_x != 0) or (off_y != 0) or (off_z != 0)
        must_scale = scale != 1

        if must_offset:
            for brick in brv.bricks:
                brick.pos += Vec3(off_x, off_y, off_z)

        if must_scale:
            for brick in brv.bricks:
                # Position
                brick.pos *= scale
                # Modify properties
                for prop, val in brick.get_all_properties().items():
                    # Float & vec properties
                    if prop in (
                            p.BRICK_SIZE,
                            p.SPINNER_RADIUS, p.SPINNER_SIZE,
                            p.WHEEL_DIAMETER, p.WHEEL_WIDTH, p.TIRE_WIDTH,
                            p.PATTERN_SCALE,
                            p.FONT_SIZE
                    ):
                        brick.set_property(prop, val * scale)



        serialized = try_serialize(brv)
        if serialized is None:
            return
        with open(self.vehicle_selector.brv_file, "wb") as f:
            f.write(serialized)

        QMessageBox.information(self, "BrickEdit-Interface", "Successfully saved changes.")



    def get_menu_name(self) -> str:
        return "Vehicle Transformer"

    def get_icon(self) -> QIcon:
        return QIcon(":/assets/icons/GizmoIcon.png")
