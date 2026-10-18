# GestureMouse

Control your computer mouse with **both hands** through a webcam, using the same gestures you would use on a touchpad: move, click, drag, scroll, swipe and zoom.

Everything runs locally on your computer. No video is saved or sent anywhere.

## Features

- Two-hand tracking with 21 landmarks per hand (all five fingers)
- Move cursor, left / right / middle click, double click, drag and drop
- Vertical and horizontal scrolling
- Three-finger swipe to switch desktops
- Two-hand pinch zoom
- Smooth, jitter-free cursor using a One Euro filter
- Pause / resume gesture and a safe dry-run mode
- 24 automated unit tests that need no camera

## Gestures

Either hand can do any gesture. If both hands are active, the **Right hand** moves the cursor (configurable). A comfortable way to work is to point with one hand and click with the other.

| Gesture | Action |
|---|---|
| Index finger up, other fingers curled | Move cursor |
| Tap thumb + index | Left click (two quick taps = double click) |
| Hold thumb + index, then move | Drag and drop |
| Tap thumb + middle finger | Right click |
| Tap thumb + ring finger | Middle click |
| Index + middle up, move hand | Scroll (up/down and left/right) |
| Index + middle + ring up, swipe | Left/right: switch desktop, up: overview, down: show desktop |
| Both hands pinch thumb + index, spread or close | Zoom in / out |
| Both hands open palm for 1.5 seconds | Pause / resume |

A single open palm or a fist does nothing, so it is a safe resting pose.

## Requirements

- Python **3.9 to 3.12** (tested on 3.11)
- A webcam
- Windows, macOS or Linux (Linux needs an X11 session; Wayland blocks mouse control)

> **Why is mediapipe pinned to 0.10.21?** Newer MediaPipe releases removed the `solutions` API this project uses, and 0.10.21 has no builds for Python 3.13 or newer.

## Installation

### Windows (PowerShell)

```powershell
git clone https://github.com/YOUR_USERNAME/gesture-mouse.git
cd gesture-mouse
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run this first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### macOS / Linux

```bash
git clone https://github.com/YOUR_USERNAME/gesture-mouse.git
cd gesture-mouse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You can also run `run.bat` (Windows) or `./run.sh` (macOS/Linux). They create the environment, install the dependencies and start the app in one step.

**Permissions**
- macOS: allow *Camera* and *Accessibility* for Terminal in System Settings > Privacy & Security.
- Linux: install `python3-tk` and `python3-dev`, and use an X11 session.

## Usage

```bash
python main.py --selftest    # check dependencies, camera, FPS and unit tests
python main.py --dry-run     # real camera, actions are only logged (safe)
python main.py               # real mouse control
```

Other options:

```bash
python main.py --camera 1      # use a different camera
python main.py --no-preview    # run without the camera window (Ctrl+C to quit)
python main.py --verbose       # detailed logs
```

In the preview window: `q` or `Esc` quits, `p` pauses, `h` shows or hides the help text.

**Tip:** try `--dry-run` first to get used to the gestures before taking control of your real mouse.

## Configuration

Edit `config.json` to tune the tool. Delete any key to use its default.

| Setting | What it does |
|---|---|
| `camera_index` | Which camera to use (0, 1, 2...) |
| `primary_hand` | Hand that moves the cursor: `Right` or `Left` |
| `margin_x`, `margin_top`, `margin_bottom` | Size of the active area in the camera image |
| `min_cutoff`, `beta` | Smoothing: lower `min_cutoff` is steadier, higher `beta` is snappier |
| `pinch_engage`, `pinch_release` | How close the fingers must be to click |
| `drag_hold_s` | How long to hold a pinch before it becomes a drag |
| `scroll_speed`, `natural_scroll` | Scroll speed and direction |
| `swipe_distance` | How far to swipe to trigger a desktop switch |
| `zoom_speed` | Zoom sensitivity |

## How it works

1. **Capture**: a background thread reads the newest webcam frame (low latency).
2. **Detect**: MediaPipe Hands finds up to two hands and returns 21 landmarks each.
3. **Classify**: finger geometry decides which fingers are extended and which finger is pinching the thumb. Pinch distance is divided by hand size, so it works at any distance from the camera.
4. **Decide**: a state machine turns poses into actions (click vs drag timing, scroll, swipe, zoom, pause).
5. **Smooth and map**: a One Euro filter removes jitter, and the active camera region is mapped to the full screen.
6. **Act**: PyAutoGUI sends the mouse and keyboard events to the operating system.

Design details worth knowing:
- Pinch uses **hysteresis** (starts at 0.22, ends at 0.38) so it does not flicker.
- The cursor freezes while pinching and rewinds slightly on pinch start, so clicks land where you aimed.
- A fist is never counted as a click.
- If tracking drops during a drag, the button is released after 0.4 seconds so it never gets stuck.

## Project structure

```
gesture-mouse/
  main.py                 entry point (run, --dry-run, --selftest)
  config.json             tunable settings
  requirements.txt        pinned dependencies
  run.bat / run.sh        one-step launchers
  build.bat / build.sh    PyInstaller packaging
  gesture_mouse/
    camera.py             threaded webcam reader
    tracker.py            MediaPipe Hands wrapper
    gestures.py           pose and pinch detection (pure geometry)
    controller.py         gesture state machine
    smoothing.py          One Euro filter
    mouse_backend.py      real mouse (PyAutoGUI) and dry-run logger
    overlay.py            preview window drawing
    config.py             settings loader
  tests/                  unit tests
  docs/                   technical guide (PDF)
```

## Testing

The unit tests use synthetic hands, a fake mouse and a fake clock, so they need no camera:

```bash
python -m unittest discover -s tests -t . -v
```

Expected result: `Ran 24 tests ... OK`.

Full pre-deployment test plan: see `docs/GestureMouse_Technical_Guide.pdf`.

## Packaging

`build.bat` (Windows) or `build.sh` (macOS/Linux) creates a standalone app folder with PyInstaller. Build on each operating system you want to support.

## Troubleshooting

| Problem | Fix |
|---|---|
| `No matching distribution found for mediapipe==0.10.21` | Your Python is too new. Use Python 3.9 to 3.12 (for example `py -3.11 -m venv .venv`). |
| `Cannot open camera` | Close other apps using the camera, try `--camera 1`, and allow camera permission. |
| Cursor jitters | Improve lighting or lower `min_cutoff`. |
| Cursor lags | Raise `beta` or `min_cutoff`, or close heavy apps. |
| Clicks missed | Raise `pinch_engage` slightly and keep the whole hand visible. |
| Accidental clicks | Lower `pinch_engage` and keep fingers straight when pointing. |
| Scroll direction feels wrong | Set `natural_scroll` to `true` or `false`. |
| Nothing happens on macOS | Grant Accessibility permission, then restart the terminal. |
| Nothing happens on Linux | Use an X11 session instead of Wayland. |

## Limitations

- Uses one camera and 2D landmarks, so very fast motion or hands overlapping can lose tracking.
- Works best in bright, even lighting.
- Some elevated (administrator) windows ignore synthetic input unless the app is also run as administrator.
- Default thresholds may need tuning for different hand sizes and cameras.

## Future ideas

- On-screen calibration wizard
- Per-user profiles
- Custom gesture editor
- System tray interface
- Migration to the MediaPipe Tasks API for newer Python versions

## Credits

Built with [MediaPipe](https://github.com/google-ai-edge/mediapipe), [OpenCV](https://opencv.org/) and [PyAutoGUI](https://github.com/asweigart/pyautogui).

## License

MIT License.
