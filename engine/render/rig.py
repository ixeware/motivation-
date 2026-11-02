"""Pill-style stick figure rig.

The look (from the reference): matte white figures, round head, capsule
torso, thick capsule limbs with round ends, soft glow, darker "back" limbs.
Our signature additions are drawn here too: the glowing CORE in the chest,
the BAND (blindfold) + glowing EYES, and CURSE MARKS.

Units: one unit = head radius. `s` = pixels per unit.
Angles are absolute, in degrees. 0 = limb points straight down.
  front view: positive = outward (away from body center), 180 = straight up
  side view:  positive = forward (towards facing), 180 = straight up
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import skia

from . import gfx

P = dict(neck=0.30, torso_len=2.35, torso_w=1.62, torso_w_side=1.10, limb=0.60,
         uarm=1.50, farm=1.42, thigh=1.70, shin=1.70, sh_in=0.30)

KEYS = ["lean", "head_tilt", "head_drop", "head_dx", "slump",
        "la1", "la2", "ra1", "ra2", "ll1", "ll2", "rl1", "rl2",
        "fingers", "head_front"]

BASE = dict(lean=0, head_tilt=0, head_drop=0, head_dx=0, slump=0,
            la1=6, la2=4, ra1=6, ra2=4, ll1=4, ll2=2, rl1=4, rl2=2,
            fingers=0, head_front=0)

# ----------------------------------------------------------------------------- poses
# Each pose is authored for one view. "view" is not interpolated (switches at 50%).
POSES: dict[str, dict] = {
    # ---- front view (classroom / close-up) ----
    "sit": dict(view="front", la1=10, la2=-30, ra1=10, ra2=-30),
    "sit_relaxed": dict(view="front", la1=14, la2=-8, ra1=14, ra2=-8),
    "sleep": dict(view="front", head_drop=2.15, slump=0.55, la1=38, la2=-96, ra1=38, ra2=-96, head_front=1),
    "head_in_hands": dict(view="front", head_drop=0.55, la1=72, la2=-143, ra1=72, ra2=-143),
    "hands_on_head": dict(view="front", la1=118, la2=-150, ra1=118, ra2=-150),
    "arms_up": dict(view="front", la1=150, la2=162, ra1=150, ra2=162, ll1=10, ll2=6, rl1=10, rl2=6),
    "fist_up": dict(view="front", la1=10, la2=-30, ra1=150, ra2=172),
    "stand": dict(view="front", la1=7, la2=4, ra1=7, ra2=4, ll1=5, ll2=2, rl1=5, rl2=2),
    "cast": dict(view="front", la1=8, la2=4, ra1=26, ra2=-160, fingers=1, ll1=5, ll2=2, rl1=5, rl2=2),
    "cast_sit": dict(view="front", la1=10, la2=-30, ra1=26, ra2=-160, fingers=1),
    "heaven": dict(view="front", la1=38, la2=46, ra1=150, ra2=172, fingers=1, ll1=5, ll2=2, rl1=5, rl2=2),
    "hands_out": dict(view="front", la1=52, la2=78, ra1=52, ra2=78, ll1=8, ll2=4, rl1=8, rl2=4),
    "hands_together": dict(view="front", la1=40, la2=-72, ra1=40, ra2=-72, ll1=6, ll2=3, rl1=6, rl2=3),
    "fire_right": dict(view="front", la1=10, la2=6, ra1=90, ra2=90, fingers=1, ll1=8, ll2=3, rl1=10, rl2=4),
    "fire_left": dict(view="front", la1=90, la2=90, ra1=10, ra2=6, fingers=1, ll1=10, ll2=4, rl1=8, rl2=3),
    "shrug": dict(view="front", la1=40, la2=110, ra1=40, ra2=110, ll1=5, ll2=2, rl1=5, rl2=2),
    "slumped": dict(view="front", head_drop=0.9, slump=0.25, la1=4, la2=0, ra1=4, ra2=0, ll1=4, ll2=2, rl1=4, rl2=2),

    # ---- side view (study / board / arena) ----
    "sit_side": dict(view="side", lean=6, la1=28, la2=80, ra1=34, ra2=86, ll1=90, ll2=2, rl1=88, rl2=-2),
    "write": dict(view="side", lean=30, head_tilt=14, la1=26, la2=84, ra1=40, ra2=98, ll1=90, ll2=4, rl1=88, rl2=0),
    "think_side": dict(view="side", lean=4, la1=28, la2=80, ra1=22, ra2=168, ll1=90, ll2=2, rl1=88, rl2=-2),
    "stand_side": dict(view="side", la1=-6, la2=-3, ra1=6, ra2=3, ll1=-3, ll2=-1, rl1=3, rl2=1),
    "board_write": dict(view="side", lean=4, la1=-6, la2=6, ra1=118, ra2=104, ll1=-4, ll2=-2, rl1=6, rl2=2),
    "point": dict(view="side", lean=2, la1=-6, la2=4, ra1=98, ra2=96, ll1=-4, ll2=-2, rl1=6, rl2=2),
    "stance": dict(view="side", lean=6, la1=32, la2=128, ra1=24, ra2=120, ll1=-20, ll2=-8, rl1=22, rl2=4),
    "punch": dict(view="side", lean=14, la1=34, la2=140, ra1=90, ra2=90, ll1=-24, ll2=-10, rl1=28, rl2=6),
    "punch_back": dict(view="side", lean=14, la1=90, la2=90, ra1=34, ra2=140, ll1=-24, ll2=-10, rl1=28, rl2=6),
    "guard": dict(view="side", lean=4, la1=36, la2=160, ra1=40, ra2=164, ll1=-18, ll2=-6, rl1=20, rl2=4),
    "hit": dict(view="side", lean=-22, head_tilt=-12, la1=-40, la2=-70, ra1=-20, ra2=-60, ll1=-26, ll2=-12, rl1=18, rl2=6),
    "kick": dict(view="side", lean=-16, la1=-30, la2=-10, ra1=40, ra2=120, ll1=-6, ll2=-2, rl1=96, rl2=92),
    "cast_side": dict(view="side", lean=0, la1=-8, la2=-2, ra1=84, ra2=94, fingers=1, ll1=-6, ll2=-2, rl1=8, rl2=2),
    "float_side": dict(view="side", lean=0, la1=-12, la2=-4, ra1=10, ra2=6, ll1=6, ll2=-6, rl1=18, rl2=4),
    "victory_side": dict(view="side", lean=-4, la1=150, la2=165, ra1=150, ra2=165, ll1=-4, ll2=-2, rl1=6, rl2=2),
    "kneel_side": dict(view="side", lean=18, head_tilt=20, la1=20, la2=30, ra1=30, ra2=60, ll1=0, ll2=-90, rl1=90, rl2=0),
}


def pose_dict(name_or_dict) -> dict:
    if isinstance(name_or_dict, dict):
        base = POSES.get(name_or_dict.get("base", ""), {})
        d = {**BASE, **base, **name_or_dict}
    else:
        d = {**BASE, **POSES.get(name_or_dict, POSES["stand"])}
    d.setdefault("view", "front")
    return d


def blend(a: dict, b: dict, t: float) -> dict:
    out = {}
    for k in KEYS:
        va, vb = a.get(k, BASE[k]), b.get(k, BASE[k])
        out[k] = va + (vb - va) * t
    out["view"] = a.get("view", "front") if t < 0.5 else b.get("view", "front")
    return out


# ----------------------------------------------------------------------------- modifiers

def apply_mods(p: dict, mods: dict, t: float) -> dict:
    """Procedural motion on top of a pose (breathing, walking, writing...)."""
    p = dict(p)
    ph = t * 2 * math.pi
    if mods.get("breath", 1):
        p["lean"] += math.sin(ph * 0.25) * 0.8
    if mods.get("writing"):
        amp = mods["writing"]
        p["ra2"] += math.sin(t * 15) * 7 * amp
        p["ra1"] += math.sin(t * 7.5) * 3 * amp
        p["head_tilt"] += math.sin(t * 3.1) * 2 * amp
    if mods.get("board"):
        amp = mods["board"]
        p["ra2"] += math.sin(t * 11) * 9 * amp
        p["ra1"] += math.sin(t * 5.5 + 1) * 6 * amp
    if mods.get("walk"):
        spd = mods["walk"]
        w = t * 2 * math.pi * 1.6 * spd
        sw = math.sin(w)
        p["ll1"] = 26 * sw
        p["rl1"] = -26 * sw
        p["ll2"] = p["ll1"] - max(0.0, 34 * math.sin(w + 1.3))
        p["rl2"] = p["rl1"] - max(0.0, 34 * math.sin(w + 1.3 + math.pi))
        if p.get("view") == "side":
            p["la1"] = -22 * sw
            p["ra1"] = 22 * sw
            p["la2"] = p["la1"] + 18
            p["ra2"] = p["ra1"] + 18
        p["lean"] += 3
    if mods.get("shake"):
        amp = mods["shake"]
        p["head_dx"] += math.sin(t * 40) * 0.05 * amp
        p["la2"] += math.sin(t * 37) * 4 * amp
        p["ra2"] += math.cos(t * 41) * 4 * amp
    if mods.get("fight"):
        amp = mods["fight"]
        p["lean"] += math.sin(t * 9) * 3 * amp
    return p


# ----------------------------------------------------------------------------- geometry


@dataclass
class Joints:
    hip: tuple
    neck: tuple
    head: tuple
    up: tuple
    tw: float
    tl: float
    sh: dict = field(default_factory=dict)   # 'l','r'
    el: dict = field(default_factory=dict)
    ha: dict = field(default_factory=dict)
    hp: dict = field(default_factory=dict)
    kn: dict = field(default_factory=dict)
    ft: dict = field(default_factory=dict)


def _dir(a_deg, side: str, view: str, facing: int):
    a = math.radians(a_deg)
    if view == "front":
        sx = -1 if side == "l" else 1
        return (sx * math.sin(a), math.cos(a))
    return (facing * math.sin(a), math.cos(a))


def solve(p: dict, x: float, y: float, s: float, facing: int = 1) -> Joints:
    view = p.get("view", "front")
    lean = math.radians(p["lean"])
    f = facing if view == "side" else 1
    up = (math.sin(lean) * f, -math.cos(lean))
    perp = (math.cos(lean), math.sin(lean) * f)
    tl = P["torso_len"] * (1 - 0.35 * p.get("slump", 0))
    tw = P["torso_w"] if view == "front" else P["torso_w_side"]
    hip = (x, y)
    neck = (x + up[0] * tl * s, y + up[1] * tl * s)
    ht = math.radians(p["lean"] + p["head_tilt"])
    hup = (math.sin(ht) * f, -math.cos(ht))
    hd = (P["neck"] + 1.0) * s
    head = (neck[0] + hup[0] * hd + p["head_dx"] * s * (f if view == "side" else 1),
            neck[1] + hup[1] * hd + p["head_drop"] * s)
    j = Joints(hip=hip, neck=neck, head=head, up=up, tw=tw, tl=tl)
    sh_base = (neck[0] - up[0] * P["sh_in"] * s, neck[1] - up[1] * P["sh_in"] * s)
    for side, sgn in (("l", -1), ("r", 1)):
        if view == "front":
            off = (tw / 2 - P["limb"] / 2 + 0.02) * s * sgn
            sh = (sh_base[0] + perp[0] * off, sh_base[1] + perp[1] * off)
            hoff = (tw / 2 - P["limb"] / 2 - 0.05) * s * sgn
            hp = (hip[0] + perp[0] * hoff, hip[1] + perp[1] * hoff)
        else:
            sh = sh_base
            hp = hip
        d1 = _dir(p[side + "a1"], side, view, facing)
        d2 = _dir(p[side + "a2"], side, view, facing)
        el = (sh[0] + d1[0] * P["uarm"] * s, sh[1] + d1[1] * P["uarm"] * s)
        ha = (el[0] + d2[0] * P["farm"] * s, el[1] + d2[1] * P["farm"] * s)
        d3 = _dir(p[side + "l1"], side, view, facing)
        d4 = _dir(p[side + "l2"], side, view, facing)
        kn = (hp[0] + d3[0] * P["thigh"] * s, hp[1] + d3[1] * P["thigh"] * s)
        ft = (kn[0] + d4[0] * P["shin"] * s, kn[1] + d4[1] * P["shin"] * s)
        j.sh[side], j.el[side], j.ha[side] = sh, el, ha
        j.hp[side], j.kn[side], j.ft[side] = hp, kn, ft
    return j


def ground_offset(p: dict, s: float, facing: int = 1) -> float:
    """Distance from hip to the lowest foot bottom (px). Used to stand on floors."""
    j = solve(p, 0, 0, s, facing)
    return max(j.ft["l"][1], j.ft["r"][1], j.kn["l"][1], j.kn["r"][1]) + P["limb"] * s / 2


# ----------------------------------------------------------------------------- drawing


@dataclass
class Look:
    color: object = "figure"
    alpha: float = 1.0
    core: object | None = None      # core color (our signature)
    core_amt: float = 1.0           # 0..1+ brightness
    glow: float = 0.22              # white outer glow strength
    band: float = 0.0               # blindfold band 0..1
    eyes: object | None = None      # glowing eye color
    eyes_amt: float = 0.0
    marks: float = 0.0              # curse marks 0..1
    legs: bool = True
    tint: object | None = None      # colour tint (afterimages / shadows)
    tint_amt: float = 0.0
    shadow_figure: bool = False     # draw as dark silhouette (shadow soldiers)


def _limb(c: skia.Canvas, a, b, w, pnt):
    c.drawLine(a[0], a[1], b[0], b[1], pnt)


def draw_figure(canvas: skia.Canvas, p: dict, x: float, y: float, s: float, *, facing: int = 1,
                look: Look | None = None, t: float = 0.0) -> Joints:
    look = look or Look()
    view = p.get("view", "front")
    j = solve(p, x, y, s, facing)
    lw = P["limb"] * s

    base = gfx.rgb(look.color)
    if look.tint is not None and look.tint_amt > 0:
        base = gfx.mix(base, look.tint, look.tint_amt)
    if look.shadow_figure:
        base = gfx.rgb("#0d0a14")
    back = gfx.shade(base, 0.74)
    sep = skia.Paint(AntiAlias=True, Color=gfx.col("black", 0.38), Style=skia.Paint.kStroke_Style,
                     StrokeWidth=lw + s * 0.16, StrokeCap=skia.Paint.kRound_Cap)
    if look.shadow_figure:
        sep.setColor(gfx.col("#7c3aed", 0.25))

    def lp(c_):
        return gfx.paint(c_, 1.0, stroke=lw)

    # bounds for the picture recorder
    pts = [j.head, j.hip, *j.ha.values(), *j.ft.values(), *j.el.values(), *j.kn.values()]
    minx = min(q[0] for q in pts) - 2.5 * s
    maxx = max(q[0] for q in pts) + 2.5 * s
    miny = min(q[1] for q in pts) - 2.5 * s
    maxy = max(q[1] for q in pts) + 2.5 * s
    rec = skia.PictureRecorder()
    c = rec.beginRecording(skia.Rect(minx, miny, maxx, maxy))

    def arm(side, color, with_sep):
        if with_sep:
            _limb(c, j.sh[side], j.el[side], lw, sep)
            _limb(c, j.el[side], j.ha[side], lw, sep)
        pnt = lp(color)
        _limb(c, j.sh[side], j.el[side], lw, pnt)
        _limb(c, j.el[side], j.ha[side], lw, pnt)
        if p.get("fingers", 0) > 0.5 and side == "r":
            # two raised fingers (hand sign)
            dx, dy = j.ha[side][0] - j.el[side][0], j.ha[side][1] - j.el[side][1]
            n = math.hypot(dx, dy) or 1
            tip = (j.ha[side][0] + dx / n * s * 0.55, j.ha[side][1] + dy / n * s * 0.55)
            c.drawLine(*j.ha[side], *tip, gfx.paint(color, 1, stroke=lw * 0.45))

    def leg(side, color, with_sep):
        if not look.legs:
            return
        if with_sep:
            _limb(c, j.hp[side], j.kn[side], lw, sep)
            _limb(c, j.kn[side], j.ft[side], lw, sep)
        pnt = lp(color)
        _limb(c, j.hp[side], j.kn[side], lw, pnt)
        _limb(c, j.kn[side], j.ft[side], lw, pnt)

    def torso():
        mid = ((j.hip[0] + j.neck[0]) / 2, (j.hip[1] + j.neck[1]) / 2)
        ang = math.degrees(math.atan2(j.up[0], -j.up[1]))
        L = j.tl * s + lw * 0.6
        W = j.tw * s
        c.save()
        c.translate(*mid)
        c.rotate(ang)
        gfx.rrect(c, -W / 2, -L / 2, W, L, W * 0.42, gfx.paint(base))
        c.restore()

    def head(with_sep=True):
        hr = s
        if with_sep:
            c.drawCircle(*j.head, hr + s * 0.09, gfx.paint("black", 0.38))
        c.drawCircle(*j.head, hr, gfx.paint(base))

    def core_dot():
        if look.core is None:
            return
        cp = (j.neck[0] - j.up[0] * s * 0.95, j.neck[1] - j.up[1] * s * 0.95)
        if view == "side":
            cp = (cp[0] + facing * j.tw * s * 0.18, cp[1])
        r = s * 0.2 * (0.85 + 0.25 * look.core_amt)
        c.drawCircle(*cp, r * 1.22, gfx.paint(gfx.mix(look.core, "black", 0.4), 0.35))
        c.drawCircle(*cp, r, gfx.paint(gfx.mix(look.core, "white", 0.18 * min(1, look.core_amt))))

    if view == "front":
        legc = gfx.shade(base, 0.86)
        leg("l", legc, False)
        leg("r", legc, False)
        torso()
        core_dot()
        if p.get("head_front", 0) > 0.5:
            arm("l", base, True)
            arm("r", base, True)
            head(True)
        else:
            head(p.get("head_drop", 0) > 0.05)
            arm("l", base, True)
            arm("r", base, True)
    else:
        arm("l", back, False)
        leg("l", back, False)
        torso()
        core_dot()
        head(True)
        leg("r", base, True)
        arm("r", base, True)

    # face details (signature attributes)
    hx, hy = j.head
    fx = facing * 0.38 * s if view == "side" else 0.0
    if look.marks > 0.01:
        mk = gfx.paint("#111111", look.marks, stroke=s * 0.08)
        for sgn in ((-1, 1) if view == "front" else (1,)):
            ex = hx + fx + sgn * s * 0.38 * (1 if view == "front" else 0.6)
            for k in range(2):
                yy = hy + s * (0.18 + k * 0.17)
                c.drawLine(ex - s * 0.18, yy, ex + s * 0.18, yy - s * 0.04, mk)
        c.drawLine(hx + fx - s * 0.12, hy - s * 0.58, hx + fx + s * 0.12, hy - s * 0.58, mk)
    if look.band > 0.01:
        bw = s * 0.42
        bp = gfx.paint("#0f0f12", look.band)
        c.save()
        c.clipPath(_circle_path(hx, hy, s))
        c.drawRect(skia.Rect(hx - s * 1.2, hy - s * 0.32 - bw / 2, hx + s * 1.2, hy - s * 0.32 + bw / 2), bp)
        c.restore()

    pic = rec.finishRecordingAsPicture()

    # --- composite: glow, body, shading
    a = look.alpha
    if a <= 0.001:
        return j
    if look.glow > 0 and not look.shadow_figure:
        gp = skia.Paint(ImageFilter=skia.ImageFilters.Blur(s * 0.35, s * 0.35))
        gp.setAlphaf(look.glow * a)
        canvas.saveLayer(skia.Rect(minx, miny, maxx, maxy), gp)
        canvas.drawPicture(pic)
        canvas.restore()
    lp_ = skia.Paint()
    lp_.setAlphaf(a)
    canvas.saveLayer(skia.Rect(minx, miny, maxx, maxy), lp_)
    canvas.drawPicture(pic)
    # soft top-light shading (only on the figure: SrcATop)
    sh = gfx.linear(0, miny, 0, maxy, [(0, "white", 0.0), (0.55, "black", 0.05), (1, "black", 0.22)])
    canvas.drawRect(skia.Rect(minx, miny, maxx, maxy),
                    skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcATop))
    canvas.restore()

    # additive glows drawn outside the layer
    if look.core is not None and look.core_amt > 0.05:
        cp = (j.neck[0] - j.up[0] * s * 0.95, j.neck[1] - j.up[1] * s * 0.95)
        if view == "side":
            cp = (cp[0] + facing * j.tw * s * 0.18, cp[1])
        vis = 1.0 - gfx.clamp(p.get("head_drop", 0) / 1.6) if p.get("head_front", 0) > 0.5 else 1.0
        gfx.glow_circle(canvas, *cp, s * 0.22, look.core, 0.75 * a * vis * min(1.6, look.core_amt),
                        spread=3.2 + look.core_amt)
    if look.eyes is not None and look.eyes_amt > 0.01:
        for sgn in ((-1, 1) if view == "front" else (1,)):
            ex = hx + fx + (sgn * s * 0.36 if view == "front" else 0)
            ey = hy - s * 0.3
            canvas.drawCircle(ex, ey, s * 0.075, gfx.paint(gfx.mix(look.eyes, "white", 0.5), look.eyes_amt * a))
            gfx.glow_circle(canvas, ex, ey, s * 0.07, look.eyes, look.eyes_amt * a, spread=3.0)
    if look.shadow_figure:
        # glowing eyes for shadow soldiers
        for sgn in ((-1, 1) if view == "front" else (1,)):
            ex = hx + fx + (sgn * s * 0.33 if view == "front" else 0)
            gfx.glow_circle(canvas, ex, hy - s * 0.2, s * 0.08, "#8b5cf6", 0.9 * a, spread=3)
            canvas.drawCircle(ex, hy - s * 0.2, s * 0.06, gfx.paint("#e9d5ff", a))
    return j


def _circle_path(x, y, r):
    pth = skia.Path()
    pth.addCircle(x, y, r)
    return pth


# ----------------------------------------------------------------------------- label / props on figures


def draw_label(canvas, x: float, head_y: float, s: float, text: str, *, a=1.0, level: float | None = None,
               level_c="violet", level_text: str | None = None, size_k=0.34, glitch: float = 0.0, t=0.0):
    """Mono, letter-spaced, uppercase label above the head + optional XP bar (signature)."""
    if not text or a <= 0.01:
        return head_y
    size = max(14.0, s * size_k)
    base_y = head_y - s * 1.32
    shown = text
    if glitch > 0:
        import random
        rnd = random.Random(int(t * 30))
        chars = list(text)
        for i in range(len(chars)):
            if rnd.random() < glitch * 0.5:
                chars[i] = rnd.choice("█▓▒░#@$%&*<>/\\|")
        shown = "".join(chars)
        dx = (rnd.random() - 0.5) * s * 0.3 * glitch
        gfx.draw_text(canvas, shown, x + dx + 3, base_y, size=size, c="#ff2a6d", a=a * 0.6 * glitch,
                      spacing=size * 0.16, face=gfx.MONO)
        gfx.draw_text(canvas, shown, x + dx - 3, base_y, size=size, c="#22d3ee", a=a * 0.6 * glitch,
                      spacing=size * 0.16, face=gfx.MONO)
    w = gfx.draw_text(canvas, shown, x, base_y, size=size, c="#f4f4f2", a=a, spacing=size * 0.16,
                      face=gfx.MONO, glow=size * 0.25)
    top = base_y - size
    if level is not None:
        bw = max(w, s * 1.6)
        bh = max(3.0, s * 0.055)
        by = base_y + size * 0.42
        gfx.rrect(canvas, x - bw / 2, by, bw, bh, bh / 2, gfx.paint("white", 0.16 * a))
        fill = gfx.clamp(level)
        if fill > 0:
            gfx.rrect(canvas, x - bw / 2, by, bw * fill, bh, bh / 2, gfx.paint(level_c, 0.95 * a))
            gfx.glow_circle(canvas, x - bw / 2 + bw * fill, by + bh / 2, bh * 1.2, level_c, 0.8 * a, spread=4)
        if level_text:
            gfx.draw_text(canvas, level_text, x + bw / 2 + size * 0.5, by + bh + size * 0.12, size=size * 0.62,
                          c=level_c, a=a, align="left", face=gfx.MONO, spacing=size * 0.08)
    return top


def draw_sheet(canvas, cx: float, bottom: float, s: float, mark: str, *, a=1.0, scale=1.0, rot=0.0,
               stamp_c="stamp", stamp_t=1.0):
    """Graded paper (reference prop): white sheet, red circled mark, grey lines."""
    if a <= 0.01:
        return
    w, h = s * 1.45 * scale, s * 1.9 * scale
    canvas.save()
    canvas.translate(cx, bottom - h / 2)
    canvas.rotate(rot)
    canvas.drawRect(skia.Rect(-w / 2 + s * 0.06, -h / 2 + s * 0.08, w / 2 + s * 0.06, h / 2 + s * 0.08),
                    gfx.paint("black", 0.35 * a, blur=s * 0.12))
    canvas.drawRect(skia.Rect(-w / 2, -h / 2, w / 2, h / 2), gfx.paint("paper", a))
    canvas.drawRect(skia.Rect(-w / 2, -h / 2, w / 2, h / 2), gfx.paint("#bdbab2", a * 0.6, stroke=s * 0.02))
    for i in range(5):
        yy = h * 0.12 + i * h * 0.075
        ln = w * (0.66 if i % 2 else 0.78)
        canvas.drawLine(-w * 0.38, yy, -w * 0.38 + ln, yy, gfx.paint("#9b9890", a * 0.8, stroke=s * 0.035))
    if stamp_t > 0:
        k = 1.0 + (1 - min(1.0, stamp_t)) * 0.8
        ra = s * 0.42 * scale * k
        sa = a * min(1.0, stamp_t * 1.4)
        cy = -h * 0.18
        canvas.drawCircle(0, cy, ra, gfx.paint(stamp_c, sa, stroke=s * 0.07 * scale))
        size = ra * (1.25 if len(mark) == 1 else 1.0)
        gfx.draw_text(canvas, mark, 0, cy + size * 0.36, size=size, face=gfx.DISPLAY, c=stamp_c, a=sa)
    canvas.restore()


def draw_zzz(canvas, x, y, s, t, a=1.0):
    for i in range(3):
        ph = (t * 0.5 + i / 3.0) % 1.0
        size = s * (0.3 + 0.25 * ph)
        xx = x + ph * s * 0.7
        yy = y - ph * s * 1.3
        al = a * math.sin(ph * math.pi)
        gfx.draw_text(canvas, "Z", xx, yy, size=size, face=gfx.MONO, c="#e9e9e9", a=al)
