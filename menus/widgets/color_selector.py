from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QToolButton
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon


from .square_widget import SquareWidget
from .float_line_edit import SafeMathLineEdit




class ColorSelectorWidget(SquareWidget):

    def __init__(self, position, position_enabled, duplicate_enabled, remove_enabled):
        super().__init__()

        self.position_enabled = position_enabled
        self.duplicate_enabled = duplicate_enabled
        self.remove_enabled = remove_enabled


        self.master_layout = QVBoxLayout(self)
        self.setLayout(self.master_layout)
        
        # Constants
        self.color_button_size = 64
        self.color_icon_size = 28
        self.color_icon = QIcon(":/assets/icons/BrickEditorIcon.png")

        self.action_button_size = 32
        self.action_icon_size = 16
        self.duplicate_icon = QIcon.fromTheme("edit-copy")
        self.remove_icon = QIcon.fromTheme("edit-delete")

        # Button
        self.color_button = QPushButton()
        # self.color_button.setFixedSize(self.color_button_size, self.color_button_size)
        self.color_button.setFixedHeight(self.color_button_size)
        self.color_button.setIcon(self.color_icon)
        self.color_button.setIconSize(QSize(self.color_icon_size, self.color_icon_size))
        # self.color_button.clicked.connect(self.reroll_color)
        self.master_layout.addWidget(self.color_button)

        # Position
        self.position_layout = QHBoxLayout()
        self.master_layout.addLayout(self.position_layout)

        self.position_le = SafeMathLineEdit(position, self, min_val=0.0, max_val=100.0)
        self.position_layout.addWidget(self.position_le, 1)
        self.position_percent_label = QLabel("%")
        self.position_percent_label.setAlignment(Qt.AlignLeft)
        self.position_layout.addWidget(self.position_percent_label)

        self._apply_color_button_style()
        self.update_disabled()


        # Buttons
        self.button_layout = QHBoxLayout()
        self.master_layout.addLayout(self.button_layout)
        
        self.duplicate_button = QToolButton()
        self.duplicate_button.setFixedHeight(self.action_button_size)
        self.duplicate_button.setIcon(self.duplicate_icon)
        self.duplicate_button.setIconSize(QSize(self.action_icon_size, self.action_icon_size))
        self.button_layout.addWidget(self.duplicate_button)

        self.remove_button = QToolButton()
        self.remove_button.setFixedHeight(self.action_button_size)
        self.remove_button.setIcon(self.remove_icon)
        self.remove_button.setIconSize(QSize(self.action_icon_size, self.action_icon_size))
        self.button_layout.addWidget(self.remove_button)



    def _apply_color_button_style(self):
        r, g, b, a = 255, 127, 127, 192
        # r, g, b, a = self._unpack_color(self.color)
        # r, g, b = self.blend_with_white(r, g, b, (255-a) / 255)
        # self.hex_copy_label.setText(self.get_hex_code(self.color))
        self.color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgb({r}, {g}, {b});
            }}
            QPushButton:pressed {{
                background-color: rgb({max(r - 20, 0)}, {max(g - 20, 0)}, {max(b - 20, 0)});
            }}
        """)


    def update_disabled(self):
        pass



    def set_position_modifiable(self, position_enabled: bool):
        self.position_enabled = position_enabled

    def set_removable(self, remove_enabled: bool):
        self.remove_enabled = remove_enabled
        if not remove_enabled:
            pass

    def set_duplicatable(self, duplicate_enabled: bool):
        self.duplicate_enabled = duplicate_enabled
