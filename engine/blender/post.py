"""Post for Blender frames: bloom, manga impact frames, grain, crisp 2D text, encode with audio.

Text is drawn here (not in 3D) so labels and captions stay pixel-sharp and fixed on screen while the
3D camera shakes or punches in.
"""
from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = {False: ROOT / "assets" / "fonts" / "Silkscreen-Regular.ttf", True: ROOT / "assets" / "fonts" / "Silkscreen-Bold.ttf"}


@lru_cache(maxsize=64)
def font(size: int, bold: bool):
    return ImageFont.truetype(str(FONTS[bold]), size)


def draw_text(img: Image.Image, ops, scale: float = 1.0) -> Image.Image:
    """ops: (text, x, y, size, bold, (r,g,b), alpha, spacing); x, y are frame fractions (x = centre)."""
    if not ops:
        return img
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for text, x, y, size, bold, color, alpha, spacing in ops:
        if alpha <= 0:
            continue
        f = font(max(6, int(round(size * scale))), bold)
        sp = spacing * scale
        widths = [d.textlength(ch, font=f) for ch in text]
        total = sum(widths) + sp * (len(text) - 1)
        cx = x * W - total / 2
        cy = y * H
        a = int(255 * alpha)
        for ch, w in zip(text, widths):
            # soft dark halo so white text reads over bright 3D parts
            d.text((cx + 2 * scale, cy + 2 * scale), ch, font=f, fill=(0, 0, 0, int(a * 0.55)))
            d.text((cx, cy), ch, font=f, fill=(*color, a))
            cx += w + sp
    out = img.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def bloom(img: Image.Image, threshold=0.70, radius=7, strength=0.55) -> Image.Image:
    small = img.reduce(4)
    a = np.asarray(small).astype(np.float32) / 255
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mask = np.clip((lum - threshold) / (1 - threshold), 0, 1)[..., None]
    hi = Image.fromarray((a * mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    hi2 = hi.filter(ImageFilter.GaussianBlur(radius * 3))
    glow = (np.asarray(hi.resize(img.size, Image.BILINEAR)).astype(np.float32) * 0.6
            + np.asarray(hi2.resize(img.size, Image.BILINEAR)).astype(np.float32) * 0.6)
    base = np.asarray(img).astype(np.float32)
    out = base + glow * strength
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def impact(img: Image.Image, kind: str) -> Image.Image:
    a = np.asarray(img).astype(np.float32)
    if kind == "invert":      # manga impact frame: inverted, crushed to black/white
        lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        inv = 255 - lum
        inv = np.where(inv > 150, 255, np.where(inv > 70, inv * 0.5, 0))
        return Image.fromarray(np.repeat(inv[..., None], 3, 2).astype(np.uint8))
    if kind == "flash":
        return Image.fromarray(np.clip(a * 0.8 + 255 * 0.22, 0, 255).astype(np.uint8))
    return img


def add_glows(img: Image.Image, glows) -> Image.Image:
    """Additive soft light blooms: (x, y, radius, (r,g,b), strength) in frame fractions (radius of width)."""
    if not glows:
        return img
    W, H = img.size
    w, h = W // 4, H // 4
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    acc = np.zeros((h, w, 3), np.float32)
    for x, y, r, col, s in glows:
        if s <= 0:
            continue
        rr = max(1.0, r * w)
        d2 = ((xx - x * w) ** 2 + (yy - y * h) ** 2) / (rr * rr)
        g = np.exp(-d2 * 2.2) * 0.75 + np.exp(-d2 * 0.6) * 0.25
        acc += g[..., None] * np.array(col, np.float32)[None, None] * s
    up = np.asarray(Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    out = np.asarray(img).astype(np.float32) + up
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def grain(img: Image.Image, sigma=3.0, seed=0) -> Image.Image:
    rng = np.random.default_rng(seed)
    a = np.asarray(img).astype(np.float32)
    n = rng.normal(0, sigma, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(a + n, 0, 255).astype(np.uint8))


def compose(img, f, frames_dir, ops_fn, impacts=None, scale=1.0, bloom_strength=0.55):
    """Glows + bloom + text, or for an impact frame: text first, then the whole frame inverted."""
    kind = (impacts or {}).get(f)
    if kind == "invert":
        return impact(draw_text(img, ops_fn(f), scale), kind)
    gj = Path(frames_dir) / f"f_{f:04d}.json"
    if gj.exists():
        import json
        img = add_glows(img, json.loads(gj.read_text()))
    img = bloom(img, strength=bloom_strength)
    if kind:
        img = impact(img, kind)
    return draw_text(img, ops_fn(f), scale)


def finish(frames_dir, out_mp4, *, fps, frames, ops_fn, impacts=None, audio=None, size=(1080, 1920), crf=18,
           cover_frame=None, cover_out=None, bloom_strength=0.55):
    """Composite every rendered frame (PNG f_0001.png...) and encode to mp4 (with audio if given)."""
    frames_dir = Path(frames_dir)
    W, H = size
    ff = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ff, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if audio:
        cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out_mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    scale = W / 1080
    last = None
    for f in frames:
        p = frames_dir / f"f_{f:04d}.png"
        if p.exists():
            last = Image.open(p).convert("RGB")
        img = last.resize((W, H), Image.LANCZOS) if last.size != (W, H) else last
        img = compose(img, f, frames_dir, ops_fn, impacts, scale, bloom_strength)
        img = grain(img, 2.5, f)
        if cover_frame is not None and f == cover_frame and cover_out:
            img.save(cover_out)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode:
        raise RuntimeError("ffmpeg failed")
    return out_mp4
