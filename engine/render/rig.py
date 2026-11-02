"""Pill-style stick figure rig.

The look (from the reference account): matte white figures, round head,
capsule torso, capsule limbs with round ends, a thin dark outline around every
part (so overlapping limbs read clearly), soft white glow, darker back limbs.

Builds:
  chunky - the classroom reference (big head, wide torso)
  slim   - the newer stage / track videos (smaller head, long limbs)

Our signature additions are drawn here too: the glowing CORE in the chest,
the BAND (blindfold) + glowing EYES, CURSE MARKS, the FLAME on the head and
the DIM state for archetypes that gave up.

Units: one unit = head radius. `s` = pixels per unit.
Angles are absolute, in degrees. 0 = limb points straight down.
  front view: positive = outward (away from body center), 180 = straight up
  side view:  positive = forward (towards facing), 180 = straight up
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import skia

from . import gfx

BUILDS = {
    "chunky": dict(neck=0.30, torso_len=2.35, torso_w=1.62, torso_w_side=1.10, limb=0.60,
                   uarm=1.50, farm=1.42, thigh=1.70, shin=1.70, sh_in=0.30),
    "slim": dict(neck=0.40, torso_len=3.25, torso_w=1.16, torso_w_side=0.90, limb=0.54,
                 uarm=2.0, farm=1.9, thigh=2.35, shin=2.3, sh_in=0.30),
}
P = BUILDS["chunky"]

KEYS = ["lean", "head_tilt", "head_drop", "head_dx", "slump",
        "la1", "la2", "ra1", "ra2", "ll1", "ll2", "rl1", "rl2",
        "fingers", "head_front"]

BASE = dict(lean=0, head_tilt=0, head_drop=0, head_dx=0, slump=0,
            la1=6, la2=4, ra1=6, ra2=4, ll1=4, ll2=2, rl1=4, rl2=2,
            fingers=0, head_front=0)

_SQUAT = dict(ll1=64, ll2=-6, rl1=64, rl2=-6)

# ----------------------------------------------------------------------------- poses
# Each pose is authored for one view. "view" is not interpolated (switches at 50%).
POSES: dict[str, dict] = {
    # ---- front view (classroom / close-up / stage) ----
    "sit": dict(view="front", la1=10, la2=-30, ra1=10, ra2=-30),
    "sit_relaxed": dict(view="front", la1=14, la2=-8, ra1=14, ra2=-8),
    "sleep": dict(view="front", head_drop=2.15, slump=0.55, la1=38, la2=-96, ra1=38, ra2=-96, head_front=1),
    "head_in_hands": dict(view="front", head_drop=0.55, la1=72, la2=-143, ra1=72, ra2=-143),
    "hands_on_head": dict(view="front", la1=118, la2=-150, ra1=118, ra2=-150),
    "arms_up": dict(view="front", la1=150, la2=162, ra1=150, ra2=162, ll1=10, ll2=6, rl1=10, rl2=6),
    "fist_up": dict(view="front", la1=10, la2=-30, ra1=150, ra2=172),
    "stand": dict(view="front", la1=7, la2=4, ra1=7, ra2=4, ll1=5, ll2=2, rl1=5, rl2=2),
    "stand_proud": dict(view="front", la1=48, la2=-78, ra1=48, ra2=-78, ll1=9, ll2=4, rl1=9, rl2=4),
    "cast": dict(view="front", la1=8, la2=4, ra1=26, ra2=-160, fingers=1, ll1=5, ll2=2, rl1=5, rl2=2),
    "cast_sit": dict(view="front", la1=10, la2=-30, ra1=26, ra2=-160, fingers=1),
    "heaven": dict(view="front", la1=38, la2=46, ra1=150, ra2=172, fingers=1, ll1=5, ll2=2, rl1=5, rl2=2),
    "hands_out": dict(view="front", la1=52, la2=78, ra1=52, ra2=78, ll1=8, ll2=4, rl1=8, rl2=4),
    "hands_together": dict(view="front", la1=40, la2=-72, ra1=40, ra2=-72, ll1=6, ll2=3, rl1=6, rl2=3),
    "fire_right": dict(view="front", la1=10, la2=6, ra1=90, ra2=90, fingers=1, ll1=8, ll2=3, rl1=10, rl2=4),
    "fire_left": dict(view="front", la1=90, la2=90, ra1=10, ra2=6, fingers=1, ll1=10, ll2=4, rl1=8, rl2=3),
    "shrug": dict(view="front", la1=40, la2=110, ra1=40, ra2=110, ll1=5, ll2=2, rl1=5, rl2=2),
    "slumped": dict(view="front", head_drop=0.9, slump=0.25, la1=4, la2=0, ra1=4, ra2=0, ll1=4, ll2=2, rl1=4, rl2=2),
    # stacking blocks: pile on the left, tower on the right (mirror for the other side)
    "pick_l": dict(view="front", lean=-14, head_drop=0.25, la1=26, la2=8, ra1=-34, ra2=-22,
                   ll1=60, ll2=-12, rl1=48, rl2=-16),
    "place_r": dict(view="front", lean=9, la1=-116, la2=-148, ra1=124, ra2=154, ll1=4, ll2=2, rl1=10, rl2=5),
    "carry": dict(view="front", la1=30, la2=-62, ra1=30, ra2=-62, ll1=6, ll2=3, rl1=6, rl2=3),
    "squat": dict(view="front", la1=34, la2=-12, ra1=34, ra2=-12, **_SQUAT),
    "squat_rest": dict(view="front", head_tilt=0, la1=34, la2=-14, ra1=58, ra2=-150, **_SQUAT),
    "squat_despair": dict(view="front", head_drop=0.35, la1=112, la2=-150, ra1=112, ra2=-150, **_SQUAT),
    "squat_slump": dict(view="front", head_drop=0.55, slump=0.15, la1=12, la2=-24, ra1=12, ra2=-24, **_SQUAT),
    "kneel_front": dict(view="front", head_drop=0.2, la1=14, la2=-10, ra1=14, ra2=-10,
                        ll1=40, ll2=-30, rl1=40, rl2=-30),
    # seated struggle (exam): thinking, scratching the head, stretching
    "sit_think": dict(view="front", head_dx=0.06, la1=10, la2=-30, ra1=46, ra2=-152),
    "sit_scratch": dict(view="front", la1=10, la2=-30, ra1=104, ra2=-140),
    "sit_stretch": dict(view="front", la1=150, la2=168, ra1=150, ra2=168),

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


def mirror(p: dict) -> dict:
    """Mirror a front-view pose left <-> right."""
    q = dict(p)
    for a, b in (("la1", "ra1"), ("la2", "ra2"), ("ll1", "rl1"), ("ll2", "rl2")):
        q[a], q[b] = p.get(b, BASE[b]), p.get(a, BASE[a])
    q["lean"] = -p.get("lean", 0)
    q["head_dx"] = -p.get("head_dx", 0)
    return q


POSES["pick_r"] = mirror(POSES["pick_l"])
POSES["place_l"] = mirror(POSES["place_r"])


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
    if mods.get("look_around"):
        amp = mods["look_around"]
        v = look_phase(t, mods.get("look_rate", 1.3), mods.get("look_offset", 0.0))
        p["head_dx"] += 0.34 * amp * v
        p["lean"] += 5 * amp * v
    if mods.get("pant"):
        amp = mods["pant"]
        p["head_drop"] += (0.5 + 0.5 * math.sin(t * 9)) * 0.08 * amp
        p["slump"] += (0.5 + 0.5 * math.sin(t * 9)) * 0.04 * amp
    return p


def look_phase(t: float, rate: float = 1.3, offset: float = 0.0) -> float:
    """-1 (looking left) .. +1 (looking right): quick glances with short holds (comparing).
    offset (radians): pi/2 puts the extremes exactly on t = 0, 1/(2 rate), ... (use it to land on beats)."""
    v = math.sin(t * rate * 2 * math.pi + offset)
    return math.copysign(abs(v) ** 0.35, v)


def stack_pose(phase: float, side: int = 1) -> tuple[dict, bool]:
    """One block-stacking cycle. side=1: tower on the right. Returns (pose, carrying)."""
    pick = pose_dict("pick_l" if side > 0 else "pick_r")
    place = pose_dict("place_r" if side > 0 else "place_l")
    ph = phase % 1.0
    if ph < 0.38:            # go down to the pile
        k = _smooth(ph / 0.38)
        return blend(place, pick, k), False
    if ph < 0.50:            # grab
        return pick, ph > 0.44
    if ph < 0.90:            # lift and reach the tower
        k = _smooth((ph - 0.5) / 0.4)
        return blend(pick, place, k), True
    return place, False      # release


def _smooth(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


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
    build: dict = field(default_factory=dict)


def _dir(a_deg, side: str, view: str, facing: int):
    a = math.radians(a_deg)
    if view == "front":
        sx = -1 if side == "l" else 1
        return (sx * math.sin(a), math.cos(a))
    return (facing * math.sin(a), math.cos(a))


def _build(build) -> dict:
    if isinstance(build, dict):
        return build
    return BUILDS.get(build or "chunky", BUILDS["chunky"])


def solve(p: dict, x: float, y: float, s: float, facing: int = 1, build=None) -> Joints:
    B = _build(build)
    view = p.get("view", "front")
    lean = math.radians(p["lean"])
    f = facing if view == "side" else 1
    up = (math.sin(lean) * f, -math.cos(lean))
    perp = (math.cos(lean), math.sin(lean) * f)
    tl = B["torso_len"] * (1 - 0.35 * p.get("slump", 0))
    tw = B["torso_w"] if view == "front" else B["torso_w_side"]
    hip = (x, y)
    neck = (x + up[0] * tl * s, y + up[1] * tl * s)
    ht = math.radians(p["lean"] + p["head_tilt"])
    hup = (math.sin(ht) * f, -math.cos(ht))
    hd = (B["neck"] + 1.0) * s
    head = (neck[0] + hup[0] * hd + p["head_dx"] * s * (f if view == "side" else 1),
            neck[1] + hup[1] * hd + p["head_drop"] * s)
    j = Joints(hip=hip, neck=neck, head=head, up=up, tw=tw, tl=tl, build=B)
    sh_base = (neck[0] - up[0] * B["sh_in"] * s, neck[1] - up[1] * B["sh_in"] * s)
    for side, sgn in (("l", -1), ("r", 1)):
        if view == "front":
            off = (tw / 2 - B["limb"] / 2 + 0.02) * s * sgn
            sh = (sh_base[0] + perp[0] * off, sh_base[1] + perp[1] * off)
            hoff = (tw / 2 - B["limb"] / 2 - 0.05) * s * sgn
            hp = (hip[0] + perp[0] * hoff, hip[1] + perp[1] * hoff)
        else:
            sh = sh_base
            hp = hip
        d1 = _dir(p[side + "a1"], side, view, facing)
        d2 = _dir(p[side + "a2"], side, view, facing)
        el = (sh[0] + d1[0] * B["uarm"] * s, sh[1] + d1[1] * B["uarm"] * s)
        ha = (el[0] + d2[0] * B["farm"] * s, el[1] + d2[1] * B["farm"] * s)
        d3 = _dir(p[side + "l1"], side, view, facing)
        d4 = _dir(p[side + "l2"], side, view, facing)
        kn = (hp[0] + d3[0] * B["thigh"] * s, hp[1] + d3[1] * B["thigh"] * s)
        ft = (kn[0] + d4[0] * B["shin"] * s, kn[1] + d4[1] * B["shin"] * s)
        j.sh[side], j.el[side], j.ha[side] = sh, el, ha
        j.hp[side], j.kn[side], j.ft[side] = hp, kn, ft
    return j


def ground_offset(p: dict, s: float, facing: int = 1, build=None) -> float:
    """Distance from hip to the lowest foot bottom (px). Used to stand on floors."""
    B = _build(build)
    j = solve(p, 0, 0, s, facing, B)
    return max(j.ft["l"][1], j.ft["r"][1], j.kn["l"][1], j.kn["r"][1]) + B["limb"] * s / 2


def core_point(j: Joints, s: float, view: str, facing: int):
    cp = (j.neck[0] - j.up[0] * s * 0.95, j.neck[1] - j.up[1] * s * 0.95)
    if view == "side":
        cp = (cp[0] + facing * j.tw * s * 0.18, cp[1])
    return cp


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
    build: object = "chunky"
    outline: float = 1.0            # thin dark outline around every part
    dim: float = 0.0                # 0..1: the archetype gave up (grey, no glow)
    flame: float = 0.0              # 0..1 flame on the head (motivation)
    flame_c: object = "#ff4b2b"


OUTLINE_C = "#25262a"


def draw_figure(canvas: skia.Canvas, p: dict, x: float, y: float, s: float, *, facing: int = 1,
                look: Look | None = None, t: float = 0.0) -> Joints:
    look = look or Look()
    B = _build(look.build)
    view = p.get("view", "front")
    j = solve(p, x, y, s, facing, B)
    lw = B["limb"] * s
    ow = s * 0.075 * look.outline         # outline width (each side)

    base = gfx.rgb(look.color)
    if look.tint is not None and look.tint_amt > 0:
        base = gfx.mix(base, look.tint, look.tint_amt)
    if look.dim > 0:
        base = gfx.mix(base, "#77787d", 0.78 * look.dim)
    if look.shadow_figure:
        base = gfx.rgb("#0d0a14")
    back = gfx.shade(base, 0.76)
    oc = gfx.rgb("#7c3aed") if look.shadow_figure else gfx.rgb(OUTLINE_C)
    oa = 0.35 if look.shadow_figure else 0.9

    # bounds for the picture recorder
    pts = [j.head, j.hip, *j.ha.values(), *j.ft.values(), *j.el.values(), *j.kn.values()]
    minx = min(q[0] for q in pts) - 2.5 * s
    maxx = max(q[0] for q in pts) + 2.5 * s
    miny = min(q[1] for q in pts) - 2.5 * s
    maxy = max(q[1] for q in pts) + 2.5 * s
    rec = skia.PictureRecorder()
    c = rec.beginRecording(skia.Rect(minx, miny, maxx, maxy))

    def limb(a, b, d, color):
        path = gfx.polyline([a, b, d])
        if ow > 0.2:
            c.drawPath(path, gfx.paint(oc, oa, stroke=lw + 2 * ow))
        c.drawPath(path, gfx.paint(color, 1.0, stroke=lw))

    def arm(side, color):
        limb(j.sh[side], j.el[side], j.ha[side], color)
        if p.get("fingers", 0) > 0.5 and side == "r":
            dx, dy = j.ha[side][0] - j.el[side][0], j.ha[side][1] - j.el[side][1]
            n = math.hypot(dx, dy) or 1
            tip = (j.ha[side][0] + dx / n * s * 0.55, j.ha[side][1] + dy / n * s * 0.55)
            if ow > 0.2:
                c.drawLine(*j.ha[side], *tip, gfx.paint(oc, oa, stroke=lw * 0.45 + 2 * ow))
            c.drawLine(*j.ha[side], *tip, gfx.paint(color, 1, stroke=lw * 0.45))

    def leg(side, color):
        if look.legs:
            limb(j.hp[side], j.kn[side], j.ft[side], color)

    def torso():
        mid = ((j.hip[0] + j.neck[0]) / 2, (j.hip[1] + j.neck[1]) / 2)
        ang = math.degrees(math.atan2(j.up[0], -j.up[1]))
        L = j.tl * s + lw * 0.6
        W = j.tw * s
        c.save()
        c.translate(*mid)
        c.rotate(ang)
        if ow > 0.2:
            gfx.rrect(c, -W / 2 - ow, -L / 2 - ow, W + 2 * ow, L + 2 * ow, W * 0.42 + ow, gfx.paint(oc, oa))
        gfx.rrect(c, -W / 2, -L / 2, W, L, W * 0.42, gfx.paint(base))
        c.restore()

    def head():
        if ow > 0.2:
            c.drawCircle(*j.head, s + ow, gfx.paint(oc, oa))
        c.drawCircle(*j.head, s, gfx.paint(base))

    def core_dot():
        if look.core is None:
            return
        cp = core_point(j, s, view, facing)
        k = max(0.0, look.core_amt) * (1 - 0.7 * look.dim)
        r = s * 0.2 * (0.85 + 0.25 * min(k, 1.6))
        c.drawCircle(*cp, r * 1.22, gfx.paint(gfx.mix(look.core, "black", 0.4), 0.35))
        c.drawCircle(*cp, r, gfx.paint(gfx.mix(gfx.mix(look.core, "#555", 0.6 * look.dim), "white",
                                               0.18 * min(1, k))))

    if view == "front":
        legc = gfx.shade(base, 0.9)
        leg("l", legc)
        leg("r", legc)
        torso()
        core_dot()
        if p.get("head_front", 0) > 0.5:
            arm("l", base)
            arm("r", base)
            head()
        else:
            head()
            arm("l", base)
            arm("r", base)
    else:
        arm("l", back)
        leg("l", back)
        torso()
        core_dot()
        head()
        leg("r", base)
        arm("r", base)

    # face details (signature attributes)
    hx, hy = j.head
    fx = facing * 0.38 * s if view == "side" else 0.0
    if look.marks > 0.01:
        mk = gfx.paint("#111111", look.marks, stroke=s * 0.08)
        for sgn in ((-1, 1) if view == "front" else (1,)):
            ex = hx + fx + sgn * s * 0.38 * (1 if view == "front" else 0.6)
            for kk in range(2):
                yy = hy + s * (0.18 + kk * 0.17)
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
    glow = look.glow * (1 - 0.85 * look.dim)
    if glow > 0 and not look.shadow_figure:
        gp = skia.Paint(ImageFilter=skia.ImageFilters.Blur(s * 0.35, s * 0.35))
        gp.setAlphaf(min(1.0, glow * a))
        canvas.saveLayer(skia.Rect(minx, miny, maxx, maxy), gp)
        canvas.drawPicture(pic)
        canvas.restore()
    lp_ = skia.Paint()
    lp_.setAlphaf(a)
    canvas.saveLayer(skia.Rect(minx, miny, maxx, maxy), lp_)
    canvas.drawPicture(pic)
    # soft top-light shading (only on the figure: SrcATop)
    sh = gfx.linear(0, miny, 0, maxy, [(0, "white", 0.0), (0.55, "black", 0.04), (1, "black", 0.2)])
    canvas.drawRect(skia.Rect(minx, miny, maxx, maxy),
                    skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcATop))
    canvas.restore()

    # additive glows drawn outside the layer
    if look.core is not None and look.core_amt > 0.05:
        cp = core_point(j, s, view, facing)
        vis = 1.0 - gfx.clamp(p.get("head_drop", 0) / 1.6) if p.get("head_front", 0) > 0.5 else 1.0
        k = min(1.6, look.core_amt) * (1 - 0.8 * look.dim)
        gfx.glow_circle(canvas, *cp, s * 0.22, look.core, 0.75 * a * vis * k, spread=3.2 + look.core_amt)
    if look.eyes is not None and look.eyes_amt > 0.01:
        for sgn in ((-1, 1) if view == "front" else (1,)):
            ex = hx + fx + (sgn * s * 0.36 if view == "front" else 0)
            ey = hy - s * 0.3
            canvas.drawCircle(ex, ey, s * 0.075, gfx.paint(gfx.mix(look.eyes, "white", 0.5), look.eyes_amt * a))
            gfx.glow_circle(canvas, ex, ey, s * 0.07, look.eyes, look.eyes_amt * a, spread=3.0)
    if look.shadow_figure:
        for sgn in ((-1, 1) if view == "front" else (1,)):
            ex = hx + fx + (sgn * s * 0.33 if view == "front" else 0)
            gfx.glow_circle(canvas, ex, hy - s * 0.2, s * 0.08, "#8b5cf6", 0.9 * a, spread=3)
            canvas.drawCircle(ex, hy - s * 0.2, s * 0.06, gfx.paint("#e9d5ff", a))
    if look.flame > 0.01:
        draw_flame(canvas, hx, hy - s * 0.92, s, look.flame, t, color=look.flame_c, a=a)
    return j


def _circle_path(x, y, r):
    pth = skia.Path()
    pth.addCircle(x, y, r)
    return pth


# ----------------------------------------------------------------------------- flame / sparkle


def draw_flame(canvas, x, y, s, amt: float, t: float, *, color="#ff4b2b", a=1.0):
    """A flame sitting on the head (motivation). amt 1 = full fire, ->0 = dying, smoke."""
    amt = max(0.0, min(1.2, amt))
    fl = 0.5 + 0.5 * math.sin(t * 23) * 0.6 + 0.25 * math.sin(t * 37 + 1)
    h = s * (0.9 + 1.0 * amt) * (0.88 + 0.12 * fl)
    w = s * (0.32 + 0.38 * amt)
    sway = math.sin(t * 7.3) * s * 0.18 * amt
    if amt > 0.05:
        gfx.glow_circle(canvas, x, y - h * 0.35, w * 1.2, color, 0.55 * a * min(1.0, amt), spread=3.2)

        def tongue(scale, col, alpha):
            ww, hh = w * scale, h * scale
            pth = skia.Path()
            pth.moveTo(x - ww, y)
            pth.cubicTo(x - ww * 1.1, y - hh * 0.45, x - ww * 0.3 + sway * 0.5, y - hh * 0.7, x + sway, y - hh)
            pth.cubicTo(x + ww * 0.3 + sway * 0.5, y - hh * 0.7, x + ww * 1.1, y - hh * 0.45, x + ww, y)
            pth.cubicTo(x + ww, y + ww * 0.7, x - ww, y + ww * 0.7, x - ww, y)
            canvas.drawPath(pth, gfx.paint(col, alpha * a))

        tongue(1.0, color, 0.95 * min(1.0, amt * 1.5))
        tongue(0.62, "#ff9f1c", 0.95 * min(1.0, amt * 1.5))
        tongue(0.32, "#fff1c1", 0.9 * min(1.0, amt * 1.5))
    if amt < 0.45:
        rnd = random.Random(7)
        k = (0.45 - amt) / 0.45
        for i in range(7):
            ph = (t * 0.55 + rnd.random()) % 1.0
            px = x + math.sin(t * 2 + i) * s * 0.25 * ph + (rnd.random() - 0.5) * s * 0.3
            py = y - s * 0.3 - ph * s * 2.6
            canvas.drawCircle(px, py, s * (0.12 + 0.35 * ph), gfx.paint("#9a9aa0", 0.22 * k * (1 - ph) * a,
                                                                       blur=s * 0.15))


def draw_sparkle(canvas, x, y, size, t: float, *, color="white", a=1.0):
    """4-point twinkle star."""
    k = 0.75 + 0.25 * math.sin(t * 9)
    r = size * k
    canvas.save()
    canvas.translate(x, y)
    canvas.rotate(t * 25)
    gfx.glow_circle(canvas, 0, 0, r * 0.35, color, 0.6 * a, spread=3.0)
    for ang in (0, 90):
        canvas.save()
        canvas.rotate(ang)
        pth = gfx.poly([(0, -r), (r * 0.13, 0), (0, r), (-r * 0.13, 0)])
        canvas.drawPath(pth, gfx.paint(color, a))
        canvas.restore()
    canvas.restore()


# ----------------------------------------------------------------------------- label / props on figures


def draw_label(canvas, x: float, head_y: float, s: float, text: str, *, a=1.0, level: float | None = None,
               level_c="violet", level_text: str | None = None, size_k=0.34, glitch: float = 0.0, t=0.0,
               base_y: float | None = None, color="#f4f4f2"):
    """Mono, letter-spaced, uppercase label above the head (or at base_y) + optional XP bar."""
    if not text or a <= 0.01:
        return head_y
    size = max(14.0, s * size_k)
    if base_y is None:
        base_y = head_y - s * 1.32
    shown = text
    if glitch > 0:
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
    w = gfx.draw_text(canvas, shown, x, base_y, size=size, c=color, a=a, spacing=size * 0.16,
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
               stamp_c="stamp", stamp_t=1.0, score: str | None = None, glow=None, t: float = 0.0):
    """Graded paper (reference prop): white sheet, red circled mark, grey lines, optional red score
    ("100") written at the top and an optional coloured glow around the sheet."""
    if a <= 0.01:
        return
    w, h = s * 1.45 * scale, s * 1.9 * scale
    if glow:
        pulse = 0.8 + 0.2 * math.sin(t * 9)
        gfx.glow_circle(canvas, cx, bottom - h / 2, h * 0.75, glow, 0.55 * a * pulse, spread=2.2)
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
        if score:
            # the teacher's red number in the top corner (+ double underline for a perfect score)
            ss = s * 0.62 * scale
            canvas.save()
            canvas.translate(w * 0.47, -h * 0.5 - ss * 0.15)
            canvas.rotate(-10)
            gfx.draw_text(canvas, score, 0, 0, size=ss, face=gfx.DISPLAY, c=stamp_c, a=sa, align="center")
            if score.strip() in ("100", "100/100"):
                sw = gfx.text_width(score, gfx.font(gfx.DISPLAY, ss))
                for i in range(2):
                    canvas.drawLine(-sw / 2, ss * (0.22 + 0.16 * i), sw / 2, ss * (0.16 + 0.16 * i),
                                    gfx.paint(stamp_c, sa, stroke=ss * 0.07))
            canvas.restore()
    canvas.restore()


def draw_zzz(canvas, x, y, s, t, a=1.0):
    for i in range(3):
        ph = (t * 0.5 + i / 3.0) % 1.0
        size = s * (0.3 + 0.25 * ph)
        xx = x + ph * s * 0.7
        yy = y - ph * s * 1.3
        al = a * math.sin(ph * math.pi)
        gfx.draw_text(canvas, "Z", xx, yy, size=size, face=gfx.MONO, c="#e9e9e9", a=al)


def draw_block(canvas, x, y, w, h, *, a=1.0, glow=0.5, c="#f2f2f0"):
    """A glowing white block (tower piece). (x, y) = bottom-center."""
    r = h * 0.18
    if glow > 0:
        gfx.rrect(canvas, x - w / 2 - h * 0.15, y - h - h * 0.15, w + h * 0.3, h * 1.3, r,
                  gfx.paint("white", 0.25 * glow * a, blur=h * 0.45))
    gfx.rrect(canvas, x - w / 2 - 1.5, y - h - 1.5, w + 3, h + 3, r + 1, gfx.paint(OUTLINE_C, 0.9 * a))
    gfx.rrect(canvas, x - w / 2, y - h, w, h, r, gfx.paint(c, a))
    canvas.drawLine(x - w / 2 + h * 0.25, y - h * 0.5, x + w / 2 - h * 0.25, y - h * 0.5,
                    gfx.paint("#c9c9c6", 0.55 * a, stroke=max(1.0, h * 0.06)))
