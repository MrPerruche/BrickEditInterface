from PySide6.QtWidgets import QHBoxLayout, QFileDialog
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import QTimer, QUrl

from pathlib import Path

from ui.widgets import Button, Label, StyledLabel, LabelStyle, Separator, BoolSwitch
from ui.components import Tutorial, BrickSelector
from ui.components.brick.property_set import FormulaApplyError
from ui.components.brick_filter.filters.base_filter import BaseFilter
from ui.dialogs import (
    VehicleLoadingIssueDialog, NothingEverHappensDialog, InvalidExpressionDialog, UnexpectedErrorDialog,
    ConfirmActionsDialog, NoBricksMatchDialog, CannotApplyActionDialog,
    SavePresetDialog, ReplacePresetDialog, DeletePresetDialog, PresetFileErrorDialog,
)
from ui.models import TooltipContents
from ui.rich_text import pmd
from systems.bei_files import BeiFileError
from menus import base

from menus.rule_based_editor.actions import ActionError, plural
from menus.rule_based_editor.action_list import ActionList
from menus.rule_based_editor.selection_preview import SelectionPreview
from menus.rule_based_editor.runner import ActionFailed, run_actions
from menus.rule_based_editor.presets import (
    Preset, BUILTIN_PRESETS, PRESET_FORMAT, MAX_NAME_LENGTH, MAX_DESCRIPTION_LENGTH,
    build_filters, preset_actions, preset_invert, make_preset_content, unsaved_filters, user_presets,
    check_preset_settings,
)

import brickedit

import logging
logger = logging.getLogger(__name__)


LABEL_STRETCH = 4
LONG_STRETCH = 11
PREVIEW_DELAY_MS = 150
PRESET_FILE_FALLBACK = "preset"  # File name of a preset whose name can't be one

RELOAD_SETTING = "rbe_reload_after_applying"  # Renamed: settings files froze the old default (On)

RELOAD_TOOLTIP = TooltipContents(
    "Reload after saving",
    "Reload the vehicle once the actions are applied. Like everywhere in BEI, the vehicle isn't reloaded by "
    "default: applying again without reloading starts over from the vehicle as it was loaded, and overwrites the "
    "changes you just saved."
)
PRESET_TOOLTIP = TooltipContents(
    "Use preset",
    "Replaces the conditions and actions below with this preset's. Nothing is applied until you press the apply "
    "button at the bottom."
)
INVERT_TOOLTIP = TooltipContents("Invert selection", "Select the bricks which do NOT match the conditions.")


class RuleBasedEditor(base.BaseMenu):

    def __init__(self, mw):
        super().__init__(mw)
        self.mw.settings.register(RELOAD_SETTING, False)

        self.selection: list[brickedit.Brick] = []  # Bricks matching the conditions (see refresh_selection)
        self.library = user_presets()
        self.presets: list[Preset | None] = []  # Preset of each item of the preset combo box (None: separator)
        self._preview_dirty = True

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(PREVIEW_DELAY_MS)
        self.preview_timer.timeout.connect(self.refresh_selection)


        # ----- PRESETS -----

        self.master_layout.addWidget(StyledLabel("Presets", LabelStyle.HEADER_3))

        preset_layout = QHBoxLayout()
        preset_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(preset_layout)

        self.preset_cb = BaseFilter.make_combo_box()
        self.preset_cb.item_changed.connect(self.update_preset_widgets)
        preset_layout.addWidget(self.preset_cb, stretch=LONG_STRETCH)

        self.use_preset_button = Button("Use")
        self.use_preset_button.set_tooltip(PRESET_TOOLTIP)
        self.use_preset_button.clicked.connect(self.use_preset)
        preset_layout.addWidget(self.use_preset_button)  # No stretch for this one bc theres not enough space

        self.preset_description = Label("", muted=True)
        self.master_layout.addWidget(self.preset_description)

        # Two rows: one is too wide for the window's minimum width
        manage_layout = QHBoxLayout()
        manage_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(manage_layout)
        self.save_preset_button = self._preset_button(manage_layout, "Save", "document-save", TooltipContents(
            "Save as preset", "Save the conditions and actions below as one of your presets."), self.save_preset)
        self.delete_preset_button = self._preset_button(manage_layout, "Delete", "edit-delete", TooltipContents(
            "Delete preset", "Delete the selected preset. Built-in presets can't be deleted."), self.delete_preset)

        files_layout = QHBoxLayout()
        files_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(files_layout)
        self.import_preset_button = self._preset_button(files_layout, "Import", "document-open", TooltipContents(
            "Import presets", f"Add {PRESET_FORMAT.extension} files (eg. shared by someone else) to your presets."),
            self.import_presets)
        self.export_preset_button = self._preset_button(files_layout, "Export", "document-save-as", TooltipContents(
            "Export preset", f"Save the selected preset as a {PRESET_FORMAT.extension} file, to share it."),
            self.export_preset)
        self.open_presets_folder_button = self._preset_button(files_layout, "Open folder", "folder-open",
            TooltipContents("Open presets folder", "Open the folder of your presets in your file explorer."),
            self.open_presets_folder)

        self.broken_presets_label = Label("", muted=True)  # Preset files which couldn't be loaded, and why
        self.broken_presets_label.set_font_size(11)
        self.master_layout.addWidget(self.broken_presets_label)
        self.broken_presets_label.hide()


        # ----- CONDITIONS -----

        self.master_layout.addWidget(StyledLabel("Conditions", LabelStyle.HEADER_3))

        self.brick_selector = BrickSelector(mw, [], allow_all_if_empty=False, updates_requires_reloading=False)
        self.brick_selector.filters_changed.connect(self.schedule_preview)
        self.master_layout.addWidget(self.brick_selector)

        invert_layout = QHBoxLayout()
        invert_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(invert_layout)
        invert_label = Label("Invert selection")
        invert_label.set_tooltip(INVERT_TOOLTIP)
        invert_layout.addWidget(invert_label, stretch=LABEL_STRETCH)
        self.invert_switch = BoolSwitch(False)
        self.invert_switch.on_toggled.connect(self.schedule_preview)
        invert_layout.addWidget(self.invert_switch, stretch=LONG_STRETCH)

        self.preview = SelectionPreview()
        self.master_layout.addWidget(self.preview)


        # ----- ACTIONS -----

        self.master_layout.addWidget(StyledLabel("Actions", LabelStyle.HEADER_3))

        self.action_list = ActionList(mw)
        self.action_list.changed.connect(self.update_apply_button)
        self.master_layout.addWidget(self.action_list)

        self.add_action_button = Button("Add action", QIcon.fromTheme("list-add"), tint_icon=True)
        self.add_action_button.set_tooltip(TooltipContents(
            "Add action", "Add an action, applied after the others. Drag actions by their header to reorder them."))
        self.add_action_button.clicked.connect(lambda: self.action_list.add_action())
        self.master_layout.addWidget(self.add_action_button)


        # ----- APPLY -----

        self.master_layout.addWidget(Separator())

        reload_layout = QHBoxLayout()
        reload_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.addLayout(reload_layout)
        reload_label = Label("Reload after saving")
        reload_label.set_tooltip(RELOAD_TOOLTIP)
        reload_layout.addWidget(reload_label, stretch=LABEL_STRETCH)
        self.reload_switch = BoolSwitch(bool(self.mw.settings.get(RELOAD_SETTING)))
        self.reload_switch.on_toggled.connect(lambda value: self.mw.settings.set(RELOAD_SETTING, value))
        reload_layout.addWidget(self.reload_switch, stretch=LONG_STRETCH)

        self.apply_tip_label = Label("Changes are applied directly to the vehicle. Remember you can easily undo changes in the Backup menu.")
        self.master_layout.addWidget(self.apply_tip_label)

        self.apply_button = Button("Apply")
        self.apply_button.set_tooltip(TooltipContents("Apply the actions, in order, and save the vehicle. A backup is "
                                                      "made first."))
        self.apply_button.clicked.connect(self.apply_actions)
        self.master_layout.addWidget(self.apply_button)

        self.master_layout.addStretch()

        mw.vehicle_selector_banner.vehicle_loaded.connect(self.schedule_preview)
        self.action_list.add_action()
        self.reload_presets()


    # ----- Presets

    @staticmethod
    def _preset_button(layout: QHBoxLayout, text: str, icon: str, tooltip: TooltipContents, slot) -> Button:
        button = Button(text, QIcon.fromTheme(icon), tint_icon=True)
        button.set_tooltip(tooltip)
        button.clicked.connect(slot)
        layout.addWidget(button, stretch=1)
        return button

    def current_preset(self) -> Preset | None:
        idx = self.preset_cb.get_current_idx()
        return self.presets[idx] if 0 <= idx < len(self.presets) else None

    def reload_presets(self, select: Path | None = None):
        """(Re)loads the user's presets. select: file of the preset to select (default: keep the selected one)"""
        previous = self.current_preset()
        problems = []
        try:
            entries = self.library.load_all()
        except Exception as e:  # load_all catches errors file by file: this is only a safety net
            logger.exception("Could not load the user's presets")
            entries = []
            problems.append(f"Your presets could not be loaded: {e}")
        mine = sorted((e.item for e in entries if e.item is not None), key=lambda p: p.name.casefold())
        broken = [e for e in entries if e.item is None]
        if broken:
            problems.append(f"{plural(len(broken), 'preset file')} in {self.library.folder} couldn't be loaded:")
            problems.extend(f"{entry.path.name}: {entry.error}" for entry in broken)
        self.broken_presets_label.set_text("\n".join(problems))
        self.broken_presets_label.setVisible(bool(problems))

        self.presets = list(BUILTIN_PRESETS) + ([None] + mine if mine else [])
        self.preset_cb.qt_widget.blockSignals(True)
        try:
            self.preset_cb.clear_items()
            for preset in self.presets:
                if preset is None:
                    self.preset_cb.add_separator()
                else:
                    self.preset_cb.add_item(preset.name)
            target = 0
            for i, preset in enumerate(self.presets):
                if preset is None:
                    continue
                if (select is not None and preset.path == select) or (select is None and previous is not None and (
                        preset.path == previous.path if not previous.is_builtin else preset is previous)):
                    target = i
            self.preset_cb.set_current_idx(target)
        finally:
            self.preset_cb.qt_widget.blockSignals(False)
        self.update_preset_widgets()

    def update_preset_widgets(self, *_):
        preset = self.current_preset()
        text = "" if preset is None else preset.description
        self.preset_description.set_text(text)
        self.preset_description.setVisible(bool(text))
        self.use_preset_button.set_enabled(preset is not None)
        user_preset = preset is not None and not preset.is_builtin
        self.export_preset_button.set_enabled(user_preset)
        self.delete_preset_button.set_enabled(user_preset)

    def use_preset(self):
        preset = self.current_preset()
        if preset is None:
            return
        filters: list[BaseFilter] = []
        try:
            filters = build_filters(self.mw, preset)
            self.action_list.set_actions(preset_actions(preset))  # Changes nothing if it fails
        except BeiFileError as e:
            for f in filters:
                f.deleteLater()
            PresetFileErrorDialog.create(self.mw, "Cannot Use Preset", [f"\"{preset.name}\" can't be used: {e}"]).exec()
            return
        except Exception as e:
            for f in filters:
                f.deleteLater()
            logger.exception(f"Could not use preset {preset.name}")
            UnexpectedErrorDialog.create(self.mw, f"The preset \"{preset.name}\" could not be used.", e).exec()
            return
        self.brick_selector.set_filters(filters)
        self.invert_switch.set_value(preset_invert(preset))
        self.schedule_preview()

    def save_preset(self):
        filters, actions = self.brick_selector.filters, self.action_list.actions()
        warnings = [warning for action in actions if (warning := action.config_warning())]
        if unsaved_filters(filters):
            warnings.append("Some conditions can't be saved and will be left out.")
        selected = self.current_preset()
        mine = selected is not None and not selected.is_builtin
        result = SavePresetDialog.create(self.mw, selected.name if mine else "", selected.description if mine else "",
                                         warnings, MAX_NAME_LENGTH, MAX_DESCRIPTION_LENGTH).exec()
        if not result:
            return
        name, description = result

        existing = self._user_preset_named(name)
        if existing is not None and not ReplacePresetDialog.create(self.mw, existing.name).exec():
            return
        path = existing.path if existing is not None else self.library.free_path(name, PRESET_FILE_FALLBACK)
        try:
            content = make_preset_content(name, description, self.invert_switch.get_value(), filters, actions)
            self.library.save(path, content)
        except BeiFileError as e:
            PresetFileErrorDialog.create(self.mw, "Cannot Save Preset", [str(e)]).exec()
            return
        except Exception as e:
            logger.exception("Could not save preset")
            UnexpectedErrorDialog.create(self.mw, "The preset could not be saved.", e).exec()
            return
        self.reload_presets(select=path)

    def _user_preset_named(self, name: str) -> Preset | None:
        return next((p for p in self.presets if p is not None and not p.is_builtin
                     and p.name.casefold() == name.casefold()), None)

    def import_presets(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Import Rule Presets", filter=PRESET_FORMAT.name_filter())
        if not paths:
            return
        errors, imported = [], []
        for raw_path in paths:
            source = Path(raw_path)
            try:
                preset = self.library.load(source)
                check_preset_settings(self.mw, preset)
                existing = self._user_preset_named(preset.name)
                if existing is not None and existing.path != source:
                    if not ReplacePresetDialog.create(self.mw, existing.name).exec():
                        continue
                imported.append(self.library.import_file(source, preset.name, PRESET_FILE_FALLBACK,
                                                         replace=existing.path if existing is not None else None))
            except BeiFileError as e:
                errors.append(f"{source.name}: {e}")
            except Exception as e:
                logger.exception(f"Could not import {source}")
                errors.append(f"{source.name}: unexpected error: {e}")
            self.reload_presets()  # The next file may have the same name as this one
        if imported:
            self.reload_presets(select=imported[-1])
        if errors:
            PresetFileErrorDialog.create(self.mw, "Cannot Import Presets", errors).exec()

    def export_preset(self):
        preset = self.current_preset()
        if preset is None or preset.path is None:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Export Rule Preset", str(Path.home() / preset.path.name),
                                                     PRESET_FORMAT.name_filter())
        if not destination:
            return
        destination_path = Path(destination)
        if destination_path.suffix.lower() != PRESET_FORMAT.extension:
            destination_path = destination_path.with_name(destination_path.name + PRESET_FORMAT.extension)
        try:
            self.library.export_file(preset.path, destination_path)
        except BeiFileError as e:
            PresetFileErrorDialog.create(self.mw, "Cannot Export Preset", [str(e)]).exec()

    def delete_preset(self):
        preset = self.current_preset()
        if preset is None or preset.path is None:
            return
        if not DeletePresetDialog.create(self.mw, preset.name).exec():
            return
        try:
            self.library.delete(preset.path)
        except BeiFileError as e:
            PresetFileErrorDialog.create(self.mw, "Cannot Delete Preset", [str(e)]).exec()
            return
        self.reload_presets(select=None)

    def open_presets_folder(self):
        try:
            self.library.folder.mkdir(parents=True, exist_ok=True)  # No preset saved yet
        except OSError as e:
            PresetFileErrorDialog.create(self.mw, "Cannot Open Folder", [f"{self.library.folder}: {e}"]).exec()
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.library.folder))


    # ----- Selection preview

    def schedule_preview(self, *_):
        self._preview_dirty = True
        if self.isVisible():
            self.preview_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        if self._preview_dirty:
            self.preview_timer.start()

    def refresh_selection(self):
        self._preview_dirty = False
        self.preview_timer.stop()
        banner = self.mw.vehicle_selector_banner
        data = banner.get_brvfile_ref_data()
        if not banner.is_vehicle_loaded() or data is None:
            self.selection = []
            self.preview.set_message("Load a vehicle to see which bricks match the conditions.")
        else:
            invert = self.invert_switch.get_value()
            selector = self.brick_selector
            self.selection = [brick for brick in banner.get_brvfile_ref().bricks if selector.is_allowed(brick) != invert]
            self.preview.set_selection(self.selection, data)
        self.action_list.set_selection(self.selection)
        self.update_apply_button()


    # ----- Apply

    def update_apply_button(self, *_):
        if not hasattr(self, "apply_button"):
            return
        actions = self.action_list.actions()
        count = len(self.selection)
        if len(actions) == 1:
            self.apply_button.set_text(f"{actions[0].describe(count)} and save")
        else:
            self.apply_button.set_text(f"Apply {len(actions)} actions to {plural(count)} and save")
        self.apply_button.set_enabled(self.mw.vehicle_selector_banner.is_vehicle_loaded() and (
            bool(self.selection) or not all(action.needs_selection() for action in actions)))

    def apply_actions(self):
        banner = self.mw.vehicle_selector_banner
        data = banner.get_brvfile_ref_data()
        if not banner.is_vehicle_loaded() or data is None:
            VehicleLoadingIssueDialog.create(self.mw, True).exec()
            return
        self.refresh_selection()  # Don't trust a preview which may be waiting for its timer
        actions = self.action_list.actions()
        if not self.selection and all(action.needs_selection() for action in actions):
            NoBricksMatchDialog.create(self.mw).exec()
            return

        brvfile = banner.get_brvfile_copy()  # The loaded vehicle's data describes it: same bricks, same ref ids
        logger.info(f"Applying {len(actions)} action(s) to {len(self.selection)} brick(s)")
        try:
            outcomes = run_actions(self.mw, actions, brvfile, {brick.ref.id for brick in self.selection}, data)
        except ActionFailed as e:
            where = f"Action {e.index + 1} ({e.action.get_name()})" if len(actions) > 1 else e.action.get_name()
            if isinstance(e.error, ActionError):
                CannotApplyActionDialog.create(self.mw, f"{where}: {e.error}" if len(actions) > 1 else str(e.error)).exec()
            elif isinstance(e.error, FormulaApplyError):
                InvalidExpressionDialog.create(self.mw, f"{where}: {e.error}").exec()
            else:
                logger.exception("Unexpected error while applying actions")
                UnexpectedErrorDialog.create(self.mw, f"{where} could not be applied. Nothing was saved.", e.error).exec()
            return

        lines = [outcome.describe() if len(outcomes) > 1 else outcome.summary() for outcome in outcomes]
        changed = [o for o in outcomes if o.result is not None and o.result.changed]
        if not changed:
            NothingEverHappensDialog.create(self.mw, saved=False).exec()
            return

        if any(o.action.removes_bricks() for o in changed):
            if not ConfirmActionsDialog.create(self.mw, lines).exec():
                return

        saved = banner.save_brv(brvfile, description=" ".join(lines) + f" Applied with the {self.get_menu_name()}.")
        if not saved:
            return
        logger.info("Actions applied: " + " ".join(lines))

        if self.reload_switch.get_value():
            banner.load_vehicle(banner.get_vehicle_loc())


    # ----- Menu

    def get_menu_name(self) -> str:
        """Return the display name of this menu."""
        # NOTE: TUTORIAL USE A DIFFERENT NAME. IF MENU NAME MUST BE CHANGED, UPDATE TUTORIAL MANUALLY!
        return "Rule Based Editor"

    def _make_menu_info(self) -> base.MenuInfo:
        """Return the icon for this menu."""
        return base.MenuInfo(QIcon(":/assets/icons/RuleBasedEditor.png"), True,
            tutorial=Tutorial("R.B. Editor", self.mw)  # Name too long for tutorials
                .add_text("The rule based editor edits every brick matching a set of conditions at once: "
                          "conditions select bricks (which bricks?), then actions are applied to them (what to "
                          "do with them?).")
                .add_text("It can find and fix duplicated bricks and mirroring mistakes, select bricks with "
                          "custom formulas, and delete, paint, edit, group, transform, mirror or copy them, or "
                          "change their type.")
                .add_header("Getting started")
                .add_steps(
                    "Save your vehicle in Brick Rigs, then load (or reload) it in BrickEdit-Interface.",
                    "Pick a preset and press \"Use\", or add conditions and actions yourself. A preset only fills "
                        "the menu in: nothing is applied yet.",
                    "Check the selection: how many bricks match, of which types, and (with \"Show bricks\") "
                        "where they are. Adjust the conditions until only the right bricks are selected.",
                    "Check the actions and their settings.",
                    "Press the apply button. The vehicle is saved, after making a backup.",
                    "Re-open your vehicle in Brick Rigs to see the changes. Reload it in BEI before applying "
                        "again, or enable \"Reload after saving\".",
                )
                .add_header("Presets")
                .add_text("Presets fill the conditions and actions in for common tasks. Save your own setups "
                          "with \"Save\", and share them as files with \"Export\" and \"Import\".")
                .add_text(pmd(f"Your presets are `{PRESET_FORMAT.extension}` files, stored in "
                              f"BrickEdit-Interface's settings folder (\"Open folder\" opens it). Every setting is "
                              "saved, including the edits of \"Edit properties\": they're applied to the bricks the "
                              "preset selects, formulas for each brick."))
                .add_header("Conditions")
                .add_text("Conditions work like the brick editor's filters: a brick is selected if it matches "
                          "the conditions. When there is no condition, no brick is selected. \"Invert selection\" "
                          "selects every brick which doesn't match instead.")
                .refer_to("getting_started_filters")
                .add_text("Unlike in the brick editor, the selection updates live: there's no need to reload "
                          "the vehicle after editing conditions.")
                .add_low_header("Duplicates")
                .add_text("Bricks are duplicates when they have the same type, position and orientation, and "
                          "(depending on the comparison) the same properties. Among duplicates, the first brick is "
                          "the one which comes first in the vehicle. \"a copy\" selects all but the first, "
                          "\"duplicated\" selects all of them, and \"a copy past the Nth\" keeps N of them.")
                .add_low_header("Mirror status")
                .add_text("Every brick is paired with the brick of the same type (or its left / right version, "
                          "eg. for wings and doors) at its mirrored position. Brick Rigs vehicles are usually "
                          "symmetric along the Y axis, with the mirror plane at 0. A pair is perfectly mirrored if "
                          "both bricks are rotated like mirror images and share the same color and properties. "
                          "Some properties are expected to change, like Brick Rigs does when mirroring: eg. a "
                          "spinner's angle is inverted.")
                .add_text("By default, only exact mirror images count, like in Brick Rigs: a counterpart may be "
                          "off by 0.0001 cm and 0.01° at most. For a vehicle built by hand, increase the position "
                          "and angle tolerances (eg. 0.1 cm and 1°), and allow turned symmetric bricks.")
                .add_text("\"Side\" restricts the condition to one side of the mirror plane, eg. to delete the "
                          "bricks missing a counterpart on one side only.")
                .add_low_header("Property values and formulas")
                .add_text("\"Property must be\" compares a property to a value, or checks it's within a range.")
                .add_text(pmd("\"Satisfy condition\" selects bricks for which a formula is true, eg. "
                              "`y > 0 and sz <= 10`. Hover the condition to see every variable available."))
                .refer_to("getting_started_expressions")
                .add_header("Actions")
                .add_text("Actions are applied from top to bottom, then the vehicle is saved once. Drag an action "
                          "by its header to move it.")
                .add_text("Each action applies to the selected bricks, except after an action which creates or "
                          "deletes bricks: after \"Copy\" and \"Mirror\", the next actions apply to the new bricks "
                          "only, and nothing is left after \"Delete\". Order matters: copying then painting paints "
                          "the copies only, painting then copying paints both.")
                .add_text(pmd("\"Select\" changes which bricks the next actions apply to with a formula, like "
                              "\"Satisfy condition\": among the selected bricks (eg. only the copies with "
                              "`z > 100`), or in the whole vehicle, to apply several rules at once."))
                .add_collection("Actions",
                    ("Delete", "Removes the selected bricks. Wires from other bricks to them are removed too."),
                    ("Edit properties", "Edits the position, rotation and properties of every selected brick at "
                        "once, with formulas, like the brick editor."),
                    ("Paint", "Sets the color (and optionally the material) of the selected bricks. Handy to "
                        "find them in Brick Rigs before deciding what to do with them."),
                    ("Set group", "Moves the selected bricks to a named group, a new group, or out of their group."),
                    ("Transform", "Rotates, scales and moves the selected bricks as a whole, about the center of "
                        "the selection or a point, or each brick in place. Scaling also scales sizes (brick size, "
                        "wheel diameter...)."),
                    ("Change type", "Turns the selected bricks into bricks of another type. They keep their "
                        "position, rotation, groups, wires, and the properties both types have. Type part of the "
                        "type's internal name to list the matching types; any name works, modded bricks included."),
                    ("Mirror", "Creates a mirror image of the selected bricks. Bricks which already have a "
                        "counterpart can be skipped, replaced, or mirrored anyway. Wires are mirrored too."),
                    ("Copy", "Copies the selected bricks one or more times, each copy moved by an offset."),
                    ("Select", "Changes which bricks the next actions apply to, with a formula."),
                )
                .add_warning("Detecting duplicates and mirror issues relies on heuristics: always check the "
                             "selection before applying. Every save makes a backup, which you can recover in the "
                             "backup manager.")
                .add_sep()
                .add_faq(
                    "<b>Why aren't my bricks seen as mirrored?</b><br>"
                        "By default, only exact mirror images count, like in Brick Rigs. Bricks placed by hand are "
                        "often slightly off: try larger tolerances (eg. 0.1 cm and 1°) and allow turned symmetric "
                        "bricks. The mirror plane may also not be at 0, or the bricks may be of different types.",
                    "<b>A mirrored brick is rotated the wrong way</b><br>"
                        "BEI mirrors bricks with the rules Brick Rigs uses, extracted from the game's data. If a "
                        "brick is mirrored differently than in Brick Rigs, please report it on the BrickEdit "
                        "discord.",
                    "<b>Why is the apply button disabled?</b><br>"
                        "No brick is selected: load a vehicle and add conditions matching at least one brick.",
                    "<b>I applied twice and the first changes disappeared</b><br>"
                        "Applying saves the vehicle as it was loaded, edited by the actions. Reload the vehicle "
                        "between two runs, or enable \"Reload after saving\".",
                    "<b>A preset can't be loaded</b><br>"
                        "It may have been made with a newer version of BrickEdit-Interface, or the file may be "
                        "damaged. The reason is shown under the preset buttons.",
                )
        )
