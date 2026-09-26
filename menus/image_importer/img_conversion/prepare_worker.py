"""
prepare_worker.py

Runs everything between "the user clicked Import" and "we have bricks" off the GUI thread: resize, blur,
quantization and (for the non-slow modes) the merging itself. On big images each of those can take a long
time, and doing it on the GUI thread froze the whole app.

For "3d_slow" only the preparation is done here (finished emits the processed image); the multi-process
search is DecomposeWorker's job and starts afterwards.

Signals are meant to be connected to bound methods of QObjects living on the GUI thread, so Qt queues
their delivery to it.
"""

from __future__ import annotations

import threading
from threading import Event

from PIL import Image, ImageFilter
from PySide6.QtCore import QObject, Signal

from .image_layers import decompose_image
from .quantize import quantize_image


class ImportPrepareWorker(QObject):
    """
    stage:    (text) name of the step now running
    progress: (done, total) colors merged so far, only emitted while merging
    finished: DecomposeResult, or the prepared PIL image when `decompose` is False
    failed:   the exception raised by any step
    """

    stage = Signal(str)
    progress = Signal(int, int)
    finished = Signal(object)
    failed = Signal(object)

    def __init__(
        self,
        image: Image.Image,
        resolution: tuple[int, int],
        blur: float,
        quantization: str | None,   # None = no quantization, else "median_cut" | "kmeans_oklab"
        color_count: int,
        mode: str,                  # "none" | "2d" | "3d_greedy" | "3d_slow"
        max_layers: int,
        parent=None,
    ):
        super().__init__(parent)
        self._image = image
        self._resolution = resolution
        self._blur = blur
        self._quantization = quantization
        self._color_count = color_count
        self._mode = mode
        self._max_layers = max_layers
        self._cancel = Event()

    def cancel(self) -> None:
        """Steps that can't be interrupted (resize, blur, quantization) finish in the background; merging
        stops at the next color. Either way nothing is emitted anymore once cancelled."""
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def run(self) -> None:
        try:
            img = self._image
            if img.size != self._resolution:
                self.stage.emit("Resizing image")
                img = img.resize(self._resolution, Image.Resampling.LANCZOS)
            if self._cancel.is_set():
                return

            if self._blur > 0:
                self.stage.emit("Blurring image")
                img = img.filter(ImageFilter.GaussianBlur(radius=self._blur))
                if self._cancel.is_set():
                    return

            if self._quantization is not None:
                self.stage.emit("Reducing colors")
                img = quantize_image(img, self._color_count, self._quantization)
                if self._cancel.is_set():
                    return

            if self._mode == "3d_slow":
                if not self._cancel.is_set():
                    self.finished.emit(img)
                return

            self.stage.emit("Merging bricks")
            result = decompose_image(
                image=img,
                mode=self._mode,
                max_layers=self._max_layers,
                max_restarts=None,
                cancel_check=self._cancel.is_set,
                color_progress=self.progress.emit,
            )
            if not self._cancel.is_set():
                self.finished.emit(result)

        except BaseException as exc:  # reported to the user instead of dying silently in a daemon thread
            if not self._cancel.is_set():
                self.failed.emit(exc)
