"""Mouse/keyboard output backends.

PyAutoGuiMouse  - real control (Windows, macOS, Linux/X11)
LogMouse        - dry run: only logs what *would* happen (safe for testing)
"""
from __future__ import annotations

import logging
import sys

log = logging.getLogger("gesture_mouse")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

_PLATFORM = "win" if IS_WIN else "mac" if IS_MAC else "linux"
SWIPE_KEYS = {
    "win": {"left": ("ctrl", "winleft", "left"), "right": ("ctrl", "winleft", "right"),
            "up": ("winleft", "tab"), "down": ("winleft", "d")},
    "mac": {"left": ("ctrl", "left"), "right": ("ctrl", "right"),
            "up": ("ctrl", "up"), "down": ("f11",)},
    "linux": {"left": ("ctrl", "alt", "left"), "right": ("ctrl", "alt", "right"),
              "up": ("winleft",), "down": ("winleft", "d")},
}


class BaseMouse:
    screen_size = (1920, 1080)

    def __init__(self) -> None:
        self.last_event = ""
        self.pos = (0, 0)

    def _emit(self, msg: str, quiet: bool = False) -> None:
        self.last_event = msg
        (log.debug if quiet else log.info)(msg)

    def release_all(self) -> None:
        pass


class LogMouse(BaseMouse):
    """Dry-run backend: never touches the real mouse."""

    def __init__(self, size=(1920, 1080)) -> None:
        super().__init__()
        self.screen_size = size

    def move(self, x, y): self.pos = (int(x), int(y))
    def down(self, b): self._emit(f"MOUSE DOWN ({b})")
    def up(self, b): self._emit(f"MOUSE UP ({b})")
    def click(self, b): self._emit(f"CLICK ({b})")
    def scroll(self, n): self._emit(f"SCROLL {n:+.2f}", quiet=True)
    def hscroll(self, n): self._emit(f"H-SCROLL {n:+.2f}", quiet=True)
    def zoom(self, n): self._emit(f"ZOOM {n:+.2f}", quiet=True)
    def swipe(self, d): self._emit(f"SWIPE {d.upper()} -> {'+'.join(SWIPE_KEYS[_PLATFORM][d])}")


class PyAutoGuiMouse(BaseMouse):
    def __init__(self) -> None:
        super().__init__()
        import pyautogui                      # imported lazily so dry-run needs no GUI
        pyautogui.FAILSAFE = False            # corners are valid cursor targets
        pyautogui.PAUSE = 0
        self.pg = pyautogui
        self.screen_size = tuple(pyautogui.size())
        self._held: set = set()
        self._sy = self._sx = self._sz = 0.0

    def move(self, x, y):
        self.pos = (int(x), int(y))
        self.pg.moveTo(self.pos[0], self.pos[1])

    def down(self, b):
        self._held.add(b); self.pg.mouseDown(button=b); self._emit(f"MOUSE DOWN ({b})")

    def up(self, b):
        self._held.discard(b); self.pg.mouseUp(button=b); self._emit(f"MOUSE UP ({b})")

    def click(self, b):
        self.pg.click(button=b); self._emit(f"CLICK ({b})")

    def _wheel(self, acc: float, horizontal: bool) -> float:
        unit = 120 if IS_WIN else 1           # Windows wheel delta = 120 per notch
        amount = int(acc * unit)
        if amount:
            (self.pg.hscroll if horizontal else self.pg.scroll)(amount)
            acc -= amount / unit
        return acc

    def scroll(self, n):
        self._sy = self._wheel(self._sy + n, False); self._emit(f"SCROLL {n:+.2f}", quiet=True)

    def hscroll(self, n):
        self._sx = self._wheel(self._sx + n, True); self._emit(f"H-SCROLL {n:+.2f}", quiet=True)

    def zoom(self, n):
        self._sz += n
        steps = int(self._sz)
        if not steps:
            return
        self._sz -= steps
        self._emit(f"ZOOM {steps:+d}", quiet=True)
        if IS_MAC:
            key = "=" if steps > 0 else "-"
            for _ in range(min(abs(steps), 5)):
                self.pg.hotkey("command", key)
        else:
            self.pg.keyDown("ctrl")
            try:
                self.pg.scroll(steps * (120 if IS_WIN else 1))
            finally:
                self.pg.keyUp("ctrl")

    def swipe(self, d):
        keys = SWIPE_KEYS[_PLATFORM][d]
        self.pg.hotkey(*keys)
        self._emit(f"SWIPE {d.upper()} -> {'+'.join(keys)}")

    def release_all(self):
        for b in list(self._held):
            self.pg.mouseUp(button=b)
        self._held.clear()
