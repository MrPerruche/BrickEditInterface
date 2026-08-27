from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QIcon, QRegularExpressionValidator

from ui.widgets import Label, Button, Slider, ComboBox, LineEdit, NumberChannelEdit, ChannelMode, StyledLabel, LabelStyle, Switcher, SwitcherEntry
from ui.dialogs import CorruptStateDialog
import ui.theme as theme
from ui.models import TooltipContents

from menus import base
from ..shared_widgets import TabMenu


class DeveloperTestMenu(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)

        # --------------------- LAYOUT 1 ----------------------


        layout1 = QVBoxLayout()
        layout1.setContentsMargins(0, 0, 0, 0)

        nce11 = NumberChannelEdit()
        nce11.set_placeholder("Float 32, no clamps")
        layout1.addWidget(nce11)

        nce12 = NumberChannelEdit(minimum=0)
        nce12.set_placeholder("Float 32, [0, +inf]")
        layout1.addWidget(nce12)

        nce13 = NumberChannelEdit(mode=ChannelMode.FLOAT64, allow_nan=False)
        nce13.set_placeholder("Float 64, no NaN")
        layout1.addWidget(nce13)

        ncesl1411 = StyledLabel("NUM FRACTIONAL DIGITS", style=LabelStyle.SUBTEXT_1)
        layout1.addWidget(ncesl1411)

        nce14 = NumberChannelEdit(mode=ChannelMode.INT, minimum=-128, maximum=127)
        nce14.set_placeholder("Int, [-128, 127]")
        layout1.addWidget(nce14)

        button11 = Button("Open Corrupt State Dialog")
        button11.clicked.connect(self.button11_clicked)
        layout1.addWidget(button11)

        layout1.addStretch()


        # --------------------- LAYOUT 2 ----------------------

        layout2 = QVBoxLayout()
        layout2.setContentsMargins(0, 0, 0, 0)
        label21 = Label("Hello, World ☆")
        layout2.addWidget(label21)
        label22 = Label("Hello, World 2")
        label22.set_tooltip(TooltipContents("hello", "world world world world"))
        layout2.addWidget(label22)

        themes_layout = QHBoxLayout()
        layout2.addLayout(themes_layout)

        self.theme_idx = 0
        self.themes = theme.theme_manager.themes
        button21 = Button("Change theme: Dark")
        button21.clicked.connect(self.button21_clicked)
        button21.qt_widget.setToolTip("<b>Click to change theme</b><br/>test1<br/><br/>Test2<br/><br/>Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3 Test3")
        self.button21 = button21
        themes_layout.addWidget(button21)

        QICON_1 = QIcon(":/assets/icons/HomeIcon.png")
        QICON_2 = QIcon(":/assets/icons/GradientIcon.png")
        combobox21 = ComboBox()
        combobox21.add_item("World", QICON_1)
        combobox21.add_item("World 2", QICON_2)
        themes_layout.addWidget(combobox21)

        slider21 = Slider(range(0, 50, 5), 15)
        slider21.set_text("Value is 15", 80)
        slider21.value_changed.connect(self.update_slider21)
        self.slider21 = slider21
        layout2.addWidget(slider21)


        lineedit21 = LineEdit('1A2B3C4D')
        validator = QRegularExpressionValidator("^[0-9A-Fa-f]{8}$")
        lineedit21.set_validator(validator)
        layout2.addWidget(lineedit21)


        layout2.addStretch()

        self.switcher = Switcher([
            SwitcherEntry("Layout 1", layout=layout1),
            SwitcherEntry("Layout 2", layout=layout2)
        ])
        self.master_layout.addWidget(self.switcher)


        self.master_layout.addStretch()

    def button11_clicked(self):
        CorruptStateDialog.create(self.mw, None).exec(blocking=False)

    def button21_clicked(self):
        self.theme_idx = (self.theme_idx + 1) % len(self.themes)
        new_theme = self.themes[self.theme_idx]
        theme.theme_manager.set_theme(new_theme)
        self.button21.set_text(f"Change theme: {new_theme.display_name}")
        
    def update_slider21(self):
        self.slider21.set_text(f"Value is {self.slider21.get_value()}", 80)

    def get_menu_name(self):
        return "Developer tests"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(":/assets/icons/unknown.png"), True)
