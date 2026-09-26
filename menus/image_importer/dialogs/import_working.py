from PySide6.QtCore import Signal, QTimer

from ui.dialogs.base import Dialog
from ui.widgets import Button

from menus.image_importer.dialogs.import_progress import ImportProgressLine

from time import perf_counter


CONTENT_MIN_WIDTH = 400


class ImportWorkingDialog(Dialog):
    """Shown while the image is being prepared / merged in the background: current step, color progress
    (while merging), time elapsed and a Cancel button."""

    cancelled = Signal()

    def __init__(self, mw):
        super().__init__(mw=mw, icon=None, title="Importing Image")

        self._resolved = False
        # On the content, not qt_dialog: the base layout's SetMinimumSize constraint overrides the dialog's own minimum
        self._content.setMinimumWidth(CONTENT_MIN_WIDTH)
        self.qt_dialog.finished.connect(self._on_qt_dialog_closed)

        self.step_widget = ImportProgressLine("Step", "Starting...", "")
        self._add_content(self.step_widget)

        self.colors_widget = ImportProgressLine("Colors merged", "-", "")
        self._add_content(self.colors_widget)

        self.time_widget = ImportProgressLine("Time elapsed", "00:00", "")
        self._add_content(self.time_widget)

        self.cancel_button = Button("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self._add_action(self.cancel_button, auto_close=False)

        self.create_time = perf_counter()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time_elapsed)
        self.timer.start(500)


    def set_stage(self, text: str):
        self.step_widget.update_contents(None, text, None)
        self.colors_widget.update_contents(None, "-", "")

    def set_color_progress(self, done: int, total: int):
        self.colors_widget.update_contents(None, f"{done:,}", f"/ {total:,}")

    def finish(self):
        """Close because the work is over (does not emit `cancelled`)."""
        self._resolved = True
        self.close()

    def _on_cancel_clicked(self):
        if self._resolved:
            return
        self._resolved = True
        self.cancelled.emit()
        self.close()

    def _on_qt_dialog_closed(self, *_qt_result_code):
        self.timer.stop()
        if not self._resolved:  # closed with the window's X
            self._resolved = True
            self.cancelled.emit()

    def _update_time_elapsed(self):
        mins, secs = divmod(int(perf_counter() - self.create_time), 60)
        self.time_widget.update_contents(None, f"{mins:02d}:{secs:02d}", None)
