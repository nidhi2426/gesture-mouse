import unittest
from gesture_mouse.gestures import analyze, POINT, SCROLL, SWIPE, PALM, FIST
from gesture_mouse.smoothing import OneEuro
from gesture_mouse.config import Config, load_config
from .handgen import make_hand


class PoseTests(unittest.TestCase):
    def test_point(self):
        i = analyze(make_hand(index=True))
        self.assertEqual((i.pose, i.pinch), (POINT, None))

    def test_scroll(self):
        self.assertEqual(analyze(make_hand(index=True, middle=True)).pose, SCROLL)

    def test_swipe(self):
        self.assertEqual(analyze(make_hand(index=True, middle=True, ring=True)).pose, SWIPE)

    def test_palm(self):
        self.assertEqual(analyze(make_hand(True, True, True, True, thumb=True)).pose, PALM)

    def test_fist_is_not_a_pinch(self):
        i = analyze(make_hand())
        self.assertEqual((i.pose, i.pinch), (FIST, None))

    def test_pinch_variants(self):
        for finger in ("index", "middle", "ring"):
            kw = {finger: True, "pinch": finger}
            self.assertEqual(analyze(make_hand(**kw)).pinch, finger, finger)

    def test_pinch_hysteresis(self):
        h = make_hand(index=True, pinch="index")
        looser = [(x, y) for x, y in h]
        looser[4] = (h[8][0] + 0.07, h[8][1] + 0.02)      # ratio ~0.26: between thresholds
        self.assertIsNone(analyze(looser).pinch)           # would not engage...
        self.assertEqual(analyze(looser, prev_pinch="index").pinch, "index")  # ...but holds

    def test_aspect_does_not_crash(self):
        self.assertEqual(analyze(make_hand(index=True), aspect=1.33).pose, POINT)


class FilterAndConfigTests(unittest.TestCase):
    def test_one_euro_reduces_jitter_and_follows_step(self):
        f = OneEuro(1.2, 12.0)
        noisy = [0.5 + (0.004 if k % 2 else -0.004) for k in range(60)]
        out = [f(v, k / 30) for k, v in enumerate(noisy)]
        self.assertLess(max(out[30:]) - min(out[30:]), 0.008)
        for k in range(60, 90):
            y = f(0.9, k / 30)
        self.assertGreater(y, 0.85)

    def test_config_override_and_bad_values(self):
        import json, os, tempfile
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json")
        with open(p, "w") as fh:
            json.dump({"scroll_speed": 10, "natural_scroll": True, "bogus": 1, "beta": "x"}, fh)
        c = load_config(p)
        self.assertEqual((c.scroll_speed, c.natural_scroll), (10.0, True))
        self.assertEqual(c.beta, Config().beta)
        self.assertEqual(load_config(os.path.join(d, "missing.json")).camera_index, 0)


if __name__ == "__main__":
    unittest.main()
