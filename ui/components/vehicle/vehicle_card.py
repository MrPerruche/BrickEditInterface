from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QSizePolicy
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QSize, Signal

from os.path import join, exists
from datetime import datetime, UTC
from struct import error as struct_error
from dataclasses import dataclass

from ui.widgets import Widget, Label, Surface, SurfaceStyle, SurfaceRole
from ui.theme import Theme, register_has_theme_and_apply

from utils import str_time_since, scale_pixmap

import brickedit


def safe_from_net_ticks(ticks: int, fallback = None):
    try:
        return brickedit.vhelper.from_net_ticks(ticks)
    except (OverflowError, ValueError):
        return fallback


@dataclass
class VehicleCardData:
    name: str
    brick_count: int
    creation_time: int
    last_update_time: int

    ambiguous_brick_count: tuple[bool, int] = (False, 0)

    @staticmethod
    def load_path_silent(path: str) -> tuple['VehicleCardData', Exception | None]:
        brm_path = join(path, "MetaData.brm")
        brv_path = join(path, "Vehicle.brv")
        try:
            if not exists(brm_path):
                raise FileNotFoundError(f"BRM file not found: {brm_path}")
            with open(brm_path, "rb") as f:
                brm = bytearray(f.read())

            brv_first3bytes = None
            if exists(brv_path):
                with open(brv_path, "rb") as f:
                    brv_first3bytes = bytearray(f.read(3))

            return VehicleCardData.load_brm_silent(brm, brv_first3bytes)

        except Exception as e:
            return VehicleCardData("", 0, 0, 0), e

    @staticmethod
    def load_brm_silent(brm: bytearray, brv_first3bytes: bytearray | None = None) -> tuple['VehicleCardData', Exception | None]:
        """Loads a BRM file. If an exception occurs, it is returned and the function fails silently."""
        try:
            version = brm[0]  # TODO: Update BrickEdit to add a safer get_version() func / method.
            if version < 7:  # BrickEdit only supports down to version 16 but can technically load metadata down to version 7 (Brick Rigs 1.0)
                raise ValueError(f"Invalid version for Brick Rigs Metadata files. Expected 7 or higher, got {version}.")

            brmfile = brickedit.BRMFile(version)
            try:
                name, brick_count, creation_time, last_update_time = brmfile.deserialize(
                    brm, config=VehicleCard.brm_loading_profile, auto_version = True
                )
            except struct_error:
                name, brick_count = brmfile.deserialize(
                    brm, config=VehicleCard.reduced_brm_loading_profile, auto_version = True
                )
                creation_time, last_update_time = 0, 0
            ambiguous_brick_count = False
            brick_count_brv = 0

            # Load parts of the BRV to get brickcount
            if brv_first3bytes is not None and brv_first3bytes[0] >= 7:
                brick_count_brv = brv_first3bytes[1] + 256 * brv_first3bytes[2]  # Could deserialization get any lazier (brickcount is u16 LE in byte 2 and 3 for BRV >= 7)
                if brick_count != brick_count_brv:
                    ambiguous_brick_count = True
                    brick_count = brick_count_brv

            # self.update_widget(
            #     update_thumbnail=True,
            #     name=name,
            #     brick_count=brick_count,
            #     creation_time=creation_time,
            #     last_update_time=last_update_time,
            #     brick_count_uncertain=(ambiguous_brick_count, brick_count_brv)
            # )

            return (VehicleCardData(
                name=name,
                brick_count=brick_count,
                creation_time=creation_time,
                last_update_time=last_update_time,
                ambiguous_brick_count=(ambiguous_brick_count, brick_count_brv)
            ), None)

        except Exception as e:
            return (VehicleCardData("", 0, 0, 0), e)
        


def format_vehicle_card_texts(vehicle_card_data: "VehicleCardData") -> tuple[str, str, str]:
    """(display name, date text, brick count text) shown on a vehicle card."""
    name = vehicle_card_data.name
    brick_count = vehicle_card_data.brick_count
    creation_time = vehicle_card_data.creation_time
    last_update_time = vehicle_card_data.last_update_time
    brick_count_uncertain = vehicle_card_data.ambiguous_brick_count

    # Display name
    display_name = name if name is not None and name else "Unnamed"

    # Brick count
    if brick_count <= 0:
        display_brick_count = "Empty" + ("*" if brick_count_uncertain[0] else "")
    elif brick_count == 1:
        display_brick_count = "1*\nbrick" if brick_count_uncertain[0] else "1\nbrick"
    else:
        display_brick_count = f"{brick_count}{'*' if brick_count_uncertain[0] else ''}\nbricks"

    # Make times safe (if above 9 quint limit, set to 0)
    if creation_time > 0x7F_FF_FF_FF_FF_FF_FF_FF:
        creation_time = 0
    if last_update_time > 0x7F_FF_FF_FF_FF_FF_FF_FF:
        last_update_time = 0
    # Make datetimes from .NET ticks
    current_datetime = datetime.now(UTC)
    creation_datetime = safe_from_net_ticks(creation_time)
    last_update_datetime = safe_from_net_ticks(last_update_time)
    if creation_datetime is None:
        creation_datetime = safe_from_net_ticks(0)
    if last_update_datetime is None:
        last_update_datetime = safe_from_net_ticks(0)
    # Datetime -> Jan 23, 4567
    creation_date_str = f"{creation_datetime.strftime('%b')} {creation_datetime.day}, {creation_datetime.year}"
    last_update_date_str = f"{last_update_datetime.strftime('%b')} {last_update_datetime.day}, {last_update_datetime.year}"
    # Create timedeltas for time since
    creation_since = current_datetime - creation_datetime
    last_update_since = current_datetime - last_update_datetime
    # Format timedeltas
    creation_since_str = str_time_since(int(creation_since.total_seconds()))
    last_update_since_str = str_time_since(int(last_update_since.total_seconds()))
    # Show text
    creation_str = f"Created {creation_date_str} ({creation_since_str})" if creation_time != 0 else "Creation date unknown"
    last_update_str = f"Last saved {last_update_date_str} ({last_update_since_str})" if last_update_time != 0 else "Last saved date unknown"
    return display_name, f"{creation_str}\n{last_update_str}", display_brick_count


class VehicleCard(Widget):

    clicked = Signal(str)

    thumbnail_size = 56, 56

    brm_loading_profile = brickedit.BRMDeserializationConfig(
        name = True,
        brick_count = True,
        creation_time = True,
        last_update_time = True
    )
    reduced_brm_loading_profile = brickedit.BRMDeserializationConfig(
        name=True,
        brick_count=True
    )


    def __init__(self, vehicle_path: str, is_active: bool, vehicle_card_data: VehicleCardData | None = None, parent=None):
        super().__init__(parent=parent)
        self.setProperty("vehicle_card", True)

        self.is_active = is_active
        self.surface_style = SurfaceStyle.ACCENT if is_active else SurfaceStyle.REGULAR

        self.vehicle_path = vehicle_path

        # Master layout in Surface block
        self.true_master_layout = QVBoxLayout()
        self.true_master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.true_master_layout)
        self.surface = Surface(highlight=True, role=SurfaceRole.BUTTONLIKE)
        self.surface.clicked.connect(self.on_clicked)
        self.surface.add_to_widget_content_margins(-4, -4, -2, -4)
        self.true_master_layout.addWidget(self.surface)
        self.master_layout = self.surface.layout()

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum
        )

        # --- PREP

        self.no_thumbnail = QIcon(':/assets/icons/missing_thumbnail_v2.png')

        # --- RENDER

        # Left side
        self.thumbnail_content_layout = QHBoxLayout()
        self.thumbnail_content_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(self.thumbnail_content_layout)

        # Thumbnail
        self.thumbnail_label = Label()
        self.thumbnail_label.setContentsMargins(0, 0, 0, 0)
        self.thumbnail_content_layout.addWidget(self.thumbnail_label)
        self.set_icon(
            self.no_thumbnail.pixmap(QSize(*self.thumbnail_size))
        )


        # Middle
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.thumbnail_content_layout.addLayout(self.content_layout, stretch=1)

        # Name and brickcount
        self.name_label = Label("Unnamed")
        self.name_label.setMinimumWidth(0)
        self.name_label.qt_widget.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred
        )
        self.content_layout.addWidget(self.name_label)

        # Date and info
        self.info_layout = QHBoxLayout()
        self.info_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addLayout(self.info_layout)
        # Date label
        self.date_label = Label("Creation date unknown\nLast saved date unknown", 11, muted=True)
        self.info_layout.addWidget(self.date_label)
        # self.info_layout.addStretch(1)
        # Brick count label
        self.brick_count_label = Label("Empty", 11, muted=True)
        self.brick_count_label.qt_widget.setAlignment(Qt.AlignRight)
        self.info_layout.addWidget(self.brick_count_label)

        # ----------------------

        if vehicle_card_data is None:
            result = self.load_vehicle_path_silent(self.vehicle_path)
        else:
            result = self.load_vehicle_data_silent(vehicle_card_data)
        if result is not None:
            raise result

        register_has_theme_and_apply(self)


    def on_clicked(self):
        self.clicked.emit(self.vehicle_path)


    def load_vehicle_path_silent(self, vehicle_path: str) -> Exception | None:
        brm_path = join(vehicle_path, "MetaData.brm")
        brv_path = join(vehicle_path, "Vehicle.brv")  # Uncertain
        try:
            result, e = VehicleCardData.load_path_silent(vehicle_path)
            if e is not None:
                return e

            self.update_widget(
                update_thumbnail=True,
                vehicle_card_data=result
            )
            return None

        except Exception as e:
            return e


    def load_vehicle_data_silent(self, vehicle_card_data: VehicleCardData) -> Exception | None:
        try:
            if not exists(join(self.vehicle_path, "MetaData.brm")):
                raise FileNotFoundError(f"BRM file not found: {join(self.vehicle_path, 'MetaData.brm')}")
            self.update_widget(
                update_thumbnail=True,
                vehicle_card_data=vehicle_card_data
            )
            return None

        except Exception as e:
            return e


    def update_widget(self,
        update_thumbnail: bool,
        vehicle_card_data: VehicleCardData
    ):
        display_name, date_text, display_brick_count = format_vehicle_card_texts(vehicle_card_data)
        self.name_label.set_text(display_name)
        self.brick_count_label.set_text(display_brick_count)
        self.date_label.set_text(date_text)


        # Thumbnail
        if not update_thumbnail:
            return

        thumbnail_path = join(self.vehicle_path, "Preview.png")
        if exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            self.set_icon(pixmap)
        else:
            self.set_icon_no_thumbnail()



    def set_icon_no_thumbnail(self):
        return self.set_icon(self.no_thumbnail.pixmap(QSize(*self.thumbnail_size)))


    def set_icon(self, pixmap: QPixmap):
        new_pixmap = scale_pixmap(pixmap, *self.thumbnail_size)
        self.thumbnail_label.qt_widget.setPixmap(new_pixmap)


    def set_active(self, active: bool):
        self.is_active = active
        self.surface.set_surface_style(SurfaceStyle.ACCENT if self.is_active else SurfaceStyle.REGULAR)
    

    def _apply_theme(self, theme: Theme):
        text_col = theme.text.color
        border_col = theme.accent_border.color if self.is_active else theme.border.color
        self.setStyleSheet(f"""
            *[vehicle_card] {{
                color: {text_col};

                border: 2px solid {border_col};
                border-radius: 4px;

                padding: 1px 4px;

                font-size: 13pt;
            }}
        """)
        self.surface.set_surface_style(SurfaceStyle.ACCENT if self.is_active else SurfaceStyle.REGULAR)
