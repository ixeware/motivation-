"""Procedural sound effects (no samples, no licensing issues).

All functions return float32 stereo arrays shaped (n, 2) at SR.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import signal

SR = 44100


def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _env(n, attack=0.005, decay=0.3, curve=4.0):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.exp(-curve * np.maximum(0, t - attack) / max(decay, 1e-4))
    return a * d


def _lp(x, hz, order=2):
    b, a = signal.butter(order, min(hz / (SR / 2), 0.99), "low")
    return signal.lfilter(b, a, x)


def _hp(x, hz, order=2):
    b, a = signal.butter(order, min(hz / (SR / 2), 0.99), "high")
    return signal.lfilter(b, a, x)


def _bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], "band")
    return signal.lfilter(b, a, x)


def _stereo(x, width=0.0, seed=0):
    x = x.astype(np.float32)
    if width <= 0:
        return np.stack([x, x], axis=1)
    d = int(SR * 0.012 * width)
    r = np.concatenate([np.zeros(d, np.float32), x[:-d]]) if d > 0 else x
    return np.stack([x, 0.7 * x + 0.3 * r], axis=1)


def _norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def _sweep(f0, f1, dur, kind="exp"):
    t = _t(dur)
    if kind == "exp":
        f = f0 * (f1 / f0) ** (t / dur)
    else:
        f = f0 + (f1 - f0) * t / dur
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph)


def _noise(dur, seed=0):
    return np.random.default_rng(seed).standard_normal(int(SR * dur))


@lru_cache(None)
def make(name: str) -> np.ndarray:
    fn = SFX.get(name)
    if fn is None:
        return np.zeros((1, 2), np.float32)
    return fn()


def boom():
    dur = 2.2
    sub = _sweep(90, 32, dur) * _env(int(SR * dur), 0.004, 0.9, 3.0)
    n = _lp(_noise(dur, 1), 420) * _env(int(SR * dur), 0.002, 0.5, 5.0) * 2.2
    click = _hp(_noise(0.02, 2), 2000) * np.linspace(1, 0, int(SR * 0.02))
    x = sub * 1.2 + n
    x[: len(click)] += click * 0.6
    return _stereo(_norm(np.tanh(x * 1.6), 0.95), 0.6)


def hit():
    dur = 0.45
    body = _sweep(160, 55, dur) * _env(int(SR * dur), 0.001, 0.18, 4.0)
    n = _bp(_noise(dur, 3), 300, 5000) * _env(int(SR * dur), 0.001, 0.08, 6.0)
    return _stereo(_norm(np.tanh((body + n * 0.8) * 2.0), 0.95), 0.3)


def crack():
    dur = 0.6
    rng = np.random.default_rng(4)
    n = _hp(_noise(dur, 5), 1500)
    gate = (rng.random(int(SR * dur)) < 0.04).astype(float)
    gate = np.convolve(gate, np.ones(220) / 220, mode="same") * 30
    x = n * np.clip(gate, 0, 1) * _env(int(SR * dur), 0.001, 0.35, 3.0)
    buzz = signal.sawtooth(2 * np.pi * 95 * _t(dur)) * _env(int(SR * dur), 0.001, 0.2, 5.0) * 0.3
    return _stereo(_norm(x + buzz, 0.8), 0.8)


def whoosh():
    dur = 0.75
    n = _noise(dur, 6)
    env = np.sin(np.linspace(0, np.pi, int(SR * dur))) ** 2
    x = _bp(n, 400, 2600) * env
    x = x + _bp(n, 2000, 7000) * env ** 3 * 0.5
    return _stereo(_norm(x, 0.7), 1.0)


def riser():
    dur = 2.0
    t = _t(dur)
    tone = _sweep(160, 1400, dur) * 0.35 + _sweep(80, 700, dur) * 0.35
    n = _bp(_noise(dur, 7), 800, 6000) * (t / dur) ** 2
    env = (t / dur) ** 1.8
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * (4 + 14 * t / dur) * t)
    return _stereo(_norm((tone + n * 0.9) * env * trem, 0.7), 0.7)


def hum():
    dur = 3.0
    t = _t(dur)
    x = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate([55, 110.4, 165.2, 221]))
    x *= 0.7 + 0.3 * np.sin(2 * np.pi * 5.5 * t)
    env = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 0.8)
    return _stereo(_norm(x * env, 0.55), 0.5)


def drone():
    dur = 3.5
    t = _t(dur)
    x = sum(signal.sawtooth(2 * np.pi * f * t) for f in (73.4, 73.9, 110.0, 146.2))
    x = _lp(x, 900)
    env = np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 1.0)
    return _stereo(_norm(x * env, 0.45), 0.8)


def rumble():
    dur = 2.5
    x = _lp(_noise(dur, 8), 160, 4) * _env(int(SR * dur), 0.05, 1.4, 2.5)
    return _stereo(_norm(x, 0.8), 0.6)


def chime():
    dur = 1.4
    t = _t(dur)
    x = np.zeros_like(t)
    for f, d, a in ((1318.5, 0.0, 1.0), (1975.5, 0.09, 0.8), (2637.0, 0.18, 0.5)):
        tt = np.maximum(0, t - d)
        x += a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 4.0) * (t >= d)
    # tiny delay "reverb"
    for dl, g in ((0.11, 0.35), (0.23, 0.2)):
        k = int(SR * dl)
        x[k:] += x[:-k] * g
    return _stereo(_norm(x, 0.55), 0.9)


def clank():
    dur = 1.0
    t = _t(dur)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * dcy) for f, dcy in
            ((523, 3), (1187, 5), (1849, 6), (2633, 8), (3511, 10)))
    x[: int(SR * 0.02)] += _hp(_noise(0.02, 9), 2500) * 0.8
    thud = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 12)
    return _stereo(_norm(x * 0.6 + thud, 0.8), 0.5)


def paper():
    dur = 0.22
    x = _hp(_noise(dur, 10), 2500) * _env(int(SR * dur), 0.02, 0.1, 3.0)
    return _stereo(_norm(x, 0.35), 0.6)


def stamp():
    dur = 0.25
    t = _t(dur)
    x = np.sin(2 * np.pi * 140 * t) * np.exp(-t * 30) + _lp(_noise(dur, 11), 1500) * np.exp(-t * 40) * 0.6
    return _stereo(_norm(x, 0.6), 0.2)


def tick():
    dur = 0.05
    x = _hp(_noise(dur, 12), 3000) * _env(int(SR * dur), 0.001, 0.01, 5.0)
    return _stereo(_norm(x, 0.3))


def slash():
    dur = 0.35
    t = _t(dur)
    n = _noise(dur, 13)
    env = np.exp(-t * 14) * np.minimum(1, t / 0.01)
    x = _bp(n, 2500, 9000) * env + _sweep(3000, 700, dur) * env * 0.2
    return _stereo(_norm(x, 0.7), 1.0)


SFX = {
    "boom": boom, "hit": hit, "crack": crack, "whoosh": whoosh, "riser": riser, "hum": hum,
    "drone": drone, "rumble": rumble, "chime": chime, "clank": clank, "paper": paper,
    "stamp": stamp, "tick": tick, "slash": slash,
}

# how much each cue ducks the music (0..1)
DUCK = {"boom": 0.7, "hit": 0.45, "crack": 0.4, "rumble": 0.3, "slash": 0.3}
