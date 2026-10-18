"""Configuration: defaults live here, overrides come from config.json."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, fields

log = logging.getLogger("gesture_mouse")


@dataclass
class Config:
    # --- camera -------------------------------------------------------
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    mirror: bool = True              # mirror image so it behaves like a mirror

    # --- hand tracking (MediaPipe) -----------------------------------
    model_complexity: int = 0        # 0 = fast, 1 = more accurate
    detection_confidence: float = 0.7
    tracking_confidence: float = 0.6
    primary_hand: str = "Right"      # hand that moves cursor if both are active

    # --- active region (fractions of camera frame) -------------------
    margin_x: float = 0.15
    margin_top: float = 0.10
    margin_bottom: float = 0.30

    # --- cursor smoothing (One Euro filter) --------------------------
    min_cutoff: float = 1.2          # lower = smoother at rest, more lag
    beta: float = 12.0               # higher = less lag when moving fast
    d_cutoff: float = 1.0

    # --- pinch / click / drag ----------------------------------------
    pinch_engage: float = 0.22       # thumb-finger distance / hand size
    pinch_release: float = 0.38      # must open past this to release
    pinch_lookback_s: float = 0.12   # cursor rewinds this much on pinch start
    drag_hold_s: float = 0.35        # hold pinch this long to start a drag

    # --- scroll -------------------------------------------------------
    scroll_speed: float = 40.0       # wheel notches per full-frame movement
    scroll_deadzone: float = 0.002
    natural_scroll: bool = False     # True = content follows the fingers

    # --- three-finger swipe ------------------------------------------
    swipe_distance: float = 0.16
    swipe_window_s: float = 0.6
    swipe_cooldown_s: float = 0.9

    # --- two-hand zoom -----------------------------------------------
    zoom_speed: float = 30.0
    zoom_deadzone: float = 0.002

    # --- pause / safety ----------------------------------------------
    toggle_hold_s: float = 1.5       # both open palms held this long = pause
    lost_grace_s: float = 0.4        # keep a drag alive through tracking dropouts

    # --- UI -----------------------------------------------------------
    preview: bool = True
    show_help: bool = True


def load_config(path: str | None = None) -> Config:
    cfg = Config()
    if not path or not os.path.exists(path):
        return cfg
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    known = {f.name: f for f in fields(Config)}
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if key not in known:
            log.warning("Unknown config key ignored: %s", key)
            continue
        default = getattr(cfg, key)
        try:
            setattr(cfg, key, type(default)(value))
        except (TypeError, ValueError):
            log.warning("Bad value for %s: %r (keeping %r)", key, value, default)
    return cfg
