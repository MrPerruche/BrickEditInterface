from PySide6.QtWidgets import QRadioButton, QButtonGroup, QComboBox
from PySide6.QtGui import QIcon
from coloraide import Color

from menus import base
from ..shared_widgets import *

from enum import Enum
from dataclasses import dataclass
import os

from brickedit import vhelper
from utils import try_serialize, try_serialize_metadata


@dataclass(frozen=True)
class ColorSpace:
    name: str
    extended_name: str
    info: str | None
    code: str

class ColorSpaces(Enum):
    OKLAB = ColorSpace("Oklab", "Lightness Green-Red Blue-Yellow", "perceptual, recommended", "oklab")
    OKLCH = ColorSpace("Oklch", "Lightness Chroma Hue", "perceptual, recommended", "oklch")
    LINEAR_RGB = ColorSpace("Linear RGB", "Red Green Blue", "produce dull colors", "linear_rgb")
    SRGB = ColorSpace("sRGB", "Red Green Blue", None, "srgb")
    HSV = ColorSpace("HSV", "Hue Saturation Value", "used by Brick Rigs", "hsv")
    # HSL = ColorSpace("HSL", "Hue Saturation Lightness", None)
    # CMYK = ColorSpace("CMYK", "Cyan Magenta Yellow Black / Key", None)

ID_TO_COLORSPACE = [ColorSpaces.OKLAB, ColorSpaces.OKLCH, ColorSpaces.LINEAR_RGB, ColorSpaces.SRGB, ColorSpaces.HSV]
COLORSPACE_TO_ID = {colorspace: i for i, colorspace in enumerate(ID_TO_COLORSPACE)}




def lerp(x: float, a: float, b: float) -> float:
    return a + (b - a) * x


def lerp_angle(
    x: float,
    a1: float,
    a2: float,
    *,
    period: float,
    long_arc: bool = False
) -> float:
    """
    Interpolates between a1 and a2 on a circle.
    a1, a2 in same units, range [0, period)
    """
    da = (a2 - a1) % period

    if not long_arc:
        if da > period / 2:
            da -= period
    else:
        if da < period / 2:
            da -= period

    return (a1 + x * da) % period


def oklab_to_oklch(L: float, a: float, b: float) -> tuple[float, float, float]:
    C = math.sqrt(a * a + b * b)
    h = math.atan2(b, a)
    return L, C, h


def oklch_to_oklab(L: float, C: float, h: float) -> tuple[float, float, float]:
    a = C * math.cos(h)
    b = C * math.sin(h)
    return L, a, b


def qcolor_to_coloraide_srgb(col: QColor) -> Color:
    r, g, b, _ = col.getRgbF()
    return Color('srgb', [r, g, b])


def interpolate_color(x: float, col1: QColor, col2: QColor, cs: ColorSpaces, long_arc: bool) -> tuple[int, int, int, int]:
    """Takes a color space and interpolates between two colors. Returns in LINEAR RGB 0 - 255"""

    match cs:

        case ColorSpaces.OKLAB | ColorSpaces.OKLCH:
            c1 = qcolor_to_coloraide_srgb(col1)
            c2 = qcolor_to_coloraide_srgb(col2)

            a1 = col1.alphaF()
            a2 = col2.alphaF()
            alpha = lerp(x, a1, a2)

            if cs is ColorSpaces.OKLAB:
                L1, a_1, b_1 = c1.convert('oklab').coords()
                L2, a_2, b_2 = c2.convert('oklab').coords()

                L = lerp(x, L1, L2)
                a = lerp(x, a_1, a_2)
                b = lerp(x, b_1, b_2)

                out = Color('oklab', [L, a, b]).convert('srgb')

            else:  # OKLCH
                L1, C1, h1 = c1.convert('oklch').coords()
                L2, C2, h2 = c2.convert('oklch').coords()

                L = lerp(x, L1, L2)
                C = lerp(x, C1, C2)
                h = lerp_angle(x, h1, h2, period=360.0, long_arc=long_arc)

                out = Color('oklch', [L, C, h]).convert('srgb')

            r, g, b = out.coords()

            return (
                int(max(0.0, min(1.0, r)) * 255),
                int(max(0.0, min(1.0, g)) * 255),
                int(max(0.0, min(1.0, b)) * 255),
                int(alpha * 255),
            )



        case ColorSpaces.LINEAR_RGB:
            r1, g1, b1, a1 = col1.getRgbF()
            r1, g1, b1 = vhelper.color.multi_linear_to_srgb(r1, g1, b1)
            r2, g2, b2, a2 = col2.getRgbF()
            r2, g2, b2 = vhelper.color.multi_linear_to_srgb(r2, g2, b2)
            return int(lerp(x, r1, r2) * 255), int(lerp(x, g1, g2) * 255), int(lerp(x, b1, b2) * 255), int(lerp(x, a1, a2) * 255)


        case ColorSpaces.SRGB:
            r1, g1, b1, a1 = col1.getRgbF()
            r2, g2, b2, a2 = col2.getRgbF()
            # r1, g1, b1 = vhelper.color.multi_linear_to_srgb(r1, g1, b1)
            # r2, g2, b2 = vhelper.color.multi_linear_to_srgb(r2, g2, b2)
            return int(lerp(x, r1, r2) * 255), int(lerp(x, g1, g2) * 255), int(lerp(x, b1, b2) * 255), int(lerp(x, a1, a2) * 255)


        case ColorSpaces.HSV:
            h1, s1, v1, a1 = col1.getHsvF()
            h2, s2, v2, a2 = col2.getHsvF()

            h = lerp_angle(x, h1, h2, period=1.0, long_arc=long_arc)
            s = lerp(x, s1, s2)
            v = lerp(x, v1, v2)

            r, g, b = vhelper.color.hsv_to_rgb(h * 360, s, v)

            return (
                int(r * 255),
                int(g * 255),
                int(b * 255),
                int(lerp(x, a1, a2) * 255),
            )



class GradientMaker(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)
        
        # Values
        self.color_space = COLORSPACE_TO_ID[ColorSpaces.OKLAB]


        # Color selector
        self.col_sel_widget = MultiColorSelectorWidget()
        self.master_layout.addWidget(self.col_sel_widget)


        # Settings:
        # Layout
        self.settings_widget = SquareWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        self.master_layout.addWidget(self.settings_widget)
        
        # Num bricks
        self.bricks_layout = QHBoxLayout()
        self.settings_layout.addLayout(self.bricks_layout)
        self.num_bricks_label = QLabel("Bricks")
        self.bricks_layout.addWidget(self.num_bricks_label, 10)
        # self.num_bricks_spin = SafeMathLineEdit(12, min_val=2, max_val=5_000, integer=True)
        self.num_bricks_spin = ExpressionWidget("12", ExpressionType.INTEGER, clamps=(2, 5000))
        self.bricks_layout.addWidget(self.num_bricks_spin, 40)

        # Brick type
        special_bricks = [bt.TEXT_BRICK.name(), bt.TEXT_CYLINDER.name(), bt.SPINNER_BRICK.name()]
        special_bricks_str = ", ".join(special_bricks)

        self.brick_type_info = QLabel(f"{special_bricks_str} have special interactions.")
        self.brick_type_info.setWordWrap(True)
        self.settings_layout.addWidget(self.brick_type_info)

        self.brick_type_sel = QComboBox()

        # Create the registry
        self.sorted_bt_registry = special_bricks.copy()
        other = [k for k, v in bt.bt_registry.items() if p.BRICK_SIZE in v.p.keys() and k not in special_bricks]
        self.sorted_bt_registry.extend(sorted(other))

        self.brick_type_sel.addItems(self.sorted_bt_registry)
        self.brick_type_sel.setCurrentIndex(self.sorted_bt_registry.index(bt.TEXT_BRICK.name()))
        self.settings_layout.addWidget(self.brick_type_sel)
        
        
        # Colorspace label & buttons
        self.colorspace_label = QLabel("Interpolation color space")
        self.colorspace_label.setWordWrap(True)
        self.settings_layout.addWidget(self.colorspace_label)
        
        self.colorspace_buttons = []
        self.colorspace_sel_group = QButtonGroup()
        self.colorspace_sel_group.setExclusive(True)

        for i, colorspace in enumerate(ID_TO_COLORSPACE):
            radio_button = QRadioButton(f"{colorspace.value.name}" + (f" ({colorspace.value.info})" if colorspace.value.info else ""))
            self.colorspace_sel_group.addButton(radio_button, i)
            if i == self.color_space:
                radio_button.setChecked(True)
            self.colorspace_buttons.append(radio_button)
            self.settings_layout.addWidget(radio_button)

        self.lerp_settings_label = QLabel("Interpolation settings")
        self.lerp_settings_label.setWordWrap(True)
        self.settings_layout.addWidget(self.lerp_settings_label)

        self.longer_hue = QRadioButton("Longer Hue (HSV and Oklch only)")
        self.longer_hue.setChecked(False)
        self.settings_layout.addWidget(self.longer_hue)

        self.colorspace_sel_group.buttonClicked.connect(self.update_colorspace)



        # Display vehicle
        self.vehicle_selector = VehicleWidget(
            VehicleWidgetMode.CREATION,
            must_deserialize=False,
            vehicle_name="bei-gradient"
        )
        self.vehicle_selector.vehicle_name.editingFinished.connect(self.reload_vehicle)
        self.master_layout.addWidget(self.vehicle_selector)


        # Create vehicle
        self.create_vehicle_button = QPushButton("Create vehicle")
        self.create_vehicle_button.clicked.connect(self.create_vehicle)
        self.master_layout.addWidget(self.create_vehicle_button)


        self.reload_vehicle()
        self.update_colorspace()
        self.master_layout.addStretch()


    def get_vehicle_path(self):
        vehicle_name_widget: QLineEdit = self.vehicle_selector.vehicle_name
        return os.path.join(get_vehicles_path(), vehicle_name_widget.text())


    def update_colorspace(self):
        self.color_space = self.colorspace_sel_group.checkedId()
        if self.color_space in (COLORSPACE_TO_ID[ColorSpaces.HSV], COLORSPACE_TO_ID[ColorSpaces.OKLCH]):
            self.longer_hue.setEnabled(True)
        else:
            self.longer_hue.setChecked(False)
            self.longer_hue.setEnabled(False)

    def get_menu_name(self):
        return "Gradient Maker"

    def get_icon(self):
        return QIcon(":/assets/icons/GradientIcon.png")


    def reload_vehicle(self):
        self.vehicle_selector.load_vehicle(self.get_vehicle_path(), silent=True)


    def create_vehicle(self):

        # Get values
        num_bricks: int = self.num_bricks_spin.value()
        colors: list[tuple[QColor, float]] = self.col_sel_widget.get_colors_pos()  # pos between 0 and 100
        colorspace: ColorSpace = ID_TO_COLORSPACE[self.color_space]
        longer_hue: bool = self.longer_hue.isChecked()

        # Make a backup
        path = self.get_vehicle_path()
        description = f"Created using the {self.get_menu_name()}: {num_bricks}-bricks {colorspace.name} gradient"
        self.main_window.backups.full_backup_procedure(path, description)
        
        # CREATE VEHICLE
        # SET THE LIST OF COLORS MAKING THE GRADIENT
        brick_colors = []
        for i in range(num_bricks):
            # Get the linear interpolant
            x = i / (num_bricks-1)

            # Find the index of col2
            color_idx = 0
            while colors[color_idx][1] < x*100:
                color_idx += 1
                if color_idx == len(colors):
                    break
            
            # Get the two colors and the local linear interpolant
            col1_tuple, col2_tuple = colors[color_idx-1], colors[color_idx]
            col1, col2 = col1_tuple[0], col2_tuple[0]
            col1_x, col2_x = col1_tuple[1], col2_tuple[1]
            local_x = (x - col1_x/100) / (col2_x/100 - col1_x/100)
            
            # Interpolate the two colors to get the final color and append to the list
            brick_colors.append(interpolate_color(
                local_x,
                col1, col2,
                colorspace,
                longer_hue
            ))

        brv = BRVFile(FILE_MAIN_VERSION)
        vh = vhelper.ValueHelper(FILE_MAIN_VERSION)

        brick_type = bt.bt_registry.get(self.brick_type_sel.currentText())
        if brick_type is None:
            brick_type = bt.TEXT_BRICK

        brick_size = min(0.5, 6 / num_bricks)  # Minimum between 60cm and a total length under 500cm

        for i, bc in enumerate(brick_colors):
            nbc = vhelper.color.pack_float_to_int(*[c/255 for c in bc])
            color_str = f"{bc[0]:02x}{bc[1]:02x}{bc[2]:02x}"
            
            # Spinner brick
            if brick_type == bt.SPINNER_BRICK:
                angle_per_step = 360 / num_bricks
                brv.add(Brick(
                    ID(f"brick_{i}"),
                    brick_type,
                    pos=Vec3(0, 0, 0),
                    rot=Vec3(0, 0, angle_per_step*i),
                    ppatch={
                        p.BRICK_COLOR: nbc,
                        p.SPINNER_RADIUS: Vec2(200, 200),
                        p.SPINNER_SIZE: Vec2(100, 50),
                        p.SPINNER_ANGLE: angle_per_step
                    }
                ))
            else:
                brv.add(Brick(
                    ID(f"brick_{i}"),
                    brick_type,
                    pos=vh.pos(i*brick_size, 0, 0),
                    rot=Vec3(0, 0, 90),
                    ppatch={
                        p.BRICK_COLOR: nbc,
                        p.BRICK_SIZE: vh.pos(0.5, brick_size, 0.5),
                        p.TEXT: f"Brick {i+1}/{num_bricks}\n#{color_str}",
                        p.FONT: p.Font.ORBITRON,
                        p.FONT_SIZE: 10
                    }
                ))

        serialized = try_serialize(brv)
        if serialized is None:
            return

        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "Vehicle.brv"), "wb") as f:
            f.write(serialized)


        # Metadata
        brm = BRMFile(FILE_MAIN_VERSION, brv)
        serialized_brm = try_serialize_metadata(
            brm,
            self.vehicle_selector.vehicle_name.text(),
            description,
            num_bricks,
            tags=[]
        )

        with open(os.path.join(path, "MetaData.brm"), "wb") as f:
            f.write(serialized_brm)


        self.reload_vehicle()

        QMessageBox.information(self, "Gradient Maker", "Successfully created vehicle.")
