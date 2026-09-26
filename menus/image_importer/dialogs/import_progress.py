from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtCore import Signal, Qt, QTimer

from ui.dialogs.base import Dialog
from ui.widgets import Widget, Label, StyledLabel, LabelStyle, Button

from collections import deque
from time import perf_counter


FONT_WEIGHT = 850
CONTENT_MIN_WIDTH = 400
POST_WIDTH = 120  # fits the longest post text (eg. "(12,345 / SEC)") without wrapping


class ImportProgressLine(Widget):

    def __init__(self, title: str, value: str, post: str):
        super().__init__()

        self.master_layout = QHBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.master_layout)

        self.title_widget = Label("title")
        self.master_layout.addWidget(self.title_widget)

        self.master_layout.addStretch(1)

        self.value_widget = Label("value", font_weight=FONT_WEIGHT)
        self.value_widget.set_alignment(Qt.AlignRight)
        self.master_layout.addWidget(self.value_widget)

        self.post_widget = StyledLabel("post", LabelStyle.SUBTEXT_1)
        self.post_widget.setMinimumWidth(POST_WIDTH)
        self.master_layout.addWidget(self.post_widget)


        self.update_contents(title, value, post)


    @staticmethod
    def _set_text_no_wrap(label: Label, text: str):
        """Sets the text and makes sure the label is never narrower than it (only ever grows, so a changing
        value doesn't make the row jitter). Word wrap stays on: TextOverflow.NONE would let the label collapse."""
        label.set_text(text)
        needed = label.qt_widget.fontMetrics().horizontalAdvance(text) + 6
        if needed > label.minimumWidth():
            label.setMinimumWidth(needed)

    def update_contents(self, title: str | None, value: str | None, post: str | None):
        if title is not None:
            self._set_text_no_wrap(self.title_widget, title)
        if value is not None:
            self._set_text_no_wrap(self.value_widget, value)
        if post is not None:
            self._set_text_no_wrap(self.post_widget, post)



class ImportProgressDialog(Dialog):

    finished = Signal()
    cancelled = Signal()

    def __init__(self, mw, max_layer_count: int, decompose_worker):
        super().__init__(mw=mw, icon=None, title="Importing Image")

        self.max_layer_count = max_layer_count
        self.decompose_worker = decompose_worker

        self._resolved = False

        # On the content, not qt_dialog: the base layout's SetMinimumSize constraint overrides the dialog's own minimum
        self._content.setMinimumWidth(CONTENT_MIN_WIDTH)
        self.qt_dialog.finished.connect(self._on_qt_dialog_closed)

        # Brick count
        self.bc_widget = ImportProgressLine("Brick count", "-", "/ 50,000 MAX")
        self._add_content(self.bc_widget)

        self.lay_widget = ImportProgressLine("Layers", "-", f"/ {max_layer_count} ALLOWED")
        self._add_content(self.lay_widget)

        self.att_widget = ImportProgressLine("Permutations tested", "-", "(- / SEC)")
        self._add_content(self.att_widget)

        self.time_widget = ImportProgressLine("Time elapsed", "00:00", "")
        self._add_content(self.time_widget)


        self.end_now_btn = Button("End now")
        self.end_now_btn.clicked.connect(self._on_end_now_clicked)
        self._add_action(self.end_now_btn, auto_close=False)

        self.cancel_button = Button("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self._add_action(self.cancel_button, auto_close=False)



        self.create_time = perf_counter()
        # (timestamp, attempt_count)
        self.attempt_history = deque()

        self.set_progress(None, 0, 0)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time_elapsed)
        self.timer.start(1000)


    def _on_end_now_clicked(self):
        if self._resolved:
            return
        self._resolved = True
        self.finished.emit()

    def _on_cancel_clicked(self):
        if self._resolved:
            return
        self._resolved = True
        self.cancelled.emit()

    def _on_qt_dialog_closed(self, *_qt_result_code):
        self.timer.stop()
        if not self._resolved:
            self._resolved = True
            self.cancelled.emit()

    def _update_time_elapsed(self):
        now = perf_counter()
        mins, secs = divmod(int(now - self.create_time), 60)
        self.time_widget.update_contents(None, f"{mins:02d}:{secs:02d}", None)


    def set_progress(self, brick_count: int | None, layer_count: int, attempt_count: int):

        now = perf_counter()

        self.bc_widget.update_contents(None, None if brick_count is None else f"{brick_count:,}", None)
        self.lay_widget.update_contents(None, f"{layer_count}", None)


        self.attempt_history.append((now, attempt_count))

        cutoff = now - 10.0
        while len(self.attempt_history) > 1 and self.attempt_history[0][0] < cutoff:
            self.attempt_history.popleft()

        if len(self.attempt_history) >= 2:
            old_time, old_attempts = self.attempt_history[0]
            elapsed = now - old_time
            attempts = attempt_count - old_attempts

            if elapsed < 0:
                return
            rate = attempts / elapsed
            self.att_widget.update_contents(None, f"{attempt_count:,}", f"({rate:,.0f} / SEC)")
