"""Music analysis (beats / drop) and the final mix (music + SFX + ducking)."""
from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from . import sfx
from .sfx import SR


def load_audio(path: str | Path, start: float = 0.0, dur: float | None = None) -> np.ndarray:
    """Decode any audio/video file to float32 stereo @44.1k via ffmpeg."""
    ff = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ff, "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-i", str(path)]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def analyze(path: str | Path, max_dur: float = 240.0) -> dict:
    """Beats + the strongest 'drop' (biggest energy jump) of a track."""
    import librosa

    y = load_audio(path, 0, max_dur).mean(axis=1)
    y22 = librosa.resample(y, orig_sr=SR, target_sr=22050)
    tempo, beat_frames = librosa.beat.beat_track(y=y22, sr=22050)
    beats = librosa.frames_to_time(beat_frames, sr=22050).tolist()
    hop = 512
    rms = librosa.feature.rms(y=y22, hop_length=hop)[0]
    t = librosa.frames_to_time(np.arange(len(rms)), sr=22050, hop_length=hop)
    fps = 22050 / hop
    pre, post = int(2.0 * fps), int(1.0 * fps)
    best, drop = -1.0, None
    for i in range(pre, len(rms) - post):
        if t[i] < 4.0:
            continue
        gain = rms[i:i + post].mean() - rms[i - pre:i].mean()
        if gain > best:
            best, drop = gain, float(t[i])
    if drop is not None and beats:
        drop = min(beats, key=lambda b: abs(b - drop))
    return {"tempo": float(np.atleast_1d(tempo)[0]), "beats": beats, "drop": drop,
            "duration": float(len(y) / SR)}


def snap_shots(shots: list[dict], beats: list[float], tol: float = 0.28) -> None:
    """Move every cut to the nearest beat (in video time) if close enough."""
    if not beats:
        return
    bounds = []
    T = 0.0
    for sh in shots:
        T += float(sh.get("dur", 2.0))
        bounds.append(T)
    new = []
    for b in bounds[:-1]:
        nb = min(beats, key=lambda x: abs(x - b))
        new.append(nb if abs(nb - b) <= tol else b)
    new.append(bounds[-1])
    prev = 0.0
    for sh, b in zip(shots, new):
        d = max(0.4, b - prev)
        # shift events proportionally so they still fit
        sh["dur"] = round(d, 3)
        prev = prev + d


def mix(total: float, cues: list[tuple[float, str, float]], *, music: np.ndarray | None = None,
        music_gain: float = 0.8, sfx_gain: float = 1.0, duck: bool = True) -> np.ndarray:
    n = int(SR * total)
    out = np.zeros((n, 2), np.float32)
    duck_env = np.ones(n, np.float32)
    for t, name, gain in sorted(cues):
        x = sfx.make(name)
        i = int(t * SR)
        if i >= n or i < 0:
            continue
        x = x[: n - i]
        out[i:i + len(x)] += x * gain * sfx_gain
        d = sfx.DUCK.get(name, 0.0) * gain
        if duck and d > 0:
            L = int(SR * 0.6)
            env = 1 - d * 0.6 * np.exp(-np.linspace(0, 4, L))
            seg = duck_env[i:i + L]
            duck_env[i:i + L] = np.minimum(seg, env[: len(seg)])
    if music is not None and len(music):
        m = music[:n]
        if len(m) < n:
            m = np.concatenate([m, np.zeros((n - len(m), 2), np.float32)])
        fi = int(SR * 0.25)
        m[:fi] *= np.linspace(0, 1, fi)[:, None]
        fo = int(SR * 0.9)
        m[-fo:] *= np.linspace(1, 0, fo)[:, None]
        out += m * music_gain * duck_env[:, None]
    peak = np.max(np.abs(out)) or 1.0
    if peak > 0.98:
        out = np.tanh(out / peak * 1.3) * 0.95
    return out


def write_wav(path: str | Path, x: np.ndarray):
    x16 = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(x16.tobytes())


def mux(video: str | Path, audio: str | Path, out: str | Path):
    ff = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run([ff, "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
