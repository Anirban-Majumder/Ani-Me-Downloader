# coding: utf-8
"""Periodic tick that triggers an anime pass."""
import time

from PyQt5.QtCore import QThread, pyqtSignal


class RunThread(QThread):
    """Sleep `interval_seconds` then emit `tick` repeatedly until stopped."""
    tick = pyqtSignal()

    def __init__(self, interval_seconds_provider):
        super().__init__()
        self._provider = interval_seconds_provider
        self._stop = False

    def stop(self) -> None:
        self._stop = True
        self.requestInterruption()

    def run(self) -> None:
        while not self._stop and not self.isInterruptionRequested():
            interval = max(1, int(self._provider()))
            for _ in range(interval):
                if self._stop or self.isInterruptionRequested():
                    return
                time.sleep(1)
            self.tick.emit()
