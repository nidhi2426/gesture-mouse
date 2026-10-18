"""One Euro filter: low jitter when still, low lag when moving fast."""
import math


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuro:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.0, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._t = None
        self._raw = 0.0
        self._x = 0.0
        self._dx = 0.0

    def __call__(self, x: float, t: float) -> float:
        if self._t is None:
            self._t, self._raw, self._x, self._dx = t, x, x, 0.0
            return x
        dt = max(t - self._t, 1e-3)
        dx = (x - self._raw) / dt
        a_d = _alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1.0 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = _alpha(cutoff, dt)
        self._x = a * x + (1.0 - a) * self._x
        self._raw, self._t = x, t
        return self._x
