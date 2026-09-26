from PySide6.QtWidgets import QLayout, QVBoxLayout, QScrollArea, QDialog, QSizePolicy, QWidget
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QIcon

from ui.widgets import Widget, Separator, Label, StyledLabel, LabelStyle, Switcher, SurfaceSwitcher, SwitcherEntry, Button
from ui.theme import Theme, style_rules

import logging
logger = logging.getLogger(__name__)


_LINK_ICON_NAMES = ("go-jump", "go-next")


def _link_icon() -> QIcon | None:
    for name in _LINK_ICON_NAMES:
        icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    return None


# id -> (owning tutorial, anchor widget, label shown on buttons pointing to it)
_link_targets: dict[str, tuple['Tutorial', QWidget, str]] = {}
# id -> (button, whether the button has its own label) for every refer_to() whose target is not registered (yet)
_pending_links: dict[str, list[tuple[Button, bool]]] = {}


def open_tutorial_target(target_id: str):
    """Opens the tutorial owning target_id and scrolls to it"""
    entry = _link_targets.get(target_id)
    if entry is None:
        logger.warning(f"Tutorial link target '{target_id}' does not exist")
        return
    tutorial, anchor, _ = entry
    tutorial.summon()
    tutorial.raise_()
    tutorial.activateWindow()
    tutorial.scroll_to(anchor)


def check_tutorial_links():
    """Logs every link pointing to a target which does not exist. Call once every tutorial is built."""
    for target_id, buttons in _pending_links.items():
        if buttons:
            logger.warning(f"Tutorial link '{target_id}' is used {len(buttons)} time(s) but has no target")


@style_rules
def _tutorial_rules(theme: Theme) -> str:
    return f"""
        Tutorial {{
            background-color: {theme.background.color};
        }}

        QScrollArea[tutorialScroll] {{
            background-color: {theme.background.color};
            border: none;
        }}

        QWidget[tutorialContent] {{
            background-color: {theme.background.color};
        }}

        QWidget[tutorialWarning] {{
            border-bottom: 2px solid {theme.border.color};
        }}"""


class Tutorial(QDialog):

    def __init__(self, title: str | None, parent=None, title_is_raw: bool = False, show_header: bool = True, standalone: bool = True, use_scroll_area: bool = True):
        super().__init__(parent)

        # Give it a normal window with its own taskbar button,
        # while still being a child (closes with parent).
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )

        self.finalized = False
        self._owns_link_targets = standalone
        self._last_widget: QWidget | None = None  # Anchor of refer_target()

        # SETUP
        self.content = QDialog()  # plain container widget
        self.content.setProperty("tutorialContent", True)
        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(10, 10, 10, 10)
        self.content.setLayout(self.master_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setProperty("tutorialScroll", True)
        self.scroll_area.setWidgetResizable(True)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer_layout)

        if use_scroll_area:
            outer_layout.addWidget(self.scroll_area)
            self.scroll_area.setWidget(self.content)
        else:
            outer_layout.addWidget(self.content)

        # WARNING
        self.warning_label = Label("IF YOU ARE UNFAMILIAR WITH BEI,\nPLEASE READ INFORMATION PROVIDED IN THE WELCOME MENU FIRST!")
        self.warning_label.set_font_weight(800)
        self.warning_label.set_muted(True)
        self.warning_label.setProperty("tutorialWarning", True)
        self.warning_label.setContentsMargins(0, 0, 0, 5)
        self.warning_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )
        self.master_layout.addWidget(self.warning_label)
        self.warning_label.setVisible(show_header)

        # TITLE
        title_text = title if title_is_raw else f"Tutorial: {title}"
        if title is not None:
            self.add_text(title_text, LabelStyle.LARGE_2)

        if standalone:
            self.setWindowTitle(title_text)
            self.setMinimumSize(300, 200)
            self.resize(325, 650)



    def add_widget(self, widget: Widget):
        self.master_layout.addWidget(widget)
        self._last_widget = widget
        return self

    def refer_target(self, target_id: str, label: str):
        """Makes the widget added right before a destination of refer_to(target_id) in any tutorial.
        label is what those buttons show."""
        if not self._owns_link_targets:
            return self  # Embedded copy of a tutorial: the standalone one owns the ids
        if target_id in _link_targets:
            logger.warning(f"Tutorial link target '{target_id}' is declared more than once, keeping the first")
            return self

        anchor = self._last_widget if self._last_widget is not None else self.content
        _link_targets[target_id] = (self, anchor, label)

        # Resolve the buttons which were created before this target
        for button, has_own_label in _pending_links.pop(target_id, []):
            if not has_own_label:
                button.set_text(label)
            button.set_enabled(True)
        return self

    def refer_to(self, target_id: str, label: str | None = None):
        """Adds a button opening the tutorial declaring refer_target(target_id, ...) at that spot.
        Its text is the target's label unless label is given."""
        entry = _link_targets.get(target_id)
        text = label if label is not None else (entry[2] if entry is not None else target_id)

        icon = _link_icon()
        button = Button(text, icon, True) if icon is not None else Button(text)
        button.clicked.connect(lambda: open_tutorial_target(target_id))
        if entry is None:
            button.set_enabled(False)  # Until the target exists
            _pending_links.setdefault(target_id, []).append((button, label is not None))
        return self.add_widget(button)

    def scroll_to(self, widget: QWidget):
        """Scrolls so widget is at the top. Deferred: the layout of a tutorial which was just shown is not final yet."""
        def _scroll():
            self.content.layout().activate()
            y = widget.mapTo(self.content, QPoint(0, 0)).y()
            bar = self.scroll_area.verticalScrollBar()
            bar.setValue(max(0, y - self.master_layout.contentsMargins().top()))
        QTimer.singleShot(0, _scroll)

    def add_layout(self, layout: QLayout):
        self.master_layout.addLayout(layout)
        return self


    def add_sep(self, top=9, bottom=9):
        return self.add_widget(Separator(top, bottom))


    def add_text(self, text: str, style: LabelStyle | None = None):
        if style is None:
            return self.add_widget(Label(text))
        else:
            return self.add_widget(StyledLabel(text, style))

    def add_title(self, text: str, nomargin: bool = False):
        return self.add_text(text, style=LabelStyle.LARGE_2 if nomargin else LabelStyle.HEADER_2)

    def add_header(self, text: str, nomargin: bool = False):
        return self.add_text(text, style=LabelStyle.LARGE_4 if nomargin else LabelStyle.HEADER_4)

    def add_low_header(self, text: str, nomargin: bool = False):
        return self.add_text(text, style=LabelStyle.LARGE_5 if nomargin else LabelStyle.HEADER_5)

    def add_subtext(self, text: str):
        return self.add_text(text, style=LabelStyle.SUBTEXT_1)


    def _get_collection_entries(self, *args: str | tuple[str, str] | SwitcherEntry) -> list[SwitcherEntry]:

        arg_count = len(args)
        entries = []

        for i, arg in enumerate(args):

            if isinstance(arg, SwitcherEntry):
                entries.append(arg)
                continue

            elif isinstance(arg, tuple):
                name, contents = arg
            else:  # str
                name, contents = f"{i+1} / {arg_count}", arg

            entry_layout = QVBoxLayout()
            entry_layout.setContentsMargins(0, 0, 0, 0)
            entry_layout.addWidget(Label(contents))
            entries.append(SwitcherEntry(name, layout=entry_layout))

        return entries


    def add_switcher(self, *args: str | tuple[str, str] | SwitcherEntry):
        entries = self._get_collection_entries(*args)
        return self.add_widget(Switcher(entries))


    def add_collection(self, title: str, *args: str | tuple[str, str]):
        return self.add_widget(SurfaceSwitcher(title, self._get_collection_entries(*args)))


    def add_tips(self, *args: str | tuple[str, str]):
        return self.add_collection("Tips", *args)

    def add_raw_faq(self, *args: str | tuple[str, str]):
        return self.add_collection("FAQ", *args)

    def add_faq(self, *args: str | tuple[str, str]):
        return self.add_collection("FAQ & Help", *args)

    def add_help(self, *args: str | tuple[str, str]):
        return self.add_collection("Help", *args)

    def add_steps(self, *args: str | tuple[str, str]):
        return self.add_collection("Steps", *args)


    def set_inner_margins(self, left: int, top: int, right: int, bottom: int):
        self.master_layout.setContentsMargins(left, top, right, bottom)
        return self

    def summon(self):
        """Show the widget in a new window
        Never summon a non finalized widget"""
        if not self.finalized:
            self.finalized = True
            self.master_layout.addStretch(1)

        self.show()
