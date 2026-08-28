from PySide6.QtWidgets import QLayout, QVBoxLayout, QScrollArea, QDialog
from PySide6.QtCore import Qt

from ui.widgets import Widget, Label, StyledLabel, LabelStyle, Switcher, SurfaceSwitcher, SwitcherEntry
from ui.theme import register_has_theme_and_apply, Theme


class Tutorial(QDialog):

    def __init__(self, title: str | None, parent=None, title_is_raw: bool = False):
        super().__init__(parent)

        # Give it a normal window with its own taskbar button,
        # while still being a child (closes with parent).
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )

        self.finalized = False

        content = QDialog()  # plain container widget
        content.setProperty("tutorialContent", True)
        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(12, 0, 12, 12)
        content.setLayout(self.master_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setProperty("tutorialScroll", True)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(content)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.scroll_area)
        self.setLayout(outer_layout)

        title_text = title if title_is_raw else f"Tutorial: {title}"
        self.setWindowTitle(title_text)
        if title is not None:
            self.add_title(title_text)

        self.setMinimumSize(300, 200)
        self.resize(300, 500)
        register_has_theme_and_apply(self)



    def add_widget(self, widget: Widget):
        self.master_layout.addWidget(widget)
        return self

    def add_layout(self, layout: QLayout):
        self.master_layout.addLayout(layout)
        return self


    def add_text(self, text: str, style: LabelStyle | None = None):
        if style is None:
            return self.add_widget(Label(text))
        else:
            return self.add_widget(StyledLabel(text, style))

    def add_title(self, text: str):
        return self.add_text(text, style=LabelStyle.HEADER_2)

    def add_header(self, text: str):
        return self.add_text(text, style=LabelStyle.HEADER_4)

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



    def summon(self):
        """Show the widget in a new window
        Never summon a non finalized widget"""
        if not self.finalized:
            self.finalized = True
            self.master_layout.addStretch(1)

        self.show()

    def _apply_theme(self, theme: Theme):
        self.setStyleSheet(f"""
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
        """)
