"""Threaded webcam reader: always returns the newest frame (low latency)."""
from __future__ import annotations

import sys
import threading
import time

import cv2


class Camera:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480) -> None:
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(index, backend)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open camera {index}. Check it is connected, not used by another "
                "app, and that camera permission is granted to your terminal/app."
            )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._frame = None
        self._seq = 0
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self._lock:
                self._frame, self._seq = frame, self._seq + 1

    def read(self, last_seq: int = -1, timeout: float = 1.0):
        """Return (frame, seq) once a frame newer than last_seq exists."""
        end = time.time() + timeout
        while time.time() < end:
            with self._lock:
                if self._frame is not None and self._seq != last_seq:
                    return self._frame.copy(), self._seq
            time.sleep(0.002)
        return None, last_seq

    def stop(self) -> None:
        self._running = False
        self._thread.join(timeout=1.0)
        self.cap.release()
