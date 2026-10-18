"""MediaPipe Hands wrapper. Returns {"Left": landmarks, "Right": landmarks}."""
from __future__ import annotations

import os

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2
import mediapipe as mp

from .config import Config


class HandTracker:
    def __init__(self, cfg: Config) -> None:
        self._mp_hands = mp.solutions.hands
        self._draw = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=cfg.model_complexity,
            min_detection_confidence=cfg.detection_confidence,
            min_tracking_confidence=cfg.tracking_confidence,
        )
        self._last = []

    def process(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self._hands.process(rgb)
        found = []
        if res.multi_hand_landmarks:
            for hand, handed in zip(res.multi_hand_landmarks, res.multi_handedness):
                lm = [(p.x, p.y) for p in hand.landmark]
                found.append((handed.classification[0].label, lm, hand))
        # Frame is mirrored before processing, so labels match the user's real hands.
        # If both hands get the same label, assign by horizontal position instead.
        if len(found) == 2 and found[0][0] == found[1][0]:
            found.sort(key=lambda h: h[1][0][0])
            found[0] = ("Left",) + found[0][1:]
            found[1] = ("Right",) + found[1][1:]
        self._last = [f[2] for f in found]
        return {label: lm for label, lm, _ in found}

    def draw(self, frame) -> None:
        for hand in self._last:
            self._draw.draw_landmarks(frame, hand, self._mp_hands.HAND_CONNECTIONS)

    def close(self) -> None:
        self._hands.close()
