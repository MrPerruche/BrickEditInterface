from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QStyle, QHBoxLayout
from PySide6.QtGui import QIcon, QColor, QBrush
from PySide6.QtCore import Qt, QRect

from ui.widgets import Widget
from ui.theme import Theme, register_has_theme_and_apply, theme_manager

from utils import stack_qcolors, tint_icon



class ComboBoxItemDelegate(QStyledItemDelegate):

    def __init__(self, theme, combo_box, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.combo_box = combo_box

    def set_theme(self, theme):
        self.theme = theme
        self.combo_box.view().viewport().update()

    def paint(self, painter, option, index):
        painter.save()

        background = QColor(self.theme.background.color_hex_argb)
        surface = stack_qcolors(background, QColor(self.theme.surface.color_hex_argb))

        # Base background for every item
        painter.fillRect(option.rect, background)

        # Hover/selection overlay
        if option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, surface)

        elif option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, surface)

        # --- Icon ---
        icon = index.data(Qt.DecorationRole)

        x = option.rect.left() + 6
        icon_size = option.decorationSize

        if isinstance(icon, QIcon):
            icon_rect = QRect(
                x,
                option.rect.center().y() - icon_size.height() // 2,
                icon_size.width(),
                icon_size.height(),
            )

            # IMPORTANT:
            # Explicitly request the normal icon.
            icon.paint(
                painter,
                icon_rect,
                Qt.AlignCenter,
                QIcon.Normal,
                QIcon.Off,
            )

        # --- Text ---
        text = index.data(Qt.DisplayRole)

        icon = index.data(Qt.DecorationRole)

        icon_width = 0
        if isinstance(icon, QIcon) and not icon.isNull():
            icon_width = option.decorationSize.width()
            icon_rect = QRect(
                option.rect.left() + 6,
                option.rect.center().y() - option.decorationSize.height() // 2,
                option.decorationSize.width(),
                option.decorationSize.height(),
            )
            icon.paint(
                painter,
                icon_rect,
                Qt.AlignCenter,
                QIcon.Normal,
                QIcon.Off,
            )
        text_x = option.rect.left() + 6 + icon_width

        if icon_width:
            text_x += 8

        painter.setPen(QColor(self.theme.text.color_hex_argb))

        painter.drawText(
            text_x,
            option.rect.top(),
            option.rect.width() - text_x,
            option.rect.height(),
            Qt.AlignVCenter | Qt.AlignLeft,
            text,
        )

        painter.restore()



class ComboBox(Widget):

    def __init__(self, tint_icons: bool = True, parent=None):
        super().__init__(parent)
        self.tint_icons = tint_icons
        self._og_icons = []

        self.master_layout = QHBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.qt_widget = QComboBox()
        self.master_layout.addWidget(self.qt_widget)
        
        self.delegate = ComboBoxItemDelegate(
            theme_manager.current(),
            self.qt_widget
        )
        self.qt_widget.view().setItemDelegate(self.delegate)

        self.item_changed = self.qt_widget.currentIndexChanged

        register_has_theme_and_apply(self)


    def get_current_idx(self) -> int:
        return self.qt_widget.currentIndex()

    def get_current_text(self) -> str:
        return self.qt_widget.currentText()

    def set_current_idx(self, idx: int):
        self.qt_widget.setCurrentIndex(idx)

    def clear_items(self):
        self.qt_widget.clear()

    def add_item(self, text: str, icon: QIcon | None = None, *args, **kwargs):
        self._og_icons.append(icon)
        if icon is None:
            self.qt_widget.addItem(text, *args, **kwargs)
        else:
            if self.tint_icons:  # Do here this way we don't have to update all other icons and have O(n2) (theres enough O(n2) as is)
                icon_col = theme_manager.current().text.color_hex_argb
                icon = tint_icon(icon, icon_col)
            self.qt_widget.addItem(icon, text, *args, **kwargs)


    def _apply_theme(self, theme: Theme):

        if self.tint_icons:
            for i, icon in enumerate(self._og_icons):
                if icon is not None:
                    icon = tint_icon(icon, theme.text.color_hex_argb)
                    self.qt_widget.setItemIcon(i, icon)

        self.delegate.set_theme(theme)
        self.setStyleSheet(f"""
            QComboBox {{
                color: {theme.text.color};
                background-color: {theme.surface.color};

                border: 2px solid {theme.border.color};
                border-radius: 4px;

                padding: 0px 4px;

                font-size: 13pt;
            }}

            QComboBox:hover {{
                background-color: {theme.surface.color_double};
                border-color: {theme.border.color};
            }}

            QComboBox:pressed {{
                background-color: {theme.surface.muted};
            }}

            QComboBox::drop-down {{
                width: 22px;
                border: none;
                background: transparent;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}

            QComboBox::down-arrow {{
                image: url(:/assets/icons/ExpandSmallIcon.png);
                width: 12px;
                height: 12px;
            }}

            QComboBox QAbstractItemView {{
                background: {theme.border.color};
                border: 2px solid;
                border-radius: 4px;
            }}

            QComboBox QAbstractItemView::item {{
                height: 26px;
            }}
        """)
