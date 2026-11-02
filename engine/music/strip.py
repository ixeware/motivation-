"""Get a clean song out of a TikTok edit, and fit its beat grid.

Typical case: our render was uploaded to the TikTok editor, a sound was added
and the edit was exported with the original sound still underneath. To re-cut
the video on that song we need the song alone:

  python -m engine music strip edit.mp4 --ours output/<slug>/final.mp4 --out assets/music/user/song.wav
  python -m engine music grid assets/music/user/song.wav

strip(): aligns our original mix to the edit (AAC delay), fits a short FIR
filter (TikTok's gain / EQ) by least squares and subtracts it.
grid(): finds the beat period and phase that best match the percussive onsets
and reports the bar and 4-bar phrase starts (good cut / climax points).
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100


def _load(path) -> np.ndarray:
    from ..audio.mix import load_audio
    return load_audio(path).astype(np.float64)


def strip(edit: str | Path, ours: str | Path, out: str | Path, *, taps: int = 96) -> dict:
    from scipy import signal
    up, mine = _load(edit), _load(ours)
    n = min(len(up), len(mine))
    up, mine = up[:n], mine[:n]
    # delay between our mix and its copy inside the edit (AAC priming etc.)
    w = slice(SR * 2, min(n, SR * 12))
    a, b = up[w].mean(1), mine[w].mean(1)
    xc = signal.correlate(a, b, mode="full", method="fft")
    lag = int(np.argmax(np.abs(xc)) - (len(b) - 1))
    clean = np.zeros_like(up)
    report = {"lag_ms": round(lag / SR * 1000, 2), "channels": []}
    half = taps // 2
    for ch in range(up.shape[1]):
        x = np.roll(mine[:, ch], lag)
        if lag < 0:
            x[lag:] = 0
        elif lag > 0:
            x[:lag] = 0
        shifts = range(-half, half)
        X = np.stack([np.roll(x, k) for k in shifts], axis=1)[SR:-SR:3]
        y = up[SR:-SR:3, ch]
        h, *_ = np.linalg.lstsq(X, y, rcond=None)
        est = sum(h[i] * np.roll(x, k) for i, k in enumerate(shifts))
        clean[:, ch] = up[:, ch] - est
        report["channels"].append({
            "corr_before": round(float(np.corrcoef(up[:, ch], x)[0, 1]), 4),
            "corr_after": round(float(np.corrcoef(clean[:, ch], x)[0, 1]), 4),
        })
    peak = float(np.max(np.abs(clean))) or 1.0
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(clean / max(1.0, peak), -1, 1) * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(clean.shape[1])
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    report.update({"out": str(out), "seconds": round(n / SR, 3)})
    return report


def grid(path: str | Path, *, bpm_min: float = 70, bpm_max: float = 180) -> dict:
    """Beat period + phase that best fit the percussive onsets; bar and phrase starts."""
    import librosa
    y = _load(path).mean(1).astype(np.float32)
    y = librosa.resample(y, orig_sr=SR, target_sr=22050)
    hop = 128
    env = librosa.onset.onset_strength(y=librosa.effects.percussive(y), sr=22050, hop_length=hop)
    tempo, _ = librosa.beat.beat_track(y=y, sr=22050)
    p0 = 60.0 / float(np.atleast_1d(tempo)[0])
    dur = len(y) / 22050

    def score(P, t0):
        ts = t0 + P * np.arange(int((dur - t0) / P))
        idx = np.clip(np.round(ts * 22050 / hop).astype(int), 0, len(env) - 1)
        return float(env[idx].sum())

    best = (-1.0, p0, 0.0)
    for P in np.arange(max(60 / bpm_max, p0 * 0.98), min(60 / bpm_min, p0 * 1.02), 0.00005):
        for t0 in np.arange(0.0, P, 0.002):
            sc = score(P, t0)
            if sc > best[0]:
                best = (sc, P, t0)
    _, P, t0 = best
    beats = [round(float(t0 + k * P), 4) for k in range(int((dur - t0) / P) + 1)]
    return {"t0": round(float(t0), 4), "period": round(float(P), 5), "bpm": round(60 / P, 3),
            "bars": beats[::4], "phrases": beats[::16], "duration": round(dur, 3)}
