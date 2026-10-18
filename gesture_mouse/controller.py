"""Gesture state machine: turns per-frame hand info into mouse actions.

Depends only on a `mouse` object (see mouse_backend.py), so it can be tested
with a fake mouse and a fake clock - no camera or screen needed.
"""
from __future__ import annotations

import math
import time
from collections import deque
from typing import Dict, List, Optional, Sequence, Tuple

from .config import Config
from .gestures import PALM, POINT, SCROLL, SWIPE, HandInfo, analyze
from .smoothing import OneEuro

BUTTON = {"index": "left", "middle": "right", "ring": "middle"}


class HandState:
    def __init__(self) -> None:
        self.pinch: Optional[str] = None
        self.pinch_t = 0.0
        self.dragging = False
        self.suppress = False            # ignore this pinch (used by zoom)
        self.scroll_prev: Optional[Tuple[float, float]] = None
        self.swipe_hist: deque = deque()
        self.swipe_cd = 0.0
        self.lost_since: Optional[float] = None


class Controller:
    def __init__(self, cfg: Config, mouse, screen_size: Tuple[int, int], clock=time.monotonic):
        self.cfg = cfg
        self.mouse = mouse
        self.sw, self.sh = screen_size
        self.clock = clock
        self.enabled = True
        self.states: Dict[str, HandState] = {}
        self.cursor_hand: Optional[str] = None
        self.status: dict = {}
        self._fx = OneEuro(cfg.min_cutoff, cfg.beta, cfg.d_cutoff)
        self._fy = OneEuro(cfg.min_cutoff, cfg.beta, cfg.d_cutoff)
        self._last_move_t = -1e9
        self._trail: deque = deque()
        self._zoom_prev: Optional[float] = None
        self._palm_since: Optional[float] = None
        self._toggle_cd = 0.0
        self._need_release = False

    # ------------------------------------------------------------ public
    def process(self, hands: Dict[str, Sequence[Tuple[float, float]]],
                aspect: float = 1.0, now: Optional[float] = None) -> dict:
        now = self.clock() if now is None else now
        cfg = self.cfg
        infos: Dict[str, HandInfo] = {}
        for label, lm in hands.items():
            st = self.states.setdefault(label, HandState())
            st.lost_since = None
            infos[label] = analyze(lm, st.pinch, aspect, cfg.pinch_engage, cfg.pinch_release)
        self._drop_lost(hands, now)
        self._update_toggle(infos, now)

        zoom = False
        if self.enabled and infos:
            zoom = len(infos) == 2 and all(i.pinch == "index" for i in infos.values())
            self._choose_cursor_hand(infos)
            for label, info in infos.items():
                st = self.states[label]
                self._pinch(label, st, info, zoom, now)
                self._scroll(st, info)
                self._swipe(st, info, now)
            self._zoom(infos, zoom, aspect)
            self._cursor(infos, now)
        elif not infos:
            self._zoom_prev = None

        self.status = {
            "enabled": self.enabled,
            "zoom": zoom,
            "cursor_hand": self.cursor_hand,
            "hands": {
                l: (i.pose, i.pinch, self.states[l].dragging if l in self.states else False)
                for l, i in infos.items()
            },
        }
        return self.status

    def set_enabled(self, value: bool) -> None:
        self.enabled = value
        if not value:
            self.release_all()

    def release_all(self) -> None:
        for st in self.states.values():
            if st.dragging:
                self.mouse.up("left")
        self.states.clear()
        self.cursor_hand = None
        self._zoom_prev = None
        if hasattr(self.mouse, "release_all"):
            self.mouse.release_all()

    # ----------------------------------------------------------- helpers
    def _map(self, ax: float, ay: float) -> Tuple[float, float]:
        c = self.cfg
        nx = (ax - c.margin_x) / (1.0 - 2.0 * c.margin_x)
        ny = (ay - c.margin_top) / (1.0 - c.margin_top - c.margin_bottom)
        nx = min(max(nx, 0.0), 1.0)
        ny = min(max(ny, 0.0), 1.0)
        return nx * (self.sw - 1), ny * (self.sh - 1)

    def _drop_lost(self, hands, now: float) -> None:
        for label in list(self.states):
            if label in hands:
                continue
            st = self.states[label]
            if st.lost_since is None:
                st.lost_since = now
            if now - st.lost_since > self.cfg.lost_grace_s:
                if st.dragging:
                    self.mouse.up("left")
                del self.states[label]
                if self.cursor_hand == label:
                    self.cursor_hand = None

    def _update_toggle(self, infos: Dict[str, HandInfo], now: float) -> None:
        both = len(infos) == 2 and all(i.pose == PALM for i in infos.values())
        if not both:
            self._palm_since = None
            self._need_release = False
            return
        if self._need_release:
            return
        if self._palm_since is None:
            self._palm_since = now
        elif now - self._palm_since >= self.cfg.toggle_hold_s and now >= self._toggle_cd:
            self.set_enabled(not self.enabled)
            self._toggle_cd = now + 2.0
            self._palm_since = None
            self._need_release = True

    def _choose_cursor_hand(self, infos: Dict[str, HandInfo]) -> None:
        def drives(label: str, info: HandInfo) -> bool:
            st = self.states[label]
            return info.pose == POINT or info.pinch is not None or st.dragging

        cands: List[str] = [l for l, i in infos.items() if drives(l, i)]
        cur = self.cursor_hand
        if cur in cands and (self.states[cur].pinch is not None or self.states[cur].dragging):
            return
        if self.cfg.primary_hand in cands:
            self.cursor_hand = self.cfg.primary_hand
        elif cur in cands:
            return
        else:
            self.cursor_hand = cands[0] if cands else None

    def _rewind_cursor(self, now: float) -> None:
        for t, x, y in self._trail:
            if t >= now - self.cfg.pinch_lookback_s:
                self.mouse.move(x, y)
                return

    def _pinch(self, label: str, st: HandState, info: HandInfo, zoom: bool, now: float) -> None:
        old, new = st.pinch, info.pinch
        if old is not None and old != new:               # released / switched
            if st.dragging:
                self.mouse.up("left")
                st.dragging = False
            elif not st.suppress:
                self.mouse.click(BUTTON[old])
            st.suppress = False
        if new is not None and new != old:               # started
            st.pinch_t, st.suppress, st.dragging = now, zoom, False
            if label == self.cursor_hand:
                self._rewind_cursor(now)
        st.pinch = new
        if new is None:
            return
        if zoom and not st.suppress:                     # zoom began mid-pinch
            if st.dragging:
                self.mouse.up("left")
                st.dragging = False
            st.suppress = True
        elif (new == "index" and not st.dragging and not st.suppress
              and now - st.pinch_t >= self.cfg.drag_hold_s):
            self.mouse.down("left")
            st.dragging = True

    def _scroll(self, st: HandState, info: HandInfo) -> None:
        if info.pose != SCROLL or info.pinch is not None:
            st.scroll_prev = None
            return
        c = info.center
        if st.scroll_prev is None:
            st.scroll_prev = c
            return
        dx, dy = c[0] - st.scroll_prev[0], c[1] - st.scroll_prev[1]
        if math.hypot(dx, dy) < self.cfg.scroll_deadzone:
            return                                       # accumulate small moves
        k = -1.0 if self.cfg.natural_scroll else 1.0
        speed = self.cfg.scroll_speed
        if abs(dy) >= abs(dx):
            self.mouse.scroll(-dy * speed * k)
        else:
            self.mouse.hscroll(dx * speed * k)
        st.scroll_prev = c

    def _swipe(self, st: HandState, info: HandInfo, now: float) -> None:
        if info.pose != SWIPE or info.pinch is not None:
            st.swipe_hist.clear()
            return
        cx, cy = info.center
        st.swipe_hist.append((now, cx, cy))
        while st.swipe_hist and now - st.swipe_hist[0][0] > self.cfg.swipe_window_s:
            st.swipe_hist.popleft()
        if now < st.swipe_cd or len(st.swipe_hist) < 3:
            return
        dx, dy = cx - st.swipe_hist[0][1], cy - st.swipe_hist[0][2]
        if max(abs(dx), abs(dy)) < self.cfg.swipe_distance:
            return
        if abs(dx) >= abs(dy):
            direction = "right" if dx > 0 else "left"
        else:
            direction = "down" if dy > 0 else "up"
        self.mouse.swipe(direction)
        st.swipe_cd = now + self.cfg.swipe_cooldown_s
        st.swipe_hist.clear()

    def _zoom(self, infos: Dict[str, HandInfo], zoom: bool, aspect: float) -> None:
        if not zoom:
            self._zoom_prev = None
            return
        a, b = [i.pinch_pt for i in infos.values()]
        d = math.hypot((a[0] - b[0]) * aspect, a[1] - b[1])
        if self._zoom_prev is None:
            self._zoom_prev = d
            return
        delta = d - self._zoom_prev
        if abs(delta) >= self.cfg.zoom_deadzone:
            self.mouse.zoom(delta * self.cfg.zoom_speed)
            self._zoom_prev = d

    def _cursor(self, infos: Dict[str, HandInfo], now: float) -> None:
        label = self.cursor_hand
        if label not in infos:
            return
        st = self.states[label]
        if st.pinch is not None and not st.dragging:
            return                                       # cursor frozen while pinching
        ax, ay = infos[label].anchor
        if now - self._last_move_t > 0.25:
            self._fx.reset()
            self._fy.reset()
        x, y = self._map(self._fx(ax, now), self._fy(ay, now))
        self.mouse.move(x, y)
        self._last_move_t = now
        self._trail.append((now, x, y))
        while self._trail and now - self._trail[0][0] > 1.0:
            self._trail.popleft()
