"""Preview-window overlay (status text, active region, cheat sheet)."""
import cv2

GREEN, RED, WHITE, YELLOW = (80, 220, 80), (60, 60, 240), (255, 255, 255), (0, 220, 255)

HELP = [
    "Index up: move  |  Pinch thumb+index: click (hold = drag)",
    "Thumb+middle: right click  |  Thumb+ring: middle click",
    "Index+middle up: scroll  |  3 fingers up: swipe",
    "Both hands pinch: zoom  |  Both open palms 1.5s: pause",
    "Keys: q quit | p pause | h help",
]


def _text(img, s, xy, color=WHITE, scale=0.5):
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, s, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def draw(frame, cfg, status: dict, fps: float, last_event: str, dry_run: bool) -> None:
    h, w = frame.shape[:2]
    x0, x1 = int(cfg.margin_x * w), int((1 - cfg.margin_x) * w)
    y0, y1 = int(cfg.margin_top * h), int((1 - cfg.margin_bottom) * h)
    cv2.rectangle(frame, (x0, y0), (x1, y1), YELLOW, 1)

    enabled = status.get("enabled", True)
    tag = ("DRY-RUN " if dry_run else "") + ("ACTIVE" if enabled else "PAUSED")
    _text(frame, f"{tag}   {fps:4.1f} FPS", (8, 20), GREEN if enabled else RED, 0.6)
    y = 42
    for label, (pose, pinch, drag) in status.get("hands", {}).items():
        extra = (f" pinch:{pinch}" if pinch else "") + (" DRAG" if drag else "")
        mark = "*" if label == status.get("cursor_hand") else " "
        _text(frame, f"{mark}{label}: {pose}{extra}", (8, y))
        y += 18
    if status.get("zoom"):
        _text(frame, "ZOOM", (8, y), YELLOW, 0.6)
    if last_event:
        _text(frame, last_event, (8, h - 10), GREEN)
    if cfg.show_help:
        for i, line in enumerate(HELP):
            _text(frame, line, (8, h - 30 - 16 * (len(HELP) - i)), WHITE, 0.4)
