#!/usr/bin/env python3
"""GestureMouse - hand-gesture mouse control.

  python main.py              run (real mouse control)
  python main.py --dry-run    run with camera, but only LOG actions (safe test)
  python main.py --selftest   check dependencies, camera, tracker, unit tests
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from gesture_mouse import __version__
from gesture_mouse.config import load_config
from gesture_mouse.controller import Controller
from gesture_mouse.mouse_backend import LogMouse, PyAutoGuiMouse

log = logging.getLogger("gesture_mouse")


def base_dir() -> str:
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
        else os.path.dirname(os.path.abspath(__file__))


def parse_args():
    ap = argparse.ArgumentParser(description="Control the mouse with hand gestures.")
    ap.add_argument("--config", default=os.path.join(base_dir(), "config.json"))
    ap.add_argument("--camera", type=int, help="camera index (overrides config)")
    ap.add_argument("--dry-run", action="store_true", help="log actions, do not move the mouse")
    ap.add_argument("--no-preview", action="store_true", help="hide the camera window (Ctrl+C to quit)")
    ap.add_argument("--selftest", action="store_true", help="run pre-deployment checks")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    return ap.parse_args()


def selftest(cfg) -> int:
    ok = True

    def report(name, passed, detail=""):
        nonlocal ok
        ok &= bool(passed)
        print(f"[{'PASS' if passed else 'FAIL'}] {name} {detail}")

    report("Python 3.9-3.12", (3, 9) <= sys.version_info[:2] <= (3, 12), sys.version.split()[0])
    try:
        import cv2
        report("opencv import", True, cv2.__version__)
    except Exception as e:
        report("opencv import", False, str(e)); return 1
    try:
        import mediapipe as mp
        report("mediapipe legacy 'solutions' API", hasattr(mp, "solutions"),
               getattr(mp, "__version__", ""))
    except Exception as e:
        report("mediapipe import", False, str(e)); return 1
    try:
        m = PyAutoGuiMouse()
        report("pyautogui / screen access", True, f"screen {m.screen_size[0]}x{m.screen_size[1]}")
    except Exception as e:
        report("pyautogui / screen access", False, str(e))

    try:
        from gesture_mouse.camera import Camera
        from gesture_mouse.tracker import HandTracker
        cam = Camera(cfg.camera_index, cfg.frame_width, cfg.frame_height)
        tracker = HandTracker(cfg)
        seq, n, t0 = -1, 0, time.time()
        while n < 30 and time.time() - t0 < 5:
            frame, seq = cam.read(seq)
            if frame is not None:
                tracker.process(frame); n += 1
        fps = n / max(time.time() - t0, 1e-6)
        report("camera + tracker pipeline", n >= 30, f"{fps:.1f} FPS end-to-end (want >= 20)")
        report("frame size", True, f"{frame.shape[1]}x{frame.shape[0]}" if frame is not None else "n/a")
        cam.stop(); tracker.close()
    except Exception as e:
        report("camera + tracker pipeline", False, str(e))

    tests_dir = os.path.join(base_dir(), "tests")
    if os.path.isdir(tests_dir):
        import unittest
        suite = unittest.defaultTestLoader.discover(tests_dir, top_level_dir=base_dir())
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        report("unit tests", res.wasSuccessful(), f"{res.testsRun} run")
    print("\nSELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def run(args, cfg) -> int:
    import cv2
    from gesture_mouse import overlay
    from gesture_mouse.camera import Camera
    from gesture_mouse.tracker import HandTracker

    mouse = LogMouse() if args.dry_run else PyAutoGuiMouse()
    ctrl = Controller(cfg, mouse, mouse.screen_size)
    cam = Camera(cfg.camera_index, cfg.frame_width, cfg.frame_height)
    tracker = HandTracker(cfg)
    win = "GestureMouse"
    if cfg.preview:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        try:
            cv2.setWindowProperty(win, cv2.WND_PROP_TOPMOST, 1)
        except Exception:
            pass
    log.info("Running%s. Both open palms for %.1fs = pause/resume.",
             " (DRY-RUN)" if args.dry_run else "", cfg.toggle_hold_s)
    seq, fps, t_prev = -1, 0.0, time.time()
    try:
        while True:
            frame, seq = cam.read(seq)
            if frame is None:
                continue
            if cfg.mirror:
                frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            hands = tracker.process(frame)
            status = ctrl.process(hands, aspect=w / h)
            now = time.time()
            fps = 0.9 * fps + 0.1 / max(now - t_prev, 1e-6)
            t_prev = now
            if cfg.preview:
                tracker.draw(frame)
                overlay.draw(frame, cfg, status, fps, mouse.last_event, args.dry_run)
                cv2.imshow(win, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("p"):
                    ctrl.set_enabled(not ctrl.enabled)
                if key == ord("h"):
                    cfg.show_help = not cfg.show_help
    except KeyboardInterrupt:
        pass
    finally:
        ctrl.release_all()
        cam.stop()
        tracker.close()
        cv2.destroyAllWindows()
    return 0


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    cfg = load_config(args.config)
    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.no_preview:
        cfg.preview = False
    if args.selftest:
        return selftest(cfg)
    try:
        return run(args, cfg)
    except RuntimeError as e:
        log.error("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
