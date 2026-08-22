from PySide6.QtWidgets import QDialog, QTextEdit
from PySide6.QtCore import QFile, QTextStream, QUrl
from PySide6.QtGui import QIcon, QDesktopServices

from menus import base
from ..shared_widgets import *

from utils import VERSION, DEV_VERSION
from ui.widgets import Label, StyledLabel, LabelStyle, Button, Switcher
from ui.theme import theme_manager


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("License")
        self.resize(600, 400)

        # Load the license text from the embedded resource
        file = QFile(":/LICENSE")
        if not file.open(QFile.ReadOnly | QFile.Text):
            license_text = "Failed to load license. Please warn the developers as soon as possible."
        else:
            stream = QTextStream(file)
            license_text = stream.readAll()
            file.close()

        # Show it in a read-only text edit
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setPlainText(license_text)

        layout = QVBoxLayout()
        layout.addWidget(text_area)
        self.setLayout(layout)


class HomeMenu(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw, header=False)

        self.text_and_logo_layout = QHBoxLayout()
        self.master_layout.addLayout(self.text_and_logo_layout)

        self._logo_pixmap = QPixmap(':/assets/icons/brickeditinterface.png')

        LOGO_SIZE = 112

        self.brickeditinterface_label = QLabel()
        self.brickeditinterface_label.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self.brickeditinterface_label.setPixmap(
            self._logo_pixmap.scaled(
                LOGO_SIZE, LOGO_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )
        self.brickeditinterface_label.setAlignment(Qt.AlignLeft)
        # self.brickeditinterface_label.setScaledContents(False)
        self.text_and_logo_layout.addWidget(self.brickeditinterface_label)

        # --- TITLE + VERSION BLOCK ---------------------------------

        title_text = "BrickEdit-Interface"
        version_text = f"{'Dev ' if DEV_VERSION else ''}Version {VERSION}"


        self.bei_text_label = Label(title_text, 16, 900)
        self.bei_text_label.set_italic(True)
        self.bei_text_label.qt_widget.setAlignment(Qt.AlignRight)

        version_label = Label(version_text, 10, muted=True)
        version_label.qt_widget.setAlignment(Qt.AlignRight)

        # Layout that holds title + version
        title_block_layout = QVBoxLayout()
        title_block_layout.addStretch()
        title_block_layout.addWidget(self.bei_text_label)
        title_block_layout.addWidget(version_label)
        title_block_layout.addStretch()

        # Theme
        self.theme_switcher = Switcher([theme.display_name for theme in theme_manager.themes], theme_manager.current_idx(), looping=True)
        self.theme_switcher.index_changed.connect(self.update_theme)
        self.master_layout.addWidget(self.theme_switcher)


        # Center the whole block in the window
        title_block_container = QWidget()
        self.text_and_logo_layout.addLayout(title_block_layout)

        self.master_layout.addWidget(title_block_container, alignment=Qt.AlignCenter)


        text = """\
#Welcome!
---
BrickEdit-Interface is a set of tools made using BrickEdit 5 to help builders and get over the limitations of Brick Rigs.

---
#License:
---
This software is under the GNU GENERAL PUBLIC LICENSE Version 3.
https://www.gnu.org/licenses/gpl-3.0.en.html
The source code is available at:
https://github.com/MrPerruche/BrickEditInterface
---
licensebtn
---

---
# Links:
---
linkbtn_discord
---
linkbtn_github
---

#Frequently asked questions:
---
→ 1. Will BrickEdit-Interface ever feature an obj-importer?
We do not currently plan to add an obj-importer. Our decision may change if the overall community's opinion shifts.
---
→ 2. Is BrickEdit-Interface safe to use?
Yes! We actively fix bugs as soon as possible, and our backup system runs automatically.
---
→ 3. Will you add X? Will you ever do Y?
We would love to add more features to our software. We are looking for suggestions and feedback, so feel free to share them in our Discord!

---
#Tips:
---
→ 1. Most features will require you to specify which vehicle you want to modify. In-game, you can select a vehicle and click "Open in file explorer" to see which file you must select.
If you remember the numbers at the end of the file path, when selecting, you can input these numbers and press Enter twice. This is much faster than searching through the list.
---
→ 2. Don't be afraid to experiment! BrickEdit-Interface automatically backs up every time it does something. You can easily recover them in the backup manager.
Our backup system lets you adjust both how many and how large the backups of a vehicle may grow. We create both "short-term" and "long-term" backups so you can recover from your immediate and previous mistakes.
---
→ 3. Most if not all number inputs allow you to input mathematical expressions, which will be evaluated once you are done writing.
"""

        self.welcome_labels = []
        for welcome_label_text in text.split('\n---\n'):

            match welcome_label_text.strip():
                case 'linkbtn_github':
                    self.github_button = Button("Github (download updates in releases)")
                    self.github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/MrPerruche/BrickEditInterface")))
                    self.master_layout.addWidget(self.github_button)
                    continue
                case 'linkbtn_discord':
                    self.discord_button = Button("Discord (chat, get notifications and support)")
                    self.discord_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/P9wcknqQVB")))
                    self.master_layout.addWidget(self.discord_button)
                    continue
                case 'licensebtn':
                    self.license_button = Button("Show license offline")
                    self.license_button.clicked.connect(self.show_license)
                    self.master_layout.addWidget(self.license_button)
                    continue

            if welcome_label_text.strip().startswith('#'):
                welcome_label_text = welcome_label_text.replace('#', '')
                welcome_label = StyledLabel(welcome_label_text, LabelStyle.HEADER_5)
            else:
                welcome_label = Label(welcome_label_text)
            self.welcome_labels.append(welcome_label)
            self.master_layout.addWidget(welcome_label)


        self.master_layout.addStretch()


    def update_theme(self):
        theme_manager.set_theme(theme_manager.themes[self.theme_switcher.get_idx()])


    def get_menu_name(self):
        return "Welcome"

    def get_icon(self) -> base.MenuIconInfo:
        return base.MenuIconInfo(QIcon(':/assets/icons/brickeditinterface.ico'), False)

    def show_license(self):
        license_window = LicenseDialog()
        license_window.exec()
