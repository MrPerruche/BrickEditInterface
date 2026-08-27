"""
decompose_worker.py

Threading / multiprocessing wrapper around image_layers.decompose_layered,
for use from a PySide6 app without blocking the GUI thread.

Why multiprocessing and not just threads
------------------------------------------------------------------------
Standard CPython 3.13 (unless you've deliberately installed the
experimental free-threaded build, "python3.13t") still has the GIL.
QThread / threading.Thread are great for getting work OFF the GUI thread
so the UI stays responsive, but they do NOT give real parallelism for
CPU-bound pure-Python code -- only one thread runs Python bytecode at a
time no matter how many QThreads you spin up. Separate *processes* each
get their own interpreter and their own GIL, which is what actually lets
multiple CPU cores crunch on different restarts of "3D stacking (slow)"
mode at the same time.

Design
------------------------------------------------------------------------
- A single background thread (run `DecomposeWorker.run`, either via
  `threading.Thread` or a `QThread` -- both shown at the bottom) acts as
  the coordinator.
- It always computes the plain deterministic greedy pass FIRST,
  synchronously, before anything else -- this seeds `best`, so the
  restart search that follows can only ever replace it with something at
  least as good, never worse.
- For "3d_slow" mode, the coordinator then farms out further restarts to
  a ProcessPoolExecutor, one restart per task, and streams results back
  as they complete. Restarts are NOT independent random orderings -- each
  task's color ordering is a small perturbation (`perturb_ordering`, in
  image_layers.py) of the current best-known ordering, i.e. local search
  rather than pure random restart. Rationale: with `n!` possible color
  orderings, pure-random sampling almost never lands near a previously
  -good ordering, so most attempts are wasted; small perturbations of an
  already-good ordering tend to still be decent, and that locality is
  exactly what pure-random restarts throw away. To avoid getting stuck in
  a local optimum, a run of `stale_restart_threshold` restarts in a row
  with no improvement triggers one full-random reshuffle (a big jump)
  before resuming local perturbation from wherever that lands.
- The heavy, shared, read-only data (color_grid) is sent to each worker
  process exactly once via the pool's `initializer`, not re-pickled on
  every single restart submission.
- Progress and the final result are delivered via Qt signals. Emitting a
  signal from a background thread is safe -- Qt automatically queues
  delivery to whichever thread owns the receiving QObject (normally your
  main/GUI thread), so ordinary signal/slot connections just work without
  you having to marshal anything by hand.

Gotchas worth knowing about beyond this file
------------------------------------------------------------------------
- multiprocessing's default start method on Windows and macOS is "spawn":
  worker processes re-import your __main__ module, so your app's entry
  script needs `if __name__ == "__main__":` around the QApplication /
  app-launch code, or you'll get a runaway process-spawn loop.
- Anything sent into a worker process (initializer args, the task
  function itself) must be importable / picklable at module scope -- no
  lambdas or closures as the task function, which is why _run_restart
  below is a plain top-level function.
"""

from __future__ import annotations

import os
import random
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from threading import Event
from typing import Optional

from PySide6.QtCore import QObject, Signal

from .image_layers import (
    DecomposeResult,
    decompose_layered,
    load_color_grid,
    perturb_ordering,
)


# --------------------------------------------------------------------------- #
# Worker-process side: module-level (picklable) state + task function
# --------------------------------------------------------------------------- #

_worker_state: dict = {}


def _init_worker(color_grid, transparent_id, max_layers: int) -> None:
    """Runs once per worker process when the pool starts -- stashes the
    shared, read-only data so individual tasks don't have to re-send it."""
    _worker_state["color_grid"] = color_grid
    _worker_state["transparent_id"] = transparent_id
    _worker_state["max_layers"] = max_layers
    # Populated lazily, one color at a time, the first time each color_id
    # is seen -- then reused for every subsequent restart this same
    # worker process handles. A color's own connected components never
    # change across restarts (only processing order/allowed regions do),
    # so this turns "recompute cc_label+find_objects for every color on
    # every restart" into "compute it once per color per worker process".
    _worker_state["color_components_cache"] = {}


def _run_restart(color_order: list[int]):
    """One restart using an explicit color ordering (a perturbation of the
    current best-known ordering, or an occasional full reshuffle -- see
    DecomposeWorker.run). Must stay at module scope so it can be pickled
    and dispatched to a worker process. Payload is tiny (n_colors small
    ints), so no pickling-cost concern even at high restart volume."""
    result = decompose_layered(
        _worker_state["color_grid"],
        _worker_state["transparent_id"],
        _worker_state["max_layers"],
        order=color_order,
        color_components_cache=_worker_state["color_components_cache"],
    )
    total = sum(len(layer) for layer in result.layers)
    return total, result


# --------------------------------------------------------------------------- #
# Coordinator: QObject with signals, safe to run from any background thread
# --------------------------------------------------------------------------- #

class DecomposeWorker(QObject):
    """
    progress: (best_total_rects, best_layers_used, restarts_completed)
              emitted once for the initial greedy pass (restarts_completed=0)
              and again every time a restart beats the current best.
    finished: the final DecomposeResult -- always populated, even if
              cancelled immediately (falls back to the greedy result).
    """

    progress = Signal(int, int, int)
    finished = Signal(object)

    def __init__(
        self,
        image,
        mode: str = "3d_slow",       # "3d_greedy" | "3d_slow"
        max_layers: int = 8,
        max_restarts: Optional[int] = 12,   # None = unlimited, run until cancel()
        max_workers: Optional[int] = None,
        alpha_threshold: int = 1,
        progress_min_interval: float = 0.2,          # seconds between heartbeat updates
        progress_min_attempts: Optional[int] = None,  # or key the heartbeat off attempt count instead
        stale_restart_threshold: int = 40,  # restarts w/o improvement before a full-random reshuffle
        seed: Optional[int] = None,          # None = non-deterministic (fresh random each run)
        parent=None,
    ):
        super().__init__(parent)
        self._image = image
        self._mode = mode
        self._max_layers = max_layers
        self._max_restarts = max_restarts
        self._max_workers = max_workers
        self._alpha_threshold = alpha_threshold
        self._progress_min_interval = progress_min_interval
        self._progress_min_attempts = progress_min_attempts
        self._stale_restart_threshold = stale_restart_threshold
        self._rng = random.Random(seed)
        self._cancel = Event()
        self._pool: Optional[ProcessPoolExecutor] = None

    def cancel(self) -> None:
        """Safe to call from the GUI thread. Stops picking up new restart
        results; any restarts already running in a worker process finish
        in the background regardless (a couple seconds at most at these
        image sizes) -- they just won't be waited on."""
        self._cancel.set()
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)

    def run(self) -> None:
        """Call this from a background thread (a QThread.run override, or
        plain threading.Thread(target=worker.run) -- both shown below)."""
        color_grid, palette, transparent_id = load_color_grid(self._image, self._alpha_threshold)

        # Seed with the deterministic greedy pass first, synchronously.
        # Everything after this point may only replace `best` with
        # something at least as good -- never worse.
        greedy = decompose_layered(color_grid, transparent_id, self._max_layers, order="area_desc")
        best_layers = greedy.layers
        best_score = (greedy.overflow_pixels, sum(len(l) for l in best_layers))
        best_ordering = greedy.color_order
        self.progress.emit(best_score[1], len(best_layers), 0)

        if self._mode == "3d_slow" and not self._cancel.is_set():
            self._pool = ProcessPoolExecutor(
                max_workers=self._max_workers,
                initializer=_init_worker,
                initargs=(color_grid, transparent_id, self._max_layers),
            )
            pool_size = self._max_workers or os.cpu_count() or 1
            unlimited = self._max_restarts is None
            submitted = 0
            stale_count = 0  # restarts since the last improvement

            def next_candidate_order():
                # Local search: perturb the current best ordering. After a
                # long enough stale run, inject one full-random reshuffle
                # (a big jump) instead, to escape a local optimum, then
                # resume perturbing from wherever that lands.
                nonlocal stale_count
                if stale_count >= self._stale_restart_threshold:
                    reshuffled = list(best_ordering)
                    self._rng.shuffle(reshuffled)
                    stale_count = 0
                    return reshuffled
                return perturb_ordering(best_ordering, self._rng)

            def submit_next():
                # Lazily produces one more restart, instead of ever
                # materializing a full list of attempts up front -- this
                # is what lets max_restarts=None mean "run until
                # cancelled" without trying to build/queue an enormous
                # (or literally infinite) batch first.
                nonlocal submitted
                if not unlimited and submitted >= self._max_restarts:
                    return None
                candidate_order = next_candidate_order()
                submitted += 1
                future = self._pool.submit(_run_restart, candidate_order)
                pending[future] = candidate_order
                return future

            # future -> ordering_used, so an improving result's ordering
            # can be adopted as the new best_ordering (not just its score).
            pending: dict = {}
            for _ in range(pool_size):
                if submit_next() is None:
                    break

            done_count = 0
            last_emit_time = time.monotonic()
            last_emit_count = 0
            try:
                while pending and not self._cancel.is_set():
                    done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                    for future in done:
                        ordering_used = pending.pop(future)
                        if future.cancelled():
                            continue
                        total, result = future.result()
                        done_count += 1
                        score = (result.overflow_pixels, total)
                        improved = score < best_score
                        if improved:
                            best_score = score
                            best_layers = result.layers
                            best_ordering = ordering_used
                            stale_count = 0
                        else:
                            stale_count += 1

                        now = time.monotonic()
                        heartbeat = (now - last_emit_time) >= self._progress_min_interval or (
                            self._progress_min_attempts is not None
                            and (done_count - last_emit_count) >= self._progress_min_attempts
                        )
                        if improved or heartbeat:
                            self.progress.emit(best_score[1], len(best_layers), done_count)
                            last_emit_time = now
                            last_emit_count = done_count

                    if self._cancel.is_set():
                        break
                    # top back up to pool_size in-flight tasks, one per
                    # completion -- never more tasks queued than workers
                    for _ in range(len(done)):
                        if submit_next() is None:
                            break
            finally:
                if self._pool is not None:
                    self._pool.shutdown(wait=False, cancel_futures=True)
                    self._pool = None

        self.finished.emit(
            DecomposeResult(
                layers=best_layers,
                palette=palette,
                total_rects=best_score[1],
                overflow_pixels=best_score[0],
            )
        )


# --------------------------------------------------------------------------- #
# Two equally valid ways to launch it -- pick whichever fits your codebase
# --------------------------------------------------------------------------- #

def launch_with_threading(worker: DecomposeWorker):
    """Simplest option: a plain Python thread. Fine here because the
    worker has no slots of its own to receive queued calls -- it only
    emits signals outward, so it doesn't need real QThread affinity."""
    import threading
    t = threading.Thread(target=worker.run, daemon=True)
    t.start()
    return t


def launch_with_qthread(worker: DecomposeWorker, qt_parent=None):
    """More idiomatic-Qt option, if you'd rather keep everything in
    Qt's own thread objects instead of mixing in `threading`."""
    from PySide6.QtCore import QThread
    thread = QThread(qt_parent)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    thread.start()
    return thread
