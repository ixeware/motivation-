"""Set dressing: rooms, desks, lamp, window, clock, whiteboard, books, floor."""
from __future__ import annotations

import math
import random

import skia

from . import gfx


# ----------------------------------------------------------------------------- rooms


def room(canvas, W, H, horizon: float, *, wall_top="#24252a", wall_bot="#1a1b1f", floor_near="#0e0f11",
         floor_far="#17181b", light: float = 0.0, light_c="lamp", light_x=None, light_y=None):
    """Back wall + floor with a soft horizon line."""
    canvas.drawRect(skia.Rect(-W, -H, 2 * W, horizon),
                    skia.Paint(Shader=gfx.linear(0, -H * 0.2, 0, horizon,
                                                 [(0, wall_top, 1), (1, wall_bot, 1)])))
    canvas.drawRect(skia.Rect(-W, horizon, 2 * W, 2 * H),
                    skia.Paint(Shader=gfx.linear(0, horizon, 0, H * 1.1,
                                                 [(0, floor_far, 1), (1, floor_near, 1)])))
    canvas.drawRect(skia.Rect(-W, horizon - 3, 2 * W, horizon + 3), gfx.paint("black", 0.35, blur=4))
    if light > 0:
        lx = W / 2 if light_x is None else light_x
        ly = horizon if light_y is None else light_y
        gfx.glow_circle(canvas, lx, ly, W * 0.25, light_c, light * 0.25, spread=3.0)


def void_floor(canvas, W, H, horizon: float, *, tint="#1a1b20", spot=0.5, spot_c="white", spot_x=None):
    """Arena: near-black space with a reflective floor and a soft spotlight."""
    canvas.drawRect(skia.Rect(-W, -H, 2 * W, 2 * H), gfx.paint("#0b0b0e"))
    canvas.drawRect(skia.Rect(-W, -H, 2 * W, horizon),
                    skia.Paint(Shader=gfx.linear(0, 0, 0, horizon, [(0, "#08080a", 1), (1, tint, 1)])))
    canvas.drawRect(skia.Rect(-W, horizon, 2 * W, 2 * H),
                    skia.Paint(Shader=gfx.linear(0, horizon, 0, H, [(0, "#18191d", 1), (1, "#09090b", 1)])))
    sx = W / 2 if spot_x is None else spot_x
    if spot > 0:
        canvas.save()
        canvas.scale(1.0, 0.22)
        gfx.glow_circle(canvas, sx, (horizon + 140) / 0.22, W * 0.3, spot_c, spot * 0.22, spread=2.2)
        canvas.restore()
        # light shaft
        shaft = gfx.linear(0, -H * 0.1, 0, horizon + 100, [(0, spot_c, 0.0), (1, spot_c, spot * 0.07)])
        canvas.drawPath(gfx.poly([(sx - 90, -H * 0.1), (sx + 90, -H * 0.1), (sx + 380, horizon + 120),
                                  (sx - 380, horizon + 120)]),
                        skia.Paint(AntiAlias=True, Shader=shaft, BlendMode=gfx.ADD))


# ----------------------------------------------------------------------------- classroom props


def desk_front(canvas, cx, top_y, w, h, *, depth=0.22, shade_k=1.0, paper=True, paper_glow=0.6):
    """Front-facing school desk: lighter top face, dark front face."""
    d = h * depth
    top = gfx.poly([(cx - w / 2, top_y), (cx + w / 2, top_y), (cx + w / 2 - d * 0.35, top_y - d),
                    (cx - w / 2 + d * 0.35, top_y - d)])
    canvas.drawPath(top, gfx.paint(gfx.shade("#4a4c52", shade_k)))
    canvas.drawRect(skia.Rect(cx - w / 2, top_y, cx + w / 2, top_y + h),
                    skia.Paint(Shader=gfx.linear(0, top_y, 0, top_y + h,
                                                 [(0, gfx.shade("#2c2d32", shade_k), 1),
                                                  (1, gfx.shade("#1b1c20", shade_k), 1)])))
    canvas.drawRect(skia.Rect(cx - w / 2, top_y, cx + w / 2, top_y + h * 0.035),
                    gfx.paint(gfx.shade("#5a5c63", shade_k), 0.9))
    if paper:
        pw, ph = w * 0.36, d * 0.62
        py = top_y - d * 0.2
        pg = gfx.poly([(cx - pw / 2, py), (cx + pw / 2, py), (cx + pw / 2 - ph * 0.3, py - ph),
                       (cx - pw / 2 + ph * 0.3, py - ph)])
        canvas.drawPath(pg, gfx.paint("paper", 0.95 * shade_k))
        if paper_glow > 0:
            gfx.glow_circle(canvas, cx, py - ph / 2, pw * 0.4, "white", 0.12 * paper_glow * shade_k, spread=2.5)


def window(canvas, x, y, w, h, *, sky="night", glow=1.0, panes=(2, 3)):
    """Wall window. sky: color or 'night'/'dawn' named color."""
    sc = gfx.rgb(sky)
    canvas.drawRect(skia.Rect(x - 6, y - 6, x + w + 6, y + h + 6), gfx.paint("#0c0c0e"))
    canvas.drawRect(skia.Rect(x, y, x + w, y + h),
                    skia.Paint(Shader=gfx.linear(0, y, 0, y + h, [(0, gfx.shade(sc, 0.75), 1),
                                                                  (1, gfx.shade(sc, 1.15), 1)])))
    cols, rows = panes
    mp = gfx.paint("#0c0c0e", 1, stroke=max(4.0, w * 0.035), cap_round=False)
    for i in range(1, cols):
        xx = x + w * i / cols
        canvas.drawLine(xx, y, xx, y + h, mp)
    for i in range(1, rows):
        yy = y + h * i / rows
        canvas.drawLine(x, yy, x + w, yy, mp)
    if glow > 0:
        gfx.glow_circle(canvas, x + w / 2, y + h / 2, max(w, h) * 0.6, sc, 0.18 * glow, spread=2.6)


def wall_clock(canvas, x, y, r, t_hours: float, a=1.0):
    canvas.drawCircle(x, y, r * 1.08, gfx.paint("#0d0d10", a))
    canvas.drawCircle(x, y, r, gfx.paint("#d8d6d0", 0.92 * a))
    for i in range(12):
        ang = i / 12 * 2 * math.pi
        canvas.drawLine(x + math.sin(ang) * r * 0.78, y - math.cos(ang) * r * 0.78,
                        x + math.sin(ang) * r * 0.9, y - math.cos(ang) * r * 0.9,
                        gfx.paint("#333", a, stroke=r * 0.05))
    hh = (t_hours % 12) / 12 * 2 * math.pi
    mm = (t_hours % 1.0) * 2 * math.pi
    canvas.drawLine(x, y, x + math.sin(hh) * r * 0.5, y - math.cos(hh) * r * 0.5, gfx.paint("#111", a, stroke=r * 0.1))
    canvas.drawLine(x, y, x + math.sin(mm) * r * 0.78, y - math.cos(mm) * r * 0.78, gfx.paint("#111", a, stroke=r * 0.06))
    canvas.drawLine(x, y, x + math.sin(mm) * r * 0.78, y - math.cos(mm) * r * 0.78, gfx.paint("stamp", a * 0.7, stroke=r * 0.025))


def desk_side(canvas, x0, x1, top_y, floor_y, *, t=0.08, c="#2a2b30"):
    th = max(10.0, (x1 - x0) * t * 0.25)
    canvas.drawRect(skia.Rect(x0, top_y, x1, top_y + th), gfx.paint(gfx.shade(c, 1.4)))
    canvas.drawRect(skia.Rect(x0, top_y + th, x1, top_y + th * 1.6), gfx.paint(c))
    lw = th * 0.9
    for lx in (x0 + lw, x1 - lw):
        canvas.drawLine(lx, top_y + th, lx, floor_y, gfx.paint(gfx.shade(c, 0.85), 1, stroke=lw, cap_round=False))


def chair_side(canvas, x, seat_y, floor_y, s, facing=1):
    c = "#26272c"
    w = s * 2.6
    x0 = x - w * 0.5
    canvas.drawRect(skia.Rect(x0, seat_y, x0 + w, seat_y + s * 0.3), gfx.paint(gfx.shade(c, 1.3)))
    bx = x - facing * w * 0.55
    canvas.drawLine(bx, seat_y + s * 0.2, bx - facing * s * 0.25, seat_y - s * 2.6, gfx.paint(c, 1, stroke=s * 0.32))
    for lx in (x0 + s * 0.2, x0 + w - s * 0.2):
        canvas.drawLine(lx, seat_y + s * 0.3, lx, floor_y, gfx.paint(gfx.shade(c, 0.9), 1, stroke=s * 0.22, cap_round=False))


def desk_lamp(canvas, base_x, desk_y, s, *, facing=-1, on=1.0, flicker=0.0):
    """Side-view desk lamp. Returns (bulb_x, bulb_y) of the light source."""
    c = "#3a3b40"
    canvas.drawRect(skia.Rect(base_x - s * 0.9, desk_y - s * 0.22, base_x + s * 0.9, desk_y), gfx.paint(c))
    j1 = (base_x, desk_y - s * 0.2)
    j2 = (base_x + facing * -s * 0.6, desk_y - s * 3.2)
    j3 = (base_x + facing * s * 1.5, desk_y - s * 4.2)
    pnt = gfx.paint(c, 1, stroke=s * 0.22)
    canvas.drawLine(*j1, *j2, pnt)
    canvas.drawLine(*j2, *j3, pnt)
    head = gfx.poly([(j3[0] - facing * s * 0.25, j3[1] - s * 0.5), (j3[0] + facing * s * 1.2, j3[1] + s * 0.2),
                     (j3[0] + facing * s * 0.55, j3[1] + s * 1.0), (j3[0] - facing * s * 0.5, j3[1] + s * 0.25)])
    canvas.drawPath(head, gfx.paint("#4a4b51"))
    bulb = (j3[0] + facing * s * 0.45, j3[1] + s * 0.62)
    if on > 0:
        canvas.drawCircle(*bulb, s * 0.28, gfx.paint("#fff5e0", on))
    return bulb


def lamp_light(canvas, bulb, desk_y, s, *, facing=-1, on=1.0, c="lamp"):
    """Additive warm cone + pool of light (draw on top of the scene layer)."""
    if on <= 0:
        return
    bx, by = bulb
    cone = gfx.poly([(bx - facing * s * 0.2, by - s * 0.1), (bx + facing * s * 0.45, by),
                     (bx + facing * s * 5.5, desk_y + s * 0.2), (bx - facing * s * 3.8, desk_y + s * 0.2)])
    sh = gfx.linear(bx, by, bx, desk_y, [(0, c, 0.30 * on), (1, c, 0.06 * on)])
    canvas.drawPath(cone, skia.Paint(AntiAlias=True, Shader=sh, BlendMode=gfx.ADD,
                                     MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, s * 0.6)))
    gfx.glow_circle(canvas, bx, by, s * 0.5, c, 0.9 * on, spread=4.0)
    canvas.save()
    canvas.scale(1, 0.3)
    gfx.glow_circle(canvas, bx + facing * s * 0.8, desk_y / 0.3, s * 3.2, c, 0.35 * on, spread=1.8)
    canvas.restore()


def books(canvas, x, desk_y, s, n: int, seed=3):
    rnd = random.Random(seed)
    y = desk_y
    for i in range(n):
        h = s * (0.26 + rnd.random() * 0.12)
        w = s * (1.8 + rnd.random() * 0.6)
        off = (rnd.random() - 0.5) * s * 0.3
        shade_ = 0.8 + rnd.random() * 0.4
        canvas.drawRect(skia.Rect(x - w / 2 + off, y - h, x + w / 2 + off, y), gfx.paint(gfx.shade("#d9d6cf", shade_)))
        canvas.drawRect(skia.Rect(x - w / 2 + off, y - h, x - w / 2 + off + s * 0.12, y),
                        gfx.paint(gfx.shade("#55565c", shade_)))
        y -= h + 1


def whiteboard(canvas, x, y, w, h, lines: list[str], reveal: float, *, size=None, a=1.0):
    """Whiteboard with handwritten-ish equations revealed progressively (0..1)."""
    canvas.drawRect(skia.Rect(x - 10, y - 10, x + w + 10, y + h + 10), gfx.paint("#55575d", a))
    canvas.drawRect(skia.Rect(x, y, x + w, y + h),
                    skia.Paint(Shader=gfx.linear(x, y, x + w, y + h, [(0, "#fbfbf8", a), (1, "#dcdcd6", a)])))
    gfx.glow_circle(canvas, x + w / 2, y + h / 2, w * 0.45, "white", 0.06 * a, spread=2.0)
    if not lines:
        return
    size = size or h / (len(lines) + 2.5)
    total = sum(len(l_) for l_ in lines)
    budget = int(total * gfx.clamp(reveal))
    yy = y + size * 1.6
    for ln in lines:
        k = min(len(ln), budget)
        budget -= k
        if k > 0:
            gfx.draw_text(canvas, ln[:k], x + w * 0.1, yy, size=size, face=gfx.MONO_MED, c="#26272b", a=a,
                          align="left", spacing=size * 0.05)
        yy += size * 1.35


def floor_shadow(canvas, x, y, w, a=0.5):
    canvas.save()
    canvas.scale(1, 0.25)
    canvas.drawCircle(x, y / 0.25, w, gfx.paint("black", a, blur=w * 0.35))
    canvas.restore()


# ----------------------------------------------------------------------------- stage (reference: newer videos)


def stage_backdrop(canvas, W, H, floor_y: float, *, tint="#141518", haze=0.6):
    """Black stage: soft dark backdrop, glossy floor gradient, bright floor edge line."""
    canvas.drawRect(skia.Rect(-W, -H, 2 * W, floor_y),
                    skia.Paint(Shader=gfx.linear(0, -H * 0.2, 0, floor_y,
                                                 [(0, "#050506", 1), (0.6, "#0b0b0d", 1), (1, tint, 1)])))
    canvas.drawRect(skia.Rect(-W, floor_y, 2 * W, 2 * H),
                    skia.Paint(Shader=gfx.linear(0, floor_y, 0, floor_y + H * 0.45,
                                                 [(0, "#1d1e22", 1), (0.25, "#111215", 1), (1, "#060607", 1)])))
    # haze band right above the floor (light scattered by the spots)
    if haze > 0:
        canvas.drawRect(skia.Rect(-W, floor_y - 260, 2 * W, floor_y),
                        skia.Paint(Shader=gfx.linear(0, floor_y - 260, 0, floor_y,
                                                     [(0, "white", 0.0), (1, "white", 0.05 * haze)])))
    # glossy edge where the floor meets the dark
    canvas.drawRect(skia.Rect(-W, floor_y - 1.5, 2 * W, floor_y + 1.5), gfx.paint("white", 0.10))
    canvas.drawRect(skia.Rect(-W, floor_y - 6, 2 * W, floor_y + 6), gfx.paint("white", 0.05, blur=6))


_BEAM_CACHE: dict = {}


def _beam_image(w_top: float, w_bottom: float, height: float, tilt: float, color) -> tuple:
    """Pre-rendered soft beam (cached, 1/3 resolution). Returns (image, scale, pad)."""
    key = (int(w_top), int(w_bottom), int(height), int(tilt), str(color))
    hit = _BEAM_CACHE.get(key)
    if hit is not None:
        return hit
    q = 1 / 3
    pad = 60.0
    Wd = w_bottom + abs(tilt) * 2 + pad * 2
    surf = skia.Surface(max(4, int(Wd * q)), max(4, int((height + pad * 2) * q)))
    c = surf.getCanvas()
    c.clear(skia.ColorTRANSPARENT)
    c.scale(q, q)
    cx = Wd / 2
    top, bot = pad, pad + height
    for k, al in ((1.0, 0.035), (0.78, 0.045), (0.56, 0.05), (0.36, 0.055), (0.18, 0.05)):
        wt, wb = w_top * k, w_bottom * k
        pth = gfx.poly([(cx + tilt - wt / 2, top), (cx + tilt + wt / 2, top), (cx + wb / 2, bot), (cx - wb / 2, bot)])
        sh = gfx.linear(0, top, 0, bot, [(0, color, al * 1.6), (0.45, color, al), (1, color, al * 1.3)])
        c.drawPath(pth, skia.Paint(AntiAlias=True, Shader=sh,
                                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10 + 22 * k)))
    img = surf.makeImageSnapshot()
    _BEAM_CACHE[key] = (img, Wd, pad)
    if len(_BEAM_CACHE) > 64:
        _BEAM_CACHE.pop(next(iter(_BEAM_CACHE)))
    return _BEAM_CACHE[key]


def spotlight(canvas, x: float, floor_y: float, *, top_y: float = -200.0, w_top: float = 70.0,
              w_bottom: float = 420.0, a: float = 1.0, color="white", tilt: float = 0.0, t: float = 0.0,
              dust: bool = True, seed: int = 0):
    """Volumetric stage beam from above + light pool on the floor. Draw it behind the actors."""
    if a <= 0.01:
        return
    xt = x + tilt
    height = floor_y - top_y
    img, Wd, pad = _beam_image(w_top, w_bottom, height, tilt, color)
    p = skia.Paint(BlendMode=gfx.ADD)
    p.setAlphaf(min(1.0, a))
    canvas.drawImageRect(img, skia.Rect(x - Wd / 2, top_y - pad, x + Wd / 2, floor_y + pad),
                         skia.SamplingOptions(skia.FilterMode.kLinear), p)
    # lamp glare at the top
    gfx.glow_circle(canvas, xt, top_y + 40, w_top * 0.5, color, 0.35 * a, spread=3.0)
    # pool of light on the floor (ellipse) + a hot center
    canvas.save()
    canvas.scale(1, 0.16)
    gfx.glow_circle(canvas, x, floor_y / 0.16, w_bottom * 0.62, color, 0.28 * a, spread=1.7)
    gfx.glow_circle(canvas, x, floor_y / 0.16, w_bottom * 0.3, color, 0.22 * a, spread=1.6)
    canvas.restore()
    if dust:
        rnd = random.Random(seed + 101)
        for i in range(22):
            fy = rnd.random()
            yy = top_y + (floor_y - top_y) * ((fy + t * 0.03 * (0.5 + rnd.random())) % 1.0)
            frac = (yy - top_y) / max(1.0, floor_y - top_y)
            half = (w_top + (w_bottom - w_top) * frac) / 2 * 0.8
            xx = x + tilt * (1 - frac) + (rnd.random() - 0.5) * 2 * half + math.sin(t * 0.7 + i) * 6
            canvas.drawCircle(xx, yy, 1.2 + rnd.random() * 1.6, gfx.paint(color, 0.22 * a * rnd.random(),
                                                                          blend=gfx.ADD))


def pedestal(canvas, x: float, floor_y: float, w: float, h: float, *, a=1.0):
    gfx.rrect(canvas, x - w / 2, floor_y - h, w, h, 3, gfx.paint("#0d0d10", a))
    canvas.drawRect(skia.Rect(x - w / 2, floor_y - h, x + w / 2, floor_y - h + 2), gfx.paint("white", 0.18 * a))


def block_pile(canvas, x: float, floor_y: float, bw: float, bh: float, n: int, *, a=1.0, cols=3, dim=0.55):
    """Grey bricks waiting to be stacked (the 'supply')."""
    from .rig import OUTLINE_C
    rows = max(0, (n + cols - 1) // cols)
    k = 0
    for r in range(rows):
        for cc in range(cols):
            if k >= n:
                return
            bx = x + (cc - (cols - 1) / 2) * (bw + 3)
            by = floor_y - r * (bh + 3)
            gfx.rrect(canvas, bx - bw / 2 - 1.2, by - bh - 1.2, bw + 2.4, bh + 2.4, bh * 0.18, gfx.paint(OUTLINE_C, a))
            gfx.rrect(canvas, bx - bw / 2, by - bh, bw, bh, bh * 0.18,
                      gfx.paint(gfx.mix("#d6d6d2", "#55565b", dim), a))
            k += 1
