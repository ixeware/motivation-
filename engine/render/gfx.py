"""Low-level drawing helpers on top of skia-python.

Everything in the engine draws through these helpers so the look stays
consistent: soft glows, mono letter-spaced labels, gradients, colors.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import skia

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "assets" / "fonts"

MONO = "JetBrainsMono-Bold.ttf"
MONO_MED = "JetBrainsMono-Medium.ttf"
MONO_XB = "JetBrainsMono-ExtraBold.ttf"
DISPLAY = "InterDisplay-Black.otf"
DISPLAY_BOLD = "InterDisplay-Bold.otf"
SANS = "Inter-Medium.otf"

# --------------------------------------------------------------------------- color

NAMED = {
    # brand palette: monochrome world + "core" accents
    "ink": "#0b0b0d",
    "bg": "#16171a",
    "wall": "#1d1e22",
    "floor": "#111214",
    "figure": "#eeeeec",
    "figure_dim": "#8d8e92",
    "paper": "#f3f1ea",
    "stamp": "#d42c2c",
    "violet": "#a855f7",
    "purple": "#9333ea",
    "cyan": "#38bdf8",
    "ice": "#7dd3fc",
    "gold": "#fbbf24",
    "red": "#ef4444",
    "crimson": "#dc2626",
    "blue": "#3b82f6",
    "green": "#34d399",
    "white": "#ffffff",
    "black": "#000000",
    "lamp": "#ffc978",
    "night": "#1e3a6e",
    "dawn": "#f2a65a",
}


def rgb(c) -> tuple[float, float, float]:
    """Accept '#rrggbb', a named color or an (r,g,b) tuple (0..1 or 0..255)."""
    if isinstance(c, str):
        c = NAMED.get(c, c)
        c = c.lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
    r, g, b = c[:3]
    if max(r, g, b) > 1.0:
        return (r / 255.0, g / 255.0, b / 255.0)
    return (float(r), float(g), float(b))


def col(c, a: float = 1.0) -> int:
    r, g, b = rgb(c)
    a = max(0.0, min(1.0, a))
    return skia.Color(int(r * 255), int(g * 255), int(b * 255), int(a * 255))


def mix(c1, c2, t: float):
    a, b = rgb(c1), rgb(c2)
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def shade(c, k: float):
    r, g, b = rgb(c)
    return (min(1, r * k), min(1, g * k), min(1, b * k))


# --------------------------------------------------------------------------- paints


def paint(c="white", a=1.0, *, stroke: float | None = None, cap_round=True, blur: float = 0.0,
          blend: skia.BlendMode | None = None, shader=None) -> skia.Paint:
    p = skia.Paint(AntiAlias=True)
    p.setColor(col(c, a))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap_round:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend is not None:
        p.setBlendMode(blend)
    if shader is not None:
        p.setShader(shader)
        p.setAlphaf(a)
    return p


ADD = skia.BlendMode.kPlus
SCREEN = skia.BlendMode.kScreen


def radial(cx, cy, r, stops: list[tuple[float, object, float]]):
    """stops: [(pos, color, alpha), ...]"""
    colors = [col(c, a) for _, c, a in stops]
    pos = [p for p, _, _ in stops]
    return skia.GradientShader.MakeRadial(skia.Point(cx, cy), max(r, 0.01), colors, pos)


def linear(x0, y0, x1, y1, stops: list[tuple[float, object, float]]):
    colors = [col(c, a) for _, c, a in stops]
    pos = [p for p, _, _ in stops]
    return skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)], colors, pos)


def glow_circle(canvas: skia.Canvas, x, y, r, c, a=1.0, spread=2.6):
    """Additive soft glow: a radial gradient that fades to transparent."""
    if a <= 0.001 or r <= 0:
        return
    R = r * spread
    sh = radial(x, y, R, [(0.0, c, a), (1.0 / spread, c, a * 0.55), (0.55, c, a * 0.15), (1.0, c, 0.0)])
    p = skia.Paint(AntiAlias=True, Shader=sh, BlendMode=ADD)
    canvas.drawCircle(x, y, R, p)


def orb(canvas, x, y, r, c, a=1.0, core="white"):
    """Bright energy sphere: colored halo + saturated body + hot white core."""
    if a <= 0.001 or r <= 0:
        return
    glow_circle(canvas, x, y, r * 1.2, c, 0.55 * a, spread=4.0)
    body = radial(x, y, r, [(0.0, core, a), (0.35, mix(core, c, 0.35), a), (0.8, c, a * 0.95), (1.0, c, 0.0)])
    canvas.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Shader=body, BlendMode=ADD))
    canvas.drawCircle(x, y, r * 0.35, paint(core, 0.9 * a, blur=r * 0.12))


# --------------------------------------------------------------------------- text


@lru_cache(None)
def typeface(name: str) -> skia.Typeface:
    p = FONTS / name
    tf = skia.Typeface.MakeFromFile(str(p)) if p.exists() else None
    return tf or skia.Typeface.MakeDefault()


@lru_cache(None)
def font(name: str, size: float) -> skia.Font:
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def text_width(s: str, fnt: skia.Font, spacing: float = 0.0) -> float:
    if not s:
        return 0.0
    return sum(fnt.measureText(ch) for ch in s) + spacing * (len(s) - 1)


def draw_text(canvas, s: str, x, y, *, size=28, face=MONO, c="white", a=1.0, spacing=0.0,
              align="center", glow: float = 0.0, glow_c=None, p: skia.Paint | None = None):
    """Draw (letter-spaced) text. y is the baseline. Returns the drawn width."""
    if not s or a <= 0.001:
        return 0.0
    fnt = font(face, size)
    w = text_width(s, fnt, spacing)
    if align == "center":
        x0 = x - w / 2
    elif align == "right":
        x0 = x - w
    else:
        x0 = x
    pnt = p or paint(c, a)
    if glow > 0:
        gp = paint(glow_c or c, a * 0.8, blur=glow)
        _draw_spaced(canvas, s, x0, y, fnt, spacing, gp)
    _draw_spaced(canvas, s, x0, y, fnt, spacing, pnt)
    return w


def _draw_spaced(canvas, s, x0, y, fnt, spacing, pnt):
    if spacing == 0:
        canvas.drawString(s, x0, y, fnt, pnt)
        return
    x = x0
    for ch in s:
        canvas.drawString(ch, x, y, fnt, pnt)
        x += fnt.measureText(ch) + spacing


def wrap(s: str, fnt: skia.Font, max_w: float, spacing=0.0) -> list[str]:
    out: list[str] = []
    for para in s.split("\n"):
        words, line = para.split(" "), ""
        for wd in words:
            cand = (line + " " + wd).strip()
            if text_width(cand, fnt, spacing) <= max_w or not line:
                line = cand
            else:
                out.append(line)
                line = wd
        out.append(line)
    return out


# --------------------------------------------------------------------------- shapes


def rrect(canvas, x, y, w, h, r, pnt):
    canvas.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), pnt)


def poly(points) -> skia.Path:
    path = skia.Path()
    if not points:
        return path
    path.moveTo(*points[0])
    for pt in points[1:]:
        path.lineTo(*pt)
    path.close()
    return path


def polyline(points) -> skia.Path:
    path = skia.Path()
    if not points:
        return path
    path.moveTo(*points[0])
    for pt in points[1:]:
        path.lineTo(*pt)
    return path


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])
