from PySide6.QtGui import QIcon

from menus import base

from ui.dialogs import VehicleLoadingIssueDialog
from ui.widgets import Button
from ui.components import BrickSelector, VehicleBricksEditor, Tutorial

from brickedit import *

import logging
logger = logging.getLogger(__name__)



class EditBrickMenu(base.BaseMenu):
    """Menu for editing brick properties."""

    def __init__(self, mw):
        super().__init__(mw)

        # self.color_selector = ColorWidget(lambda: self.vehicle_selector.brv)
        # self.master_layout.addWidget(self.color_selector)

        # self.bricks_widget = BrickListWidget([])
        # self.master_layout.addWidget(self.bricks_widget)

        self.brick_selector = BrickSelector(mw)
        self.master_layout.addWidget(self.brick_selector)

        self.vbe = VehicleBricksEditor(mw, self.brick_selector)
        self.master_layout.addWidget(self.vbe)

        self.save_button = Button("Save changes")
        self.save_button.clicked.connect(self.save_changes)
        self.master_layout.addWidget(self.save_button)

        self.master_layout.addStretch()

    def get_menu_name(self) -> str:
        return "Brick Editor"

    def _make_menu_info(self) -> base.MenuInfo:
        return base.MenuInfo(QIcon(":/assets/icons/BrickEditorIcon.png"), True,

            tutorial=Tutorial(self.get_menu_name(), self.mw)
                .add_text("The brick editor allows you to modify the properties of a vehicle's "
                          "bricks. Its purpose is to bypass Brick Rigs' limits and edit many "
                          "bricks' properties at once using formulas.")
                .add_header("Getting started")
                .add_text("Steps in order to make a basic edit on a single brick:")
                .add_steps(
                    "First, save your vehicle in Brick Rigs.",
                    "Filter out all bricks you don't want to edit (or at least, narrow the list). "
                        "If a brick respects all conditions of a filter, it is selected.\n"
                        "By default, every brick set to a given color is selected. You can "
                        "customize, add and remove conditions to a filter if you wish. Learn more "
                        "about filters below.",
                    "Load (or reload if already loaded) your vehicle in BrickEdit-Interface.",
                    "Edit properties of the selected bricks any way you want. If a property is "
                        "missing, it's likely editing it is not supported by BEI.\n"
                        "If you are confused by the property editor, it may be because you are "
                        "editing multiple bricks at a time. make sure \"split selection by "
                        "(...)\" is set to \"individual bricks\". Learn more about this setting "
                        "below.",
                    "Save changes in BrickEdit-Interface and re-open your vehicle in Brick Rigs.",
                    "If you wish to edit your vehicle again, go back to step 3 if you'd like to "
                        "keep changes you've just made.\n"
                        "Otherwise, go back to step 4 in order to re-edit what you just edited."
                )
                .add_header("Selecting bricks (filters)")
                .add_text(
                    "You can select which bricks you want to edit using filters. Filters are a "
                    "list of conditions which must be met in order for a brick to be selected. "
                    "Conditions have multiple modes to edit their behavior: whether it's "
                    "mandatory or just preferred, some can override other conditions, etc. In "
                    "this menu, no bricks are selected when there are no conditions.")
                .add_text("Learn more about filters in the Welcome menu.")

                .add_header("Bulk editing (splitting selection)")
                .add_text(
                    "BEI lets you to change how the list of bricks you selected are split. "
                    "This powerful feature allows you to edit multiple bricks at once using "
                    "mathematical formulas.")
                .add_text(
                    "Your brick selection can be split into many parts. By default, it splits "
                    "every brick. Every set of bricks it outputs has its own page. In this page, "
                    "you can change the properties of all concerned bricks simultaenously.")
                .add_text(
                    "If multiple bricks in a page have a different value for a single property, "
                    "you may use mathematical formulas to edit this property. (Note you can still "
                    "input constants if you want to set all concerned bricks to a single value).")
                .add_text(
                    "WARNING: BEI will only apply changes from the currently displayed page. "
                    "Changes made in other pages (or even with different splitting methods "
                    "selected) are not discarded but aren't applied either.")

                .add_sep()

                .add_faq(
                    "<b>Can't see a property you expected?</b><br>"
                        "A property may not appear for 3 reasons:<br>"
                        "1. Bricks holding this property are excluded by filters or in another "
                        "page (ie. you're doing things wrong);<br>"
                        "2. It is the property of a modded brick and is currently set to its "
                        "default value ;<br>"
                        "3. This property is vanilla and not supported by BrickEdit-Interface.",
                    "<b>Why are some properties not supported?</b><br>"
                        "Some properties aren't supported because they cannot be hex-edited past "
                        "the limits Brick Rigs sets (such as connector spacings), and we didn't "
                        "see any use for bulk editing them.<br>"
                        "Feel free to request their addition and we will look to add support in "
                        "the next update.",
                    "<b>Why are some modded properties so complicated to edit?</b><br>"
                        "Brick Rigs' file format does not give us any information about a "
                        "property's type.<br>"
                        "However, we are looking to make editing modded bricks easier! If any mod "
                        "adds new properties and we do not currently support them, please notify "
                        "us. We will look to add extended support for this mod."
                )
        )

    def save_changes(self):
        if not self.main_window.vehicle_selector_banner.is_vehicle_loaded():
            VehicleLoadingIssueDialog.create(self.mw, True).exec()
            return
        logger.info("Saving changes in Brick Editor...")
        self.vbe.build_modified_brvfile(True, {'description': f"Modified using the {self.get_menu_name()}."})
        logger.info("Saving changes in Brick Editor complete")
