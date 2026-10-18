# GestureMouse

Control your mouse with both hands through a webcam, using touchpad-style gestures.
Python + MediaPipe Hands + OpenCV + PyAutoGUI. Runs 100% locally - no video leaves your PC.

## Quick start
Windows: double-click `run.bat`  |  macOS/Linux: `./run.sh`
(Python 3.9-3.12 required. Always try `--dry-run` first.)

```
python main.py --selftest   # check deps, camera, FPS, unit tests
python main.py --dry-run    # camera + preview, actions only LOGGED
python main.py              # real mouse control
```
Run unit tests alone: `python -m unittest discover -s tests -t . -v`

## Gestures (either hand; Right hand drives the cursor if both are active)
| Gesture | Action |
|---|---|
| Index finger up, others curled | Move cursor |
| Tap thumb + index | Left click (two quick taps = double click) |
| Hold thumb + index, then move | Drag and drop |
| Tap thumb + middle | Right click |
| Tap thumb + ring | Middle click |
| Index + middle up, move hand | Scroll (vertical / horizontal) |
| Index + middle + ring up, swipe | Switch desktop left/right, up = overview, down = show desktop |
| Both hands pinch thumb + index, move apart/together | Zoom in / out |
| Both hands open palm for 1.5 s | Pause / resume (open palm alone = safe rest pose) |

Tip: use one hand to move and the other to click.
Preview keys: `q` quit, `p` pause, `h` help.

## Settings
Edit `config.json` (sensitivity, smoothing, thresholds, natural scroll, primary hand, camera).
Full reference and the pre-deployment test plan are in the PDF guide.

## Packaging
`build.bat` / `build.sh` creates a standalone folder with PyInstaller (build on each target OS).

## Permissions
macOS: allow Camera and Accessibility (System Settings > Privacy & Security) for Terminal/the app.
Linux: X11 session required (Wayland blocks synthetic input). Windows: no special setup.
