from PySide6.QtWidgets import QApplication, QComboBox, QStyledItemDelegate, QStyle, QStyleOptionComboBox, QHBoxLayout
from PySide6.QtGui import QIcon, QColor, QBrush, QPainter, QPixmap
from PySide6.QtCore import Qt, QRect, QSize

from ui.widgets import Widget
from ui.widgets.popup_list import setup_popup_list, SCROLL_BAR_WIDTH
from ui.theme import Theme, register_has_theme_and_apply, theme_manager

from utils import stack_qcolors, tint_icon



SEPARATOR_HEIGHT = 9
TEXT_MARGIN = 6  # Left and right of an item
ICON_SPACING = 8  # Between an item's icon and its text


class ComboBoxItemDelegate(QStyledItemDelegate):

    def __init__(self, theme, combo_box, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.combo_box = combo_box

    def set_theme(self, theme):
        self.theme = theme
        self.combo_box.view().viewport().update()

    @staticmethod
    def _is_separator(index) -> bool:
        return index.data(Qt.AccessibleDescriptionRole) == "separator"  # See QComboBox.insertSeparator

    @staticmethod
    def _icon_width(option, index) -> int:
        icon = index.data(Qt.DecorationRole)
        return option.decorationSize.width() if isinstance(icon, QIcon) and not icon.isNull() else 0

    def sizeHint(self, option, index):
        if self._is_separator(index):
            return QSize(option.rect.width(), SEPARATOR_HEIGHT)
        # Width as laid out by paint: what the popup is widened to (see _ArrowComboBox.showPopup)
        icon_width = self._icon_width(option, index)
        width = (2 * TEXT_MARGIN + (icon_width + ICON_SPACING if icon_width else 0)
                 + option.fontMetrics.horizontalAdvance(index.data(Qt.DisplayRole) or "") + 1)
        return QSize(width, super().sizeHint(option, index).height())

    def paint(self, painter, option, index):
        painter.save()

        background = QColor(self.theme.background.color_hex_argb)
        surface = stack_qcolors(background, QColor(self.theme.surface.color_hex_argb))

        # Base background for every item
        painter.fillRect(option.rect, background)

        if self._is_separator(index):
            y = option.rect.center().y()
            painter.fillRect(QRect(option.rect.left() + 6, y, option.rect.width() - 12, 1),
                             QColor(self.theme.border.color_hex_argb))
            painter.restore()
            return

        # Hover/selection overlay
        if option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, surface)

        elif option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, surface)

        # --- Icon ---
        icon_width = self._icon_width(option, index)
        if icon_width:
            icon_rect = QRect(
                option.rect.left() + TEXT_MARGIN,
                option.rect.center().y() - option.decorationSize.height() // 2,
                option.decorationSize.width(),
                option.decorationSize.height(),
            )
            # Explicitly request the normal icon
            index.data(Qt.DecorationRole).paint(
                painter,
                icon_rect,
                Qt.AlignCenter,
                QIcon.Normal,
                QIcon.Off,
            )

        # --- Text ---
        text_x = option.rect.left() + TEXT_MARGIN + icon_width
        if icon_width:
            text_x += ICON_SPACING
        text_rect = QRect(text_x, option.rect.top(), option.rect.right() - TEXT_MARGIN - text_x + 1, option.rect.height())

        painter.setPen(QColor(self.theme.text.color_hex_argb))
        # Elided when the popup can't be widened enough (see _ArrowComboBox.showPopup)
        text = painter.fontMetrics().elidedText(index.data(Qt.DisplayRole) or "", Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        painter.restore()



class _ArrowComboBox(QComboBox):
    """QComboBox that paints its own drop-down arrow. A stylesheet can only point `image:` at a fixed
    file, so the arrow could never follow the theme's text color. The stylesheet hides the native
    arrow (`image: none`), this paints the tinted one exactly where Qt would have."""

    ARROW_SIZE = 12

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._arrow: QPixmap | None = None
        self._arrow_disabled: QPixmap | None = None

    def set_arrow_pixmaps(self, normal: QPixmap, disabled: QPixmap):
        self._arrow, self._arrow_disabled = normal, disabled
        self.update()

    def showPopup(self):
        # Qt makes the list as wide as the combo box, which can be narrower than its items (eg. RBE's presets): widen
        #  it to fit them, as far as the screen allows (beyond, they are elided)
        view = self.view()
        view.ensurePolished()  # Measured with the stylesheet's font, even before it's first shown
        container = view.window()
        available = self.screen().availableGeometry()
        width = view.sizeHintForColumn(0) + 2 * view.frameWidth()
        if self.count() > self.maxVisibleItems():
            width += SCROLL_BAR_WIDTH
        container.setMinimumWidth(min(width, available.width()))
        # Qt's roll-in animation shows the list in a window of its own, with the system's frame and shadow
        animate = QApplication.isEffectEnabled(Qt.UIEffect.UI_AnimateCombo)
        QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)
        try:
            super().showPopup()
        finally:
            QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, animate)
        # Qt kept it on screen for the combo box's width, not the widened one
        geometry = container.geometry()
        if geometry.right() > available.right():
            container.move(max(available.left(), available.right() - geometry.width() + 1), geometry.y())

    def paintEvent(self, event):
        super().paintEvent(event)
        pixmap = self._arrow if self.isEnabled() else self._arrow_disabled
        if pixmap is None:
            return
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, opt, QStyle.SubControl.SC_ComboBoxArrow, self
        )
        size = self.ARROW_SIZE
        target = QRect(
            rect.center().x() - size // 2 + 1, rect.center().y() - size // 2 + 1, size, size
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(target, pixmap)


class ComboBox(Widget):

    def __init__(self, tint_icons: bool = True, parent=None):
        super().__init__(parent)
        self.tint_icons = tint_icons
        self._og_icons = []

        self.master_layout = QHBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.qt_widget = _ArrowComboBox()
        self.master_layout.addWidget(self.qt_widget)
        
        self.delegate = ComboBoxItemDelegate(
            theme_manager.current(),
            self.qt_widget
        )
        self.qt_widget.view().setItemDelegate(self.delegate)
        setup_popup_list(self.qt_widget.view())

        self.item_changed = self.qt_widget.currentIndexChanged

        register_has_theme_and_apply(self)


    def get_current_idx(self) -> int:
        return self.qt_widget.currentIndex()

    def get_current_text(self) -> str:
        return self.qt_widget.currentText()

    def set_current_idx(self, idx: int):
        self.qt_widget.setCurrentIndex(idx)

    def set_current_text(self, idx: int, text: str):
        self.qt_widget.setItemText(idx, text)

    def clear_items(self):
        self.qt_widget.clear()
        self._og_icons = []

    def add_separator(self):
        """A line between two groups of items. It can't be selected, but counts as an item (index)."""
        self._og_icons.append(None)
        self.qt_widget.insertSeparator(self.qt_widget.count())

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
        arrow_icon = QIcon(":/assets/icons/ExpandSmallIcon.png")
        self.qt_widget.set_arrow_pixmaps(
            tint_icon(arrow_icon, theme.text.color_hex_argb, size=24).pixmap(24, 24),
            tint_icon(arrow_icon, theme.text.muted_hex_argb, size=24).pixmap(24, 24),
        )
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

            QComboBox:disabled {{
                background-color: {theme.surface.muted};
                border-color: {theme.border.muted};
                color: {theme.text.muted};
            }}

            QComboBox::drop-down {{
                width: 22px;
                border: none;
                background: transparent;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}

            QComboBox::down-arrow {{
                image: none;  /* painted by _ArrowComboBox, in the theme's text color */
                width: 12px;
                height: 12px;
            }}

            /* The list's look is in popup_list.py */
            QComboBox QAbstractItemView::item {{
                height: 28px;
            }}

            QLabel {{
                font-size: 13px;
            }}
        """)
