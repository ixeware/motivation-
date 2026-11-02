"""Easing curves (t in 0..1)."""
from __future__ import annotations

import math


def clamp01(t: float) -> float:
    return 0.0 if t < 0 else 1.0 if t > 1 else t


def linear(t):
    return clamp01(t)


def in_quad(t):
    t = clamp01(t)
    return t * t


def out_quad(t):
    t = clamp01(t)
    return 1 - (1 - t) * (1 - t)


def in_out_quad(t):
    t = clamp01(t)
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def in_cubic(t):
    t = clamp01(t)
    return t ** 3


def out_cubic(t):
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def in_out_cubic(t):
    t = clamp01(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def in_out_sine(t):
    t = clamp01(t)
    return -(math.cos(math.pi * t) - 1) / 2


def out_expo(t):
    t = clamp01(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def in_expo(t):
    t = clamp01(t)
    return 0.0 if t <= 0 else 2 ** (10 * t - 10)


def out_back(t, s=1.70158):
    t = clamp01(t)
    c3 = s + 1
    return 1 + c3 * (t - 1) ** 3 + s * (t - 1) ** 2


def out_elastic(t):
    t = clamp01(t)
    if t in (0.0, 1.0):
        return t
    c4 = (2 * math.pi) / 3
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


EASINGS = {
    "linear": linear,
    "in": in_quad,
    "out": out_quad,
    "inout": in_out_quad,
    "in_cubic": in_cubic,
    "out_cubic": out_cubic,
    "inout_cubic": in_out_cubic,
    "sine": in_out_sine,
    "out_expo": out_expo,
    "in_expo": in_expo,
    "back": out_back,
    "elastic": out_elastic,
}


def ease(name: str, t: float) -> float:
    return EASINGS.get(name, in_out_cubic)(t)


def window(t: float, start: float, end: float) -> float:
    """Normalized progress of t inside [start, end] (clamped)."""
    if end <= start:
        return 1.0 if t >= start else 0.0
    return clamp01((t - start) / (end - start))


def pulse(t: float, start: float, attack: float, release: float) -> float:
    """0 -> 1 -> 0 envelope."""
    if t < start:
        return 0.0
    if t < start + attack:
        return out_quad((t - start) / max(attack, 1e-6))
    return 1.0 - in_quad((t - start - attack) / max(release, 1e-6))
