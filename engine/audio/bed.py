"""Procedural placeholder soundtrack (dark cinematic trap, ~100 BPM).

Used when no TikTok sound / file is given, so every render has music that is
safe to publish. Structure follows the video: quiet intro, tension, riser,
DROP exactly on the climax, outro.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from .sfx import SR, _lp, _noise

A_MINOR_EPIC = [  # i - VI - III - VII (Am F C G) as midi roots + minor/major triads
    (57, [0, 3, 7]), (53, [0, 4, 7]), (48, [0, 4, 7]), (55, [0, 4, 7]),
]


def _mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _kick(n_samples):
    t = np.arange(int(SR * 0.45)) / SR
    f = 45 + 110 * np.exp(-t * 28)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    return np.tanh(x * 2.5) * 0.9


def _hat(seed):
    t = np.arange(int(SR * 0.06)) / SR
    b, a = signal.butter(2, 7000 / (SR / 2), "high")
    return signal.lfilter(b, a, np.random.default_rng(seed).standard_normal(len(t))) * np.exp(-t * 70) * 0.25


def _snare(seed):
    t = np.arange(int(SR * 0.3)) / SR
    n = np.random.default_rng(seed).standard_normal(len(t))
    b, a = signal.butter(2, [1200 / (SR / 2), 8000 / (SR / 2)], "band")
    return (signal.lfilter(b, a, n) * np.exp(-t * 16) * 0.8 + np.sin(2 * np.pi * 185 * t) * np.exp(-t * 25) * 0.5)


def _pluck(freq, dur=0.9):
    t = np.arange(int(SR * dur)) / SR
    x = sum(np.sin(2 * np.pi * freq * k * t) / k ** 1.6 for k in range(1, 6))
    return x * np.exp(-t * 4.5) * 0.25


def _pad(chord_freqs, dur):
    t = np.arange(int(SR * dur)) / SR
    x = np.zeros_like(t)
    for f in chord_freqs:
        for det in (-0.12, 0.0, 0.11):
            x += signal.sawtooth(2 * np.pi * f * (1 + det / 100) * t)
    x = _lp(x, 1100)
    env = np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4)
    return x * env * 0.05


def make_bed(total: float, drop_at: float, bpm: float = 100.0, seed: int = 1) -> tuple[np.ndarray, list[float]]:
    """Returns (stereo float32 audio, beat times)."""
    n = int(SR * (total + 0.5))
    L = np.zeros(n)
    R = np.zeros(n)
    beat = 60.0 / bpm
    bar = beat * 4
    # shift grid so that a bar starts exactly on the drop
    offset = (drop_at % bar)
    beats = [offset + i * beat for i in range(-4, int(total / beat) + 4)]
    beats = [b for b in beats if 0 <= b <= total]

    def put(x, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= n or i + len(x) <= 0:
            return
        if i < 0:
            x = x[-i:]
            i = 0
        x = x[: n - i]
        L[i:i + len(x)] += x * gain * (1 - max(0, pan))
        R[i:i + len(x)] += x * gain * (1 + min(0, pan))

    kick = _kick(0)
    # chords per bar
    bar_t = offset - bar * 8
    ci = 0
    while bar_t < total:
        root, tri = A_MINOR_EPIC[ci % 4]
        freqs = [_mtof(root + iv) for iv in tri]
        after = bar_t >= drop_at - 1e-3
        pad_gain = 1.0 if after else 0.7
        put(_pad(freqs, bar + 0.2), bar_t, pad_gain)
        # sub bass
        t = np.arange(int(SR * bar)) / SR
        sub = np.sin(2 * np.pi * _mtof(root - 24) * t) * np.minimum(1, t / 0.05) * np.exp(-t * 0.6) * 0.35
        if after or bar_t >= drop_at - bar * 2:
            put(sub, bar_t, 1.0 if after else 0.5)
        # arpeggio plucks (8ths)
        for k in range(8):
            note = root + 12 + tri[k % 3] + (12 if k in (3, 7) else 0)
            g = 0.55 if not after else 0.8
            put(_pluck(_mtof(note)), bar_t + k * beat / 2, g, pan=(-0.3 if k % 2 else 0.3))
        bar_t += bar
        ci += 1
    for i, b in enumerate(beats):
        after = b >= drop_at - 1e-3
        if after:
            put(kick, b, 1.0)
            if i % 2 == 1:
                put(_snare(i), b, 0.8)
            put(_hat(i), b + beat / 2, 0.8, pan=0.2)
            put(_hat(i + 99), b, 0.5, pan=-0.2)
        elif b >= drop_at - bar * 2:
            if i % 2 == 0:
                put(kick, b, 0.6)
        else:
            if i % 4 == 0:
                put(kick, b, 0.35)
    # riser + impact into the drop
    rl = min(bar * 2, drop_at)
    if rl > 0.5:
        t = np.arange(int(SR * rl)) / SR
        nz = _lp(_noise(rl, seed), 9000) * (t / rl) ** 2.2 * 0.18
        put(nz, drop_at - rl, 1.0)
    t = np.arange(int(SR * 2.0)) / SR
    impact = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t * 1.5) + 30) / SR) * np.exp(-t * 2.2) * 0.7
    put(impact, drop_at, 1.0)
    x = np.stack([L, R], axis=1)
    x = np.tanh(x * 1.2) * 0.8
    # fades
    fi = int(SR * 0.4)
    x[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = int(SR * 1.2)
    end = int(SR * total)
    x[max(0, end - fo):end] *= np.linspace(1, 0, end - max(0, end - fo))[:, None]
    x[end:] = 0
    return x.astype(np.float32), beats
