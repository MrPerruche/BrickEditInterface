"""Look shared by the lists popping up under a widget (ComboBox's, SuggestionLineEdit's), so they all match"""

from PySide6.QtWidgets import QAbstractItemView, QStyle, QStyleOption
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QObject, QEvent

from ui.theme import Theme, style_rules


SCROLL_BAR_WIDTH = 10


@style_rules
def _popup_list_rules(theme: Theme) -> str:
    view = 'QAbstractItemView[beiPopupList="true"]'
    return f"""
        {view} {{
            background-color: {theme.background.color};
            border: 2px solid {theme.border.color};
            border-radius: 4px;
            outline: none;
            font-size: 13pt;  /* Like the combo boxes and line edits they pop up from */
        }}
        {view} QScrollBar:vertical {{
            background: transparent;
            width: {SCROLL_BAR_WIDTH}px;
            margin: 0px;
        }}
        {view} QScrollBar::handle:vertical {{
            background-color: {theme.border.color};
            border-radius: 3px;
            min-height: 24px;
            margin: 2px 2px 2px 2px;
        }}
        {view} QScrollBar::handle:vertical:hover, {view} QScrollBar::handle:vertical:pressed {{
            background-color: {theme.text.muted};
        }}
        {view} QScrollBar::add-line:vertical, {view} QScrollBar::sub-line:vertical {{
            height: 0px;
            border: none;
            background: none;
        }}
        {view} QScrollBar::add-page:vertical, {view} QScrollBar::sub-page:vertical {{
            background: none;
        }}"""


class _StyledBackgroundPainter(QObject):
    """Paints the stylesheet background and border of a translucent window, which Qt skips (translucent implies
    WA_NoSystemBackground). Its corners, outside the rounded border, stay transparent."""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Paint:
            option = QStyleOption()
            option.initFrom(watched)
            painter = QPainter(watched)
            watched.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, watched)
            painter.end()
        return False  # Then painted as usual, over it


def setup_popup_list(view: QAbstractItemView):
    """Gives a popup list (and its window: the view itself, or the combo box's container around it) the app's look:
    themed 2px border and scroll bar instead of the system's frame and shadow. Before it's first shown."""
    view.setProperty("beiPopupList", True)  # Selected by _popup_list_rules
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Too long items are elided instead

    window = view.window()
    # Windows 11 gives popups a rounded 1px frame and a shadow, drawn over the border
    window.setWindowFlags(window.windowFlags() | Qt.WindowType.FramelessWindowHint
                          | Qt.WindowType.NoDropShadowWindowHint)
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Rounded corners: the window's corners are seen
    if window is view:  # eg. a QCompleter's list. A combo box's is in a container, which paints nothing itself
        view.installEventFilter(_StyledBackgroundPainter(view))
