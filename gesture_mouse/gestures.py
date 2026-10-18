"""Pure geometry: turn 21 hand landmarks into a pose + pinch state.

No camera / OS dependencies, so it is fully unit-testable.
Landmarks are (x, y) in normalised image coordinates (0..1).
MediaPipe indices: 0 wrist, 4 thumb tip, 5/9/13/17 finger MCPs,
6/10/14/18 PIPs, 8/12/16/20 fingertips.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

Point = Tuple[float, float]

POINT, SCROLL, SWIPE, PALM, FIST, OTHER = "POINT", "SCROLL", "SWIPE", "PALM", "FIST", "OTHER"

# finger -> (MCP, PIP, DIP, TIP)
FINGERS = {
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
EXTEND_RATIO = 1.10      # tip must be this much farther from wrist than PIP
PINCH_REACH = 1.15       # pinching fingertip must be beyond its knuckle (rejects fists)


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


@dataclass
class HandInfo:
    pose: str
    pinch: Optional[str]                 # None | "index" | "middle" | "ring"
    fingers: Dict[str, bool] = field(default_factory=dict)
    ratios: Dict[str, float] = field(default_factory=dict)
    anchor: Point = (0.0, 0.0)           # cursor anchor (index knuckle)
    center: Point = (0.0, 0.0)           # hand centre (middle knuckle)
    pinch_pt: Point = (0.0, 0.0)         # midpoint of thumb tip and index tip
    size: float = 0.0


def analyze(
    lm: Sequence[Point],
    prev_pinch: Optional[str] = None,
    aspect: float = 1.0,
    engage: float = 0.22,
    release: float = 0.38,
) -> HandInfo:
    pts = [(x * aspect, y) for x, y in lm]      # undo non-square pixel stretch
    wrist = pts[0]
    size = max(dist(wrist, pts[9]), 1e-6)

    ext = {
        name: dist(pts[tip], wrist) > dist(pts[pip], wrist) * EXTEND_RATIO
        for name, (_m, pip, _d, tip) in FINGERS.items()
    }
    ext["thumb"] = dist(pts[4], pts[17]) > dist(pts[3], pts[17]) * 1.05

    ratios: Dict[str, float] = {}
    for name in ("index", "middle", "ring"):
        mcp, _p, _d, tip = FINGERS[name]
        if dist(pts[tip], wrist) < dist(pts[mcp], wrist) * PINCH_REACH:
            ratios[name] = 9.9                   # curled into a fist, not a pinch
        else:
            ratios[name] = dist(pts[4], pts[tip]) / size

    pinch = None
    if prev_pinch and ratios.get(prev_pinch, 9.9) < release:
        pinch = prev_pinch                       # hysteresis: stay pinched
    else:
        best = min(ratios, key=ratios.get)
        if ratios[best] < engage:
            pinch = best

    i, m, r, p = ext["index"], ext["middle"], ext["ring"], ext["pinky"]
    if i and m and r and p:
        pose = PALM
    elif not (i or m or r or p):
        pose = FIST
    elif i and not (m or r or p):
        pose = POINT
    elif i and m and not (r or p):
        pose = SCROLL
    elif i and m and r and not p:
        pose = SWIPE
    else:
        pose = OTHER

    return HandInfo(
        pose=pose,
        pinch=pinch,
        fingers=ext,
        ratios=ratios,
        anchor=tuple(lm[5]),
        center=tuple(lm[9]),
        pinch_pt=((lm[4][0] + lm[8][0]) / 2, (lm[4][1] + lm[8][1]) / 2),
        size=size,
    )
