"""Synthetic 21-point hands for testing without a camera."""
FIN = {"index": (5, 0.42, 0.65), "middle": (9, 0.50, 0.62),
       "ring": (13, 0.58, 0.65), "pinky": (17, 0.65, 0.70)}


def make_hand(index=False, middle=False, ring=False, pinky=False, thumb=False,
              pinch=None, dx=0.0, dy=0.0):
    p = [(0.0, 0.0)] * 21
    p[0] = (0.50, 0.90)
    p[1], p[2] = (0.44, 0.85), (0.38, 0.78)
    if thumb:
        p[3], p[4] = (0.34, 0.72), (0.30, 0.67)
    else:
        p[3], p[4] = (0.44, 0.74), (0.50, 0.74)
    up = {"index": index, "middle": middle, "ring": ring, "pinky": pinky}
    for name, (b, x, y) in FIN.items():
        p[b] = (x, y)
        p[b + 1] = (x, y - 0.10)
        if up[name]:
            p[b + 2], p[b + 3] = (x, y - 0.17), (x, y - 0.23)
        else:
            p[b + 2], p[b + 3] = (x, y - 0.04), (x, y + 0.03)
    if pinch:
        tip = p[FIN[pinch][0] + 3]
        p[4] = (tip[0] + 0.015, tip[1] + 0.01)
    return [(x + dx, y + dy) for x, y in p]
