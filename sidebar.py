from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QToolButton, QSizePolicy
)
from PySide6.QtGui import QIcon


class Sidebar(QWidget):
    """Sidebar navigation for menu selection."""
    
    menu_changed = Signal(int)

    def __init__(self, menu_configs):
        """
        Initialize the sidebar with menu buttons.
        
        Args:
            menu_configs: List of dicts with 'name' and 'icon_path' keys.
        """
        super().__init__()
        
        # Default menu configurations if none provided

        self.setFixedWidth(50)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 0, 0)
        layout.setSpacing(6)

        self.buttons = []

        for index, config in enumerate(menu_configs):
            btn = QToolButton()
            btn.setToolTip(config.get('name', f'Menu {index}'))
            btn.setIcon(config.get('icon', QIcon(':/assets/icons/placeholder.png')))
            btn.setIconSize(QSize(24, 24))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
            btn.setFixedSize(40, 40)

            btn.setStyleSheet("""
                QToolButton {
                    border-radius: 6px;
                }
                QToolButton:hover {
                    background-color: rgba(255, 255, 255, 0.08);
                }
                QToolButton:checked {
                    background-color: rgba(255, 255, 255, 0.15);
                }
            """)

            btn.clicked.connect(
                lambda checked, i=index: self.menu_changed.emit(i)
            )

            self.buttons.append(btn)
            layout.addWidget(btn)

        if self.buttons:
            self.buttons[0].setChecked(True)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
