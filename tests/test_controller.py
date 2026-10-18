import unittest
from gesture_mouse.config import Config
from gesture_mouse.controller import Controller
from .handgen import make_hand

STEP = 1 / 30


class FakeMouse:
    def __init__(self): self.ev, self.moves = [], []
    def move(self, x, y): self.moves.append((x, y))
    def down(self, b): self.ev.append(("down", b))
    def up(self, b): self.ev.append(("up", b))
    def click(self, b): self.ev.append(("click", b))
    def scroll(self, n): self.ev.append(("scroll", n))
    def hscroll(self, n): self.ev.append(("hscroll", n))
    def zoom(self, n): self.ev.append(("zoom", n))
    def swipe(self, d): self.ev.append(("swipe", d))
    def kinds(self, k): return [e for e in self.ev if e[0] == k]


class Rig:
    def __init__(self, **cfg):
        self.m = FakeMouse()
        self.c = Controller(Config(**cfg), self.m, (1920, 1080))
        self.t = 0.0

    def feed(self, hands, seconds, step=STEP):
        end = self.t + seconds
        while self.t < end - 1e-9:
            self.c.process(hands() if callable(hands) else hands, now=self.t)
            self.t += step


class ControllerTests(unittest.TestCase):
    def test_mapping_corners_and_centre(self):
        r = Rig()
        cx, cy = r.c._map(0.5, 0.4)
        self.assertAlmostEqual(cx, 959.5, delta=1); self.assertAlmostEqual(cy, 539.5, delta=1)
        self.assertEqual(r.c._map(0.0, 0.0), (0.0, 0.0))
        self.assertEqual(r.c._map(1.0, 1.0), (1919.0, 1079.0))

    def test_point_moves_cursor_within_screen(self):
        r = Rig()
        r.feed({"Right": make_hand(index=True)}, 0.3)
        self.assertTrue(r.m.moves)
        for x, y in r.m.moves:
            self.assertTrue(0 <= x < 1920 and 0 <= y < 1080)

    def test_quick_pinch_is_left_click_not_drag(self):
        r = Rig()
        r.feed({"Right": make_hand(index=True)}, 0.2)
        r.feed({"Right": make_hand(index=True, pinch="index")}, 0.15)
        r.feed({"Right": make_hand(index=True)}, 0.2)
        self.assertEqual(r.m.ev, [("click", "left")])

    def test_cursor_frozen_during_pinch(self):
        r = Rig()
        r.feed({"Right": make_hand(index=True)}, 0.3)
        n = len(r.m.moves)
        r.feed({"Right": make_hand(index=True, pinch="index", dx=0.05)}, 0.2)
        self.assertLessEqual(len(r.m.moves), n + 1)   # at most the single rewind move

    def test_long_pinch_drags(self):
        r = Rig()
        r.feed({"Right": make_hand(index=True)}, 0.1)
        r.feed({"Right": make_hand(index=True, pinch="index")}, 0.6)
        r.feed({"Right": make_hand(index=True)}, 0.1)
        self.assertEqual(r.m.ev, [("down", "left"), ("up", "left")])

    def test_right_and_middle_click(self):
        r = Rig()
        r.feed({"Right": make_hand(middle=True, pinch="middle")}, 0.15)
        r.feed({"Right": make_hand()}, 0.2)
        r.feed({"Right": make_hand(ring=True, pinch="ring")}, 0.15)
        r.feed({"Right": make_hand()}, 0.2)
        self.assertEqual(r.m.ev, [("click", "right"), ("click", "middle")])

    def test_scroll_up_and_down(self):
        r = Rig()
        k = {"n": 0}
        def up(): k["n"] += 1; return {"Right": make_hand(index=True, middle=True, dy=-0.02 * k["n"])}
        r.feed(up, 0.5)
        s = r.m.kinds("scroll")
        self.assertTrue(s and all(v > 0 for _, v in s))
        r2 = Rig(natural_scroll=True); k["n"] = 0
        def up2(): k["n"] += 1; return {"Right": make_hand(index=True, middle=True, dy=-0.02 * k["n"])}
        r2.feed(up2, 0.5)
        self.assertTrue(all(v < 0 for _, v in r2.m.kinds("scroll")))

    def test_horizontal_scroll(self):
        r = Rig(); k = {"n": 0}
        def right(): k["n"] += 1; return {"Right": make_hand(index=True, middle=True, dx=0.02 * k["n"])}
        r.feed(right, 0.5)
        self.assertTrue(r.m.kinds("hscroll") and not r.m.kinds("scroll"))

    def test_swipe_once_with_cooldown(self):
        r = Rig(); k = {"n": 0}
        def sw(): k["n"] += 1; return {"Right": make_hand(index=True, middle=True, ring=True, dx=0.05 * (k["n"] - 1))}
        r.feed(sw, 0.8, step=0.1)
        self.assertEqual(r.m.kinds("swipe"), [("swipe", "right")])

    def test_two_hand_zoom_no_clicks(self):
        r = Rig(); k = {"n": 0}
        def z():
            k["n"] += 1; s = 0.15 + 0.01 * k["n"]
            return {"Left": make_hand(index=True, pinch="index", dx=-s), "Right": make_hand(index=True, pinch="index", dx=s)}
        r.feed(z, 0.6)
        r.feed({"Left": make_hand(), "Right": make_hand()}, 0.3)
        zs = r.m.kinds("zoom")
        self.assertTrue(zs and all(v > 0 for _, v in zs))
        self.assertFalse(r.m.kinds("click") or r.m.kinds("down"))

    def test_pause_resume_with_both_palms(self):
        r = Rig()
        palm = lambda: {"Left": make_hand(True, True, True, True, True), "Right": make_hand(True, True, True, True, True)}
        r.feed(palm, 2.5)
        self.assertFalse(r.c.enabled)
        r.m.moves.clear()
        r.feed({"Right": make_hand(index=True)}, 0.3)
        self.assertEqual(r.m.moves, [])                    # paused: no cursor movement
        r.feed({"Left": make_hand(), "Right": make_hand()}, 0.2)
        r.feed(palm, 2.0)
        self.assertTrue(r.c.enabled)

    def test_drag_released_when_hand_lost(self):
        r = Rig()
        r.feed({"Right": make_hand(index=True, pinch="index")}, 0.6)
        self.assertEqual(r.m.kinds("down"), [("down", "left")])
        r.feed({}, 0.2)
        self.assertFalse(r.m.kinds("up"))                  # grace period
        r.feed({}, 0.4)
        self.assertEqual(r.m.kinds("up"), [("up", "left")])

    def test_primary_hand_drives_cursor(self):
        r = Rig(primary_hand="Right")
        r.feed({"Left": make_hand(index=True), "Right": make_hand(index=True)}, 0.2)
        self.assertEqual(r.c.cursor_hand, "Right")

    def test_secondary_hand_can_click_while_primary_points(self):
        r = Rig()
        r.feed({"Right": make_hand(index=True), "Left": make_hand()}, 0.2)
        r.feed({"Right": make_hand(index=True), "Left": make_hand(index=True, pinch="index")}, 0.15)
        r.feed({"Right": make_hand(index=True), "Left": make_hand()}, 0.2)
        self.assertEqual(r.m.ev, [("click", "left")])


if __name__ == "__main__":
    unittest.main()
