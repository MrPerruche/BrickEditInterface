from PySide6.QtWidgets import QLabel, QHBoxLayout, QPushButton, QMessageBox
from PySide6.QtGui import QIcon

from .widgets import VehicleWidget, VehicleWidgetMode, SafeMathLineEdit, LargeLabel
from . import base

from brickedit import *

from copy import deepcopy
from os import path, makedirs
import math


def mat_mult_vec(mat, vec):
    x = mat[0][0]*vec.x + mat[0][1]*vec.y + mat[0][2]*vec.z
    y = mat[1][0]*vec.x + mat[1][1]*vec.y + mat[1][2]*vec.z
    z = mat[2][0]*vec.x + mat[2][1]*vec.y + mat[2][2]*vec.z
    return Vec3(x, y, z)

def mat_mult_mat(a, b):
    result = [[0,0,0],[0,0,0],[0,0,0]]
    for i in range(3):
        for j in range(3):
            result[i][j] = a[i][0]*b[0][j] + a[i][1]*b[1][j] + a[i][2]*b[2][j]
    return result

def rotation_matrix_from_euler(rot: Vec3):
    rx, ry, rz = math.radians(-rot.x), math.radians(rot.y), math.radians(rot.z)
    # X rotation
    Rx = [
        [1, 0, 0],
        [0, math.cos(rx), -math.sin(rx)],
        [0, math.sin(rx), math.cos(rx)]
    ]
    # Y rotation
    Ry = [
        [math.cos(ry), 0, math.sin(ry)],
        [0, 1, 0],
        [-math.sin(ry), 0, math.cos(ry)]
    ]
    # Z rotation
    Rz = [
        [math.cos(rz), -math.sin(rz), 0],
        [math.sin(rz), math.cos(rz), 0],
        [0, 0, 1]
    ]
    # Combined: R = Rz * Ry * Rx
    return mat_mult_mat(Rz, mat_mult_mat(Ry, Rx))

def euler_from_rotation_matrix(R):
    """
    Extract Euler angles from rotation matrix.
    Assumes rotation order X -> Y -> Z.
    """
    if abs(R[2][0]) < 1.0:
        ry = -math.asin(R[2][0])
        cos_ry = math.cos(ry)
        rx = math.atan2(R[2][1]/cos_ry, R[2][2]/cos_ry)
        rz = math.atan2(R[1][0]/cos_ry, R[0][0]/cos_ry)
    else:  # Gimbal lock
        ry = -math.asin(R[2][0])
        rx = 0
        rz = math.atan2(-R[0][1], R[1][1])
    return Vec3(math.degrees(rx), math.degrees(ry), math.degrees(rz))


def apply_rotation(pos: Vec3, rot: Vec3, rotation_deg: Vec3, rotation_center: Vec3):
    # Build rotation matrices
    R_brick = rotation_matrix_from_euler(rot)
    R_global = rotation_matrix_from_euler(rotation_deg)
    
    # Combined rotation: first brick rotation, then global rotation
    R_combined = mat_mult_mat(R_global, R_brick)
    
    # Rotate position around center
    translated = pos - rotation_center
    rotated_pos = mat_mult_vec(R_global, translated) + rotation_center
    
    # Convert combined rotation back to Euler angles
    final_rot = euler_from_rotation_matrix(R_combined)
    
    return rotated_pos, final_rot



class VehicleUpscalerMenu(base.BaseMenu):
    """Menu for upscaling vehicle properties."""

    def __init__(self, mw):
        super().__init__(mw)

        self.vehicle_selector = VehicleWidget(VehicleWidgetMode.SELECT_AND_RELOAD, [self.update_vehicle_is_reloaded])
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
        self.pos_x_le = SafeMathLineEdit(0)
        self.pos_y_le = SafeMathLineEdit(0)
        self.pos_z_le = SafeMathLineEdit(0)
        self.pos_layout.addWidget(self.pos_x_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.pos_x_le)
        self.pos_layout.addWidget(self.pos_y_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.pos_y_le)
        self.pos_layout.addWidget(self.pos_z_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.pos_z_le)

        # Rotation modificaiton
        self.rot_label = LargeLabel("Rotation", 4)
        self.master_layout.addWidget(self.rot_label)

        self.wip_rot_label = QLabel("Rotation is Work-in-Progress.")
        self.wip_rot_label.setWordWrap(True)
        self.master_layout.addWidget(self.wip_rot_label)

        # layout
        self.rot_deg_layout = QHBoxLayout()
        # self.master_layout.addLayout(self.rot_deg_layout)
        # Label
        self.rot_deg_label = QLabel("Rotation (°):")
        # self.rot_deg_layout.addWidget(self.rot_deg_label, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_deg_label)
        # X Y Z inputs
        self.rot_deg_x_le = SafeMathLineEdit(0)
        self.rot_deg_y_le = SafeMathLineEdit(0)
        self.rot_deg_z_le = SafeMathLineEdit(0)
        # self.rot_deg_layout.addWidget(self.rot_deg_x_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_deg_x_le)
        # self.rot_deg_layout.addWidget(self.rot_deg_y_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_deg_y_le)
        # self.rot_deg_layout.addWidget(self.rot_deg_z_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_deg_z_le)

        # Layout
        self.rot_center_layout = QHBoxLayout()
        self.rot_connection_warning = QLabel("Warning: modifying these settings will likely mess up connections.\nThis will not affect welded bricks.")
        self.rot_connection_warning.setWordWrap(True)
        # self.master_layout.addWidget(self.rot_connection_warning)
        # Label
        # self.master_layout.addLayout(self.rot_center_layout)
        self.rot_center_label = QLabel("Center (cm):")
        # self.rot_center_layout.addWidget(self.rot_center_label, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_center_label)
        # X Y Z inputs
        self.rot_center_x_le = SafeMathLineEdit(0)
        self.rot_center_y_le = SafeMathLineEdit(0)
        self.rot_center_z_le = SafeMathLineEdit(0)
        # self.rot_center_layout.addWidget(self.rot_center_x_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_center_x_le)
        # self.rot_center_layout.addWidget(self.rot_center_y_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_center_y_le)
        # self.rot_center_layout.addWidget(self.rot_center_z_le, 10)
        self.disabled_if_vehicle_not_loaded.append(self.rot_center_z_le)

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
        self.scale_mult_le = SafeMathLineEdit(1)
        self.scale_mult_le.editingFinished.connect(lambda: self.scale_input_updated(True))
        self.scale_mult_layout.addWidget(self.scale_mult_le, 30)
        
        self.disabled_if_vehicle_not_loaded.append(self.scale_mult_le)
        # Divisor
        self.scale_div_layout = QHBoxLayout()
        self.master_layout.addLayout(self.scale_div_layout)
        self.scale_div_label = QLabel("Divide by:")
        self.scale_div_layout.addWidget(self.scale_div_label, 10)
        self.disabled_if_vehicle_not_loaded.append(self.scale_div_label)
        self.scale_div_le = SafeMathLineEdit(1)
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
            self.scale_div_le.setText(str(1 / float(self.scale_mult_le.text())))
            self.scale_div_le.blockSignals(False)
        else:
            self.scale_mult_le.blockSignals(True)
            self.scale_mult_le.setText(str(1 / float(self.scale_div_le.text())))
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
        
        off_x = float(self.pos_x_le.text())
        off_y = float(self.pos_y_le.text())
        off_z = float(self.pos_z_le.text())
        rotdeg_x = float(self.rot_deg_x_le.text())
        rotdeg_y = float(self.rot_deg_y_le.text())
        rotdeg_z = float(self.rot_deg_z_le.text())
        rotcenter_x = float(self.rot_center_x_le.text())
        rotcenter_y = float(self.rot_center_y_le.text())
        rotcenter_z = float(self.rot_center_z_le.text())
        scale = float(self.scale_mult_le.text())
        
        must_offset = (off_x != 0) or (off_y != 0) or (off_z != 0)
        must_rot = rotdeg_x != 0 or rotdeg_y != 0 or rotdeg_z != 0
        must_scale = scale != 1

        if must_offset:
            for brick in brv.bricks:
                brick.pos += Vec3(off_x, off_y, off_z)

        if must_rot:
            for brick in brv.bricks:
                brick.pos, brick.rot = apply_rotation(
                    brick.pos, brick.rot,
                    Vec3(rotdeg_x, rotdeg_y, rotdeg_z),
                    Vec3(rotcenter_x, rotcenter_y, rotcenter_z)
                )

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



        try:
            # Serialize and save
            serialized = brv.serialize()
            with open(self.vehicle_selector.brv_file, "wb") as f:
                f.write(serialized)

        # Message box in case of bugs
        except PermissionError as e:
            QMessageBox.critical(self, "Failed to save changes",
                f"BrickEdit-Interface was denied permission to save changes: {str(e)}"
            )
        except OSError as e:
            QMessageBox.critical(self, "Failed to save changes",
                f"BrickEdit-Interface could not save changes: {str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Failed to save changes",
                f"BrickEdit failed to save changes (most likely failed to serialize). Please report the following errors to the developers:\n\n{type(e).__name__}: {str(e)}"
            )
            raise e

        QMessageBox.information(self, "BrickEdit-Interface", "Successfully saved changes.")



    def get_menu_name(self) -> str:
        return "Vehicle Transformer"

    def get_icon(self) -> QIcon:
        return QIcon(":/assets/icons/GizmoIcon.png")
