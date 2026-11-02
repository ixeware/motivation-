"""Power moves: the hidden anime / film references.

Every effect is a pure function of time (frames can render in any order).
Names describe the visual, not the source - the reference is in the image,
never in the text.

  hollow_purple   red + blue orbs merge into a purple sphere that erases a path
  energy_orb      a growing energy sphere anywhere (behind, below, in a hand)
  domain          the world becomes an infinite void (or a red "shrine" of slashes)
  black_flash     black lightning with red rim on impact + manga impact frame
  impact          manga impact frame (inverted b/w + speed lines)
  system          blue holographic quest / level-up window
  shadow_rise     shadow soldiers rise from dark pools behind the hero
  wheel           eight-spoked wheel above the head that turns = adaptation
  aura            king's aura: shockwave + crawling black-red lightning, others faint
  afterimage      chrome-overdrive rainbow afterimages, time slows
  speedlines      radial anime speed lines
  slash           invisible cuts across the screen
  light_pillar    a beam of light shoots up from a point (finished tower, ascension)
"""
from __future__ import annotations

import math
import random

import skia

from . import gfx
from .easing import in_cubic, in_expo, in_quad, out_back, out_cubic, out_expo, out_quad, window as win


# ----------------------------------------------------------------------------- helpers


def anchor(ctx, spec, default=None):
    W, H = ctx.W, ctx.H
    if spec is None:
        return default if default is not None else (W / 2, H / 2)
    if isinstance(spec, (list, tuple)):
        return (float(spec[0]) * W, float(spec[1]) * H)
    if isinstance(spec, str):
        spec = {"who": spec}
    st = ctx.actors.get(spec.get("who"))
    if st is None or st.joints is None:
        return (float(spec.get("x", 0.5)) * W, float(spec.get("y", 0.5)) * H)
    j = st.joints
    at = spec.get("at", "core")
    s = st.s
    if at == "hand_r":
        p = j.ha["r"]
    elif at == "hand_l":
        p = j.ha["l"]
    elif at == "hands":
        p = ((j.ha["l"][0] + j.ha["r"][0]) / 2, (j.ha["l"][1] + j.ha["r"][1]) / 2)
    elif at == "head":
        p = j.head
    elif at == "above":
        p = (j.head[0], j.head[1] - s * 2.6)
    elif at == "feet":
        p = ((j.ft["l"][0] + j.ft["r"][0]) / 2, max(j.ft["l"][1], j.ft["r"][1]) + s * 0.3)
    elif at == "front":
        cp = (j.neck[0] - j.up[0] * s * 0.95, j.neck[1] - j.up[1] * s * 0.95)
        p = (cp[0] + st.facing * s * 2.4, cp[1] - s * 0.6)
    elif at == "tower":
        prm = ctx.shot.get("params", {})
        bh = s * float(prm.get("block_h", 0.62))
        floor = st.floor if st.floor is not None else st.y
        p = (st.x + st.tower_side * s * 3.1, floor - bh * 0.7 - st.tower * (bh + 2))
    else:  # core
        p = (j.neck[0] - j.up[0] * s * 0.95, j.neck[1] - j.up[1] * s * 0.95)
    return (p[0] + float(spec.get("dx", 0)) * s, p[1] + float(spec.get("dy", 0)) * s)


def speed_lines(c, cx, cy, size, T, *, color="white", a=0.6, n=60, inner=0.28):
    rnd = random.Random(int(T * 30))
    for _ in range(n):
        ang = rnd.random() * 2 * math.pi
        r0 = size * (inner + rnd.random() * 0.25)
        r1 = size * 1.4
        w = 2 + rnd.random() * 10
        dx, dy = math.cos(ang), math.sin(ang)
        px, py = -dy * w, dx * w
        pth = gfx.poly([(cx + dx * r0, cy + dy * r0), (cx + dx * r1 + px, cy + dy * r1 + py),
                        (cx + dx * r1 - px, cy + dy * r1 - py)])
        c.drawPath(pth, gfx.paint(color, a * (0.5 + rnd.random() * 0.5)))


def bolt(rnd, x0, y0, x1, y1, segs=9, jag=0.18):
    pts = [(x0, y0)]
    L = math.hypot(x1 - x0, y1 - y0)
    nx, ny = (-(y1 - y0) / (L or 1), (x1 - x0) / (L or 1))
    for i in range(1, segs):
        t = i / segs
        off = (rnd.random() - 0.5) * 2 * jag * L * (1 - abs(t - 0.5))
        pts.append((x0 + (x1 - x0) * t + nx * off, y0 + (y1 - y0) * t + ny * off))
    pts.append((x1, y1))
    return pts


def draw_bolt(c, pts, *, core="white", rim="violet", w=4.0, a=1.0):
    path = gfx.polyline(pts)
    c.drawPath(path, gfx.paint(rim, 0.7 * a, stroke=w * 4, blur=w * 2.5, blend=gfx.ADD))
    c.drawPath(path, gfx.paint(rim, a, stroke=w * 1.8))
    c.drawPath(path, gfx.paint(core, a, stroke=w * 0.8))


def particles_in(c, x, y, r, lt, color, *, n=40, seed=1, a=1.0, speed=0.9):
    """Particles spiralling INTO a point (attraction)."""
    rnd = random.Random(seed)
    for i in range(n):
        ph = (lt * speed + rnd.random()) % 1.0
        ang = rnd.random() * 2 * math.pi + ph * 2.2
        d = r * (3.2 - 2.9 * ph)
        px, py = x + math.cos(ang) * d, y + math.sin(ang) * d
        al = a * math.sin(ph * math.pi)
        c.drawCircle(px, py, 2 + rnd.random() * 3, gfx.paint(color, al, blend=gfx.ADD))
        tx, ty = x + math.cos(ang - 0.25) * (d + r * 0.35), y + math.sin(ang - 0.25) * (d + r * 0.35)
        c.drawLine(px, py, tx, ty, gfx.paint(color, al * 0.5, stroke=2, blend=gfx.ADD))


def particles_out(c, x, y, r, lt, color, *, n=40, seed=2, a=1.0, speed=1.2):
    """Particles bursting OUT of a point (repulsion)."""
    rnd = random.Random(seed)
    for i in range(n):
        ph = (lt * speed + rnd.random()) % 1.0
        ang = rnd.random() * 2 * math.pi
        d = r * (0.8 + 2.6 * ph)
        px, py = x + math.cos(ang) * d, y + math.sin(ang) * d
        al = a * (1 - ph)
        c.drawLine(px, py, px + math.cos(ang) * r * 0.3, py + math.sin(ang) * r * 0.3,
                   gfx.paint(color, al, stroke=2.5, blend=gfx.ADD))


def swirl_rings(c, x, y, r, lt, color, *, n=3, a=1.0):
    for i in range(n):
        c.save()
        c.translate(x, y)
        c.rotate(lt * (90 + i * 50) + i * 60)
        c.scale(1.0, 0.32 + 0.12 * i)
        c.drawCircle(0, 0, r * (1.25 + i * 0.22), gfx.paint(color, 0.55 * a, stroke=3 + i, blend=gfx.ADD))
        c.restore()


def capsule(x0, y0, x1, y1, w):
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L * w, (x1 - x0) / L * w
    p = skia.Path()
    p.moveTo(x0 + nx, y0 + ny)
    p.lineTo(x1 + nx, y1 + ny)
    p.arcTo(skia.Rect(x1 - w, y1 - w, x1 + w, y1 + w), math.degrees(math.atan2(ny, nx)), -180, False)
    p.lineTo(x0 - nx, y0 - ny)
    p.arcTo(skia.Rect(x0 - w, y0 - w, x0 + w, y0 + w), math.degrees(math.atan2(-ny, -nx)), -180, False)
    p.close()
    return p


# ----------------------------------------------------------------------------- base


class VFX:
    default_dur = 2.0

    def __init__(self, ev: dict, shot: dict):
        self.ev = ev
        self.t0 = float(ev.get("t", 0.0))
        self.off = float(ev.get("offset", 0.0))
        self.dur = float(ev.get("dur", self.default_dur))
        self.seed = int(ev.get("seed", 1))

    def lt(self, ctx) -> float:
        return ctx.t - self.t0 + self.off

    def on(self, ctx) -> bool:
        lt = self.lt(ctx)
        return self.off <= lt < self.dur + self.ev.get("tail", 0.0) and ctx.t >= self.t0

    def sounds(self) -> list[tuple[float, str, float]]:
        return []

    def cues(self):
        out = []
        for o, n, g in self.sounds():
            if o >= self.off - 1e-6:
                out.append((self.t0 + o - self.off, n, g))
        return out

    def pre(self, ctx, actors):
        pass

    def build(self, ctx, actors):
        pass


# ----------------------------------------------------------------------------- hollow purple


class HollowPurple(VFX):
    """Blue (attract) at one hand + red (repel) at the other -> merge -> purple
    sphere fired through the targets, leaving an erased trench."""
    default_dur = 6.0

    def __init__(self, ev, shot):
        super().__init__(ev, shot)
        self.c1 = float(ev.get("charge", 1.6))
        self.c2 = self.c1 + float(ev.get("merge", 0.9))
        self.c3 = self.c2 + float(ev.get("travel", 0.9))
        self.dur = float(ev.get("dur", self.c3 + 2.5))
        self.caster = ev.get("caster")
        self.targets = ev.get("targets", [])
        self.r = float(ev.get("r", 46))
        self.big = float(ev.get("big", 230))

    def sounds(self):
        return [(0.0, "riser", 0.9), (0.15, "hum", 0.5), (self.c1 + (self.c2 - self.c1) * 0.55, "hit", 0.9),
                (self.c2, "boom", 1.0), (self.c2 + 0.02, "whoosh", 0.8), (self.c3, "rumble", 0.8)]

    def _points(self, ctx):
        st = ctx.actors.get(self.caster)
        if st is not None and st.joints is not None:
            bl = anchor(ctx, {"who": self.caster, "at": "hand_l"})
            rd = anchor(ctx, {"who": self.caster, "at": "hand_r"})
            mp = anchor(ctx, self.ev.get("from", {"who": self.caster, "at": "front"}))
        else:
            mp = anchor(ctx, self.ev.get("from", [0.85, 0.75]))
            bl = (mp[0] - 160, mp[1])
            rd = (mp[0] + 160, mp[1])
        to = self.ev.get("to")
        if to is None and self.targets:
            pts = [anchor(ctx, {"who": tg}) for tg in self.targets if tg in ctx.actors]
            to = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None
        elif to is not None:
            to = anchor(ctx, to)
        if to is None:
            to = (mp[0] - 600, mp[1])
        dx, dy = to[0] - mp[0], to[1] - mp[1]
        L = math.hypot(dx, dy) or 1
        return bl, rd, mp, (dx / L, dy / L)

    def _sphere(self, lt, mp, d):
        p = win(lt, self.c2, self.c3)
        travel = float(self.ev.get("length", 2600))
        dist_ = travel * in_quad(p) * 0.6 + travel * p * 0.4
        R = self.r * 1.4 + (self.big - self.r * 1.4) * out_cubic(min(1.0, p * 2.5))
        return (mp[0] + d[0] * dist_, mp[1] + d[1] * dist_), R, dist_

    def pre(self, ctx, actors):
        if ctx.t < self.t0:
            return
        lt = min(self.lt(ctx), self.dur)
        st = actors.get(self.caster)
        if st is not None and lt < self.c3:
            st.look.eyes_amt = max(st.look.eyes_amt, out_quad(win(lt, 0.0, 0.4)))
            st.look.core_amt = max(st.look.core_amt, 1.0 + 1.2 * win(lt, 0, self.c2))
        # darken the world while charging
        k = win(lt, 0, self.c1 * 0.8) * (1 - win(lt, self.c3 + 0.4, self.c3 + 1.6))
        ctx.darken = max(ctx.darken, 0.55 * k)
        ctx.desat = max(ctx.desat, 0.35 * k)
        if lt >= self.c2:
            bl, rd, mp, d = self._points(ctx)
            for tg in self.targets:
                ts = actors.get(tg)
                if ts is None:
                    continue
                core = (ts.x, ts.y - ts.s * 1.5)
                proj = (core[0] - mp[0]) * d[0] + (core[1] - mp[1]) * d[1]
                _, R, dist_ = self._sphere(lt, mp, d)
                if dist_ + R * 0.6 >= proj:
                    # find erase time roughly
                    ts.alpha = 0.0
        # shakes / flashes
        mt = self.c1 + (self.c2 - self.c1) * 0.55
        if mt <= lt < mt + 0.12:
            ctx.flash = max(ctx.flash, 0.85 * (1 - (lt - mt) / 0.12))
            ctx.flash_c = "#f5e8ff"
        if self.c2 <= lt < self.c2 + 2.0 / ctx.fps:
            ctx.impact = 1.0
        if self.c2 <= lt < self.c3 + 0.8:
            ctx.shake = max(ctx.shake, 0.9 * (1 - win(lt, self.c2, self.c3 + 0.8)))
            ctx.chroma = max(ctx.chroma, 0.8 * (1 - win(lt, self.c2, self.c2 + 0.6)))
        if self.c2 - 0.3 <= lt < self.c2 + 0.5:
            ctx.zoom_punch += 0.05 * math.sin(win(lt, self.c2 - 0.3, self.c2 + 0.5) * math.pi)

    def build(self, ctx, actors):
        if ctx.t < self.t0:
            return
        lt = min(self.lt(ctx), self.dur)
        bl, rd, mp, d = self._points(ctx)
        r = self.r
        mt = self.c1 + (self.c2 - self.c1) * 0.55

        def charge(c):
            if lt >= mt:
                return
            g = out_cubic(win(lt, 0, self.c1))
            m = in_cubic(win(lt, self.c1, mt))
            b = (gfx.lerp(bl[0], mp[0], m), gfx.lerp(bl[1], mp[1], m))
            rr = (gfx.lerp(rd[0], mp[0], m), gfx.lerp(rd[1], mp[1], m))
            pulse = 1 + 0.08 * math.sin(lt * 18)
            particles_in(c, *b, r * g, lt, "#7cc4ff", n=34, seed=self.seed, a=g)
            particles_out(c, *rr, r * g, lt, "#ff6b6b", n=34, seed=self.seed + 1, a=g)
            gfx.orb(c, *b, r * g * pulse, "#2f7bff", a=g)
            gfx.orb(c, *rr, r * g * pulse, "#ff3030", a=g)
            gfx.glow_circle(c, *b, r * 2.5 * g, "#2f7bff", 0.18 * g, spread=3)
            gfx.glow_circle(c, *rr, r * 2.5 * g, "#ff3030", 0.18 * g, spread=3)
            if m > 0.4:
                rnd = random.Random(int(lt * 20))
                for _ in range(3):
                    draw_bolt(c, bolt(rnd, *b, *rr, segs=7, jag=0.25), core="#f3e8ff", rim="#a855f7", w=2.5, a=m)

        def merged(c):
            if lt < mt or lt >= self.c2 + 0.05:
                return
            k = out_back(win(lt, mt, mt + 0.35))
            R = r * 1.4 * k * (1 + 0.06 * math.sin(lt * 22))
            swirl_rings(c, *mp, R, lt * 4, "#c084fc", a=k)
            particles_in(c, *mp, R, lt, "#e9d5ff", n=40, seed=self.seed + 3, a=k, speed=1.6)
            gfx.orb(c, *mp, R, "#9333ea", a=1.0)
            gfx.glow_circle(c, *mp, R * 3.0, "#a855f7", 0.22, spread=2.5)
            rnd = random.Random(int(lt * 24))
            for _ in range(4):
                ang = rnd.random() * 2 * math.pi
                L = R * (1.6 + rnd.random())
                draw_bolt(c, bolt(rnd, *mp, mp[0] + math.cos(ang) * L, mp[1] + math.sin(ang) * L, segs=6),
                          core="#faf5ff", rim="#a855f7", w=2.0, a=0.9)

        def fired(c):
            if lt < self.c2:
                return
            pos, R, dist_ = self._sphere(lt, mp, d)
            fade = 1 - win(lt, self.c3 + 0.3, self.dur)
            w = R * 0.78
            trail = capsule(mp[0], mp[1], pos[0], pos[1], w)
            # erased trench: near-black core, violet rim, inner crackle
            ember = 0.35 + 0.65 * fade
            c.drawPath(trail, gfx.paint("#050008", 0.96 * (0.6 + 0.4 * fade)))
            c.drawPath(trail, gfx.paint("#7c3aed", 0.55 * ember, stroke=46, blur=34, blend=gfx.ADD))
            c.drawPath(trail, gfx.paint("#a855f7", 0.9 * ember, stroke=12, blur=12, blend=gfx.ADD))
            c.drawPath(trail, gfx.paint("#e9d5ff", 0.85 * ember, stroke=3))
            # embers rising from the rim
            rnd3 = random.Random(self.seed + 21)
            for _ in range(70):
                a0 = rnd3.random() * dist_
                side = 1 if rnd3.random() < 0.5 else -1
                ph = ((lt - self.c2) * (0.25 + rnd3.random() * 0.5) + rnd3.random()) % 1.0
                px = mp[0] + d[0] * a0 - d[1] * w * side
                py = mp[1] + d[1] * a0 + d[0] * w * side - ph * 160
                c.drawCircle(px, py, 1.5 + rnd3.random() * 2.5,
                             gfx.paint("#d8b4fe", ember * (1 - ph) * 0.9, blend=gfx.ADD))
            rnd = random.Random(int(lt * 15))
            L = dist_
            for _ in range(int(6 * fade) + 1):
                a0 = rnd.random() * L
                a1 = min(L, a0 + 80 + rnd.random() * 220)
                off0 = (rnd.random() - 0.5) * w * 1.6
                off1 = (rnd.random() - 0.5) * w * 1.6
                p0 = (mp[0] + d[0] * a0 - d[1] * off0, mp[1] + d[1] * a0 + d[0] * off0)
                p1 = (mp[0] + d[0] * a1 - d[1] * off1, mp[1] + d[1] * a1 + d[0] * off1)
                draw_bolt(c, bolt(rnd, *p0, *p1, segs=5), core="#f5f3ff", rim="#7c3aed", w=1.6, a=0.7 * fade)
            # sphere
            if lt < self.c3 + 0.2:
                swirl_rings(c, *pos, R, lt * 5, "#d8b4fe", a=1.0)
                gfx.orb(c, *pos, R, "#9333ea", a=1.0)
                gfx.glow_circle(c, *pos, R * 2.4, "#a855f7", 0.35, spread=2.4)
                particles_out(c, *pos, R, lt, "#e9d5ff", n=50, seed=self.seed + 5, speed=2.5)
            # shockwave at origin
            sw = win(lt, self.c2, self.c2 + 0.5)
            if 0 < sw < 1:
                c.drawCircle(*mp, r * 2 + sw * 520, gfx.paint("#e9d5ff", (1 - sw) * 0.9, stroke=14 * (1 - sw) + 2))
            # debris drifting after
            if lt > self.c3:
                rnd2 = random.Random(self.seed + 9)
                for _ in range(60):
                    a0 = rnd2.random() * L
                    off = (rnd2.random() - 0.5) * w * 2.2
                    ph = (lt - self.c3) * (0.3 + rnd2.random() * 0.6)
                    px = mp[0] + d[0] * a0 - d[1] * off
                    py = mp[1] + d[1] * a0 + d[0] * off - ph * 120
                    c.drawCircle(px, py, 1.5 + rnd2.random() * 3, gfx.paint("#c4b5fd", 0.8 * fade * (1 - min(1, ph)),
                                                                              blend=gfx.ADD))

        ctx.add("fx", charge, z=1)
        ctx.add("fx", merged, z=2)
        ctx.add("fx", fired, z=3)
        # violet light spill on the floor/world
        k = win(lt, 0, self.c1) * (1 - win(lt, self.c3 + 0.4, self.dur))
        ctx.add("fx", lambda c: gfx.glow_circle(c, *mp, 380, "#7c3aed", 0.12 * k, spread=2.4), z=0)


# ----------------------------------------------------------------------------- energy orb


class EnergyOrb(VFX):
    """A sphere that grows somewhere (e.g. behind/below fighters)."""
    default_dur = 4.0

    def sounds(self):
        return [(0.0, "hum", float(self.ev.get("gain", 0.6))), (0.0, "riser", 0.5 * float(self.ev.get("gain", 0.6)))]

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        ev = self.ev
        pos = anchor(ctx, ev.get("at", [0.5, 0.8]))
        color = ev.get("color", "#9333ea")
        r = float(ev.get("r", 120))
        grow = float(ev.get("grow", 2.0))
        g = out_cubic(win(lt, 0, grow)) * (1 - win(lt, self.dur - 0.25, self.dur))
        R = r * g * (1 + 0.05 * math.sin(lt * 9))
        layer = ev.get("layer", "back")

        def draw(c):
            if R <= 1:
                return
            gfx.glow_circle(c, pos[0], pos[1], R * 2.4, color, 0.25 * g, spread=2.8)
            particles_in(c, *pos, R, lt, gfx.mix(color, "white", 0.5), n=46, seed=self.seed, a=g)
            swirl_rings(c, *pos, R, lt * 3, gfx.mix(color, "white", 0.4), a=0.8 * g)
            gfx.orb(c, *pos, R, color, a=g)
            rnd = random.Random(int(lt * 18))
            for _ in range(3):
                ang = rnd.random() * 2 * math.pi
                L = R * (1.4 + rnd.random() * 0.8)
                draw_bolt(c, bolt(rnd, *pos, pos[0] + math.cos(ang) * L, pos[1] + math.sin(ang) * L, segs=6),
                          core="#faf5ff", rim=color, w=2, a=0.8 * g)

        ctx.add(layer, draw, z=-5 if layer == "main" else 5)
        if ev.get("spill", True):
            def spill(c):
                c.save()
                c.scale(1, 0.3)
                gfx.glow_circle(c, pos[0], (pos[1] + r * 0.6) / 0.3, R * 3.0, color, 0.22 * g, spread=1.8)
                c.restore()
            ctx.add("fx", spill, z=-1)
        ctx.tint = color
        ctx.tint_amt = max(ctx.tint_amt, 0.22 * g * float(ev.get("tint", 1.0)))


# ----------------------------------------------------------------------------- domain


class Domain(VFX):
    """The world turns into a void (style 'void') or a red shrine of cuts ('shrine')."""
    default_dur = 4.0

    def sounds(self):
        return [(0.0, "riser", 0.6), (float(self.ev.get("expand_at", 0.35)), "boom", 0.9),
                (float(self.ev.get("expand_at", 0.35)) + 0.05, "drone", 0.7)]

    def pre(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        ex = float(self.ev.get("expand_at", 0.35))
        k = out_expo(win(lt, ex, ex + 0.7))
        ctx.layer_alpha["back"] = min(ctx.layer_alpha.get("back", 1.0), 1 - k)
        ctx.layer_alpha["bg"] = min(ctx.layer_alpha.get("bg", 1.0), 1 - k)
        if ex <= lt < ex + 2.0 / ctx.fps:
            ctx.impact = 1.0
        if ex <= lt < ex + 0.5:
            ctx.shake = max(ctx.shake, 0.6 * (1 - (lt - ex) / 0.5))
        caster = self.ev.get("caster")
        for aid, st in actors.items():
            if aid == caster:
                st.look.eyes_amt = max(st.look.eyes_amt, k)
                st.look.band = st.look.band * (1 - k)
                st.look.core_amt = max(st.look.core_amt, 1 + k)
            elif aid in self.ev.get("frozen", list(actors)):
                if self.ev.get("style", "void") == "shrine":
                    st.look.tint, st.look.tint_amt = "#7f1d1d", 0.5 * k
                    cut = win(lt, ex + 0.9, ex + 1.3)
                    st.alpha = min(st.alpha, 1 - 0.85 * cut)
                    st.look.alpha = st.alpha
                else:
                    st.look.tint, st.look.tint_amt = "#1e3a8a", 0.55 * k
                    st.look.glow *= 1 - k
                    st.alpha = min(st.alpha, 1 - 0.35 * k)
                    st.look.alpha = st.alpha

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        W, H = ctx.W, ctx.H
        ex = float(self.ev.get("expand_at", 0.35))
        caster = self.ev.get("caster")
        center = anchor(ctx, {"who": caster} if caster else self.ev.get("at", [0.5, 0.5]))
        k = out_expo(win(lt, ex, ex + 0.7))
        Rmax = math.hypot(W, H) * 1.6
        R = 10 + k * Rmax
        style = self.ev.get("style", "void")
        texts = self.ev.get("texts", ["2X+7=19", "X=6", "3X+6=9", "Y=4X+1", "f'(x)=0", "∑", "π", "∞", "A+",
                                      "√144=12", "e^iπ+1=0", "Δ", "λ"])
        accent = self.ev.get("color", "#60a5fa" if style == "void" else "#ef4444")
        out_k = 1 - win(lt, self.dur - 0.3, self.dur)

        def void(c):
            if k <= 0:
                return
            c.save()
            pth = skia.Path()
            pth.addCircle(center[0], center[1], R)
            c.clipPath(pth, doAntiAlias=True)
            cx, cy = center
            if style == "void":
                c.drawRect(skia.Rect(-W, -H, 2 * W, 2 * H),
                           skia.Paint(Shader=gfx.radial(cx, cy, H, [(0, "#0d1440", out_k), (0.5, "#05061a", out_k),
                                                                     (1, "#000002", out_k)])))
                # hyperspace streaks
                rnd = random.Random(self.seed)
                for i in range(160):
                    ang = rnd.random() * 2 * math.pi
                    sp = 0.25 + rnd.random() * 0.9
                    ph = (lt * sp + rnd.random()) % 1.0
                    d0 = 40 + ph ** 2 * H * 1.1
                    d1 = d0 + 20 + ph * 140
                    col_ = "#bfdbfe" if i % 5 else "#ffffff"
                    c.drawLine(cx + math.cos(ang) * d0, cy + math.sin(ang) * d0, cx + math.cos(ang) * d1,
                               cy + math.sin(ang) * d1, gfx.paint(col_, ph * 0.9 * out_k, stroke=1.5 + ph * 2.5,
                                                                  blend=gfx.ADD))
                # giant iris
                for i in range(5):
                    rr = 260 + i * 120 + math.sin(lt * 1.5 + i) * 10
                    c.drawCircle(cx, cy, rr, gfx.paint(accent, (0.35 - i * 0.05) * out_k, stroke=2 + (i == 0) * 3,
                                                       blend=gfx.ADD))
                c.save()
                c.translate(cx, cy)
                c.rotate(lt * 12)
                for i in range(36):
                    c.rotate(10)
                    c.drawLine(0, 260, 0, 300 + (i % 3) * 30, gfx.paint(accent, 0.5 * out_k, stroke=2,
                                                                        blend=gfx.ADD))
                c.restore()
                gfx.glow_circle(c, cx, cy, 200, accent, 0.25 * out_k, spread=3)
            else:  # shrine: blood sky + slashes
                c.drawRect(skia.Rect(-W, -H, 2 * W, 2 * H),
                           skia.Paint(Shader=gfx.linear(0, 0, 0, H, [(0, "#2a0505", out_k), (0.6, "#120202", out_k),
                                                                     (1, "#000000", out_k)])))
                gfx.glow_circle(c, cx, H * 0.25, 260, "#dc2626", 0.25 * out_k, spread=3)
                c.drawCircle(cx, H * 0.25, 170, gfx.paint("#f87171", 0.9 * out_k))
            c.restore()

        def floating(c):
            if k <= 0.2:
                return
            rnd = random.Random(self.seed + 3)
            cx, cy = center
            for i in range(26):
                txt = texts[i % len(texts)]
                ang = rnd.random() * 2 * math.pi + lt * (0.1 + rnd.random() * 0.2)
                d = 260 + rnd.random() * 700
                x = cx + math.cos(ang) * d
                y = cy + math.sin(ang) * d * 1.3
                a = 0.75 * k * out_k * (0.4 + 0.6 * rnd.random())
                gfx.draw_text(c, txt, x, y, size=26 + rnd.random() * 30, face=gfx.MONO, c="#dbeafe", a=a,
                              glow=6, glow_c=accent)

        def slashes(c):
            rnd = random.Random(int(lt * 12) + self.seed)
            for _ in range(int(8 * k * out_k)):
                x0, y0 = rnd.random() * W, rnd.random() * H
                ang = rnd.random() * math.pi
                L = 300 + rnd.random() * 900
                x1, y1 = x0 + math.cos(ang) * L, y0 + math.sin(ang) * L
                c.drawLine(x0, y0, x1, y1, gfx.paint("white", 0.9, stroke=2.5))
                c.drawLine(x0, y0, x1, y1, gfx.paint("#ef4444", 0.6, stroke=8, blur=6, blend=gfx.ADD))

        def ring(c):
            if 0 < k < 0.999:
                c.drawCircle(*center, R, gfx.paint(accent, 0.9, stroke=18, blur=12, blend=gfx.ADD))
                c.drawCircle(*center, R, gfx.paint("white", 0.9, stroke=4))

        ctx.add("bgfx", void)
        if style == "void":
            ctx.add("fx", floating, z=-2)
        else:
            ctx.add("fx", slashes, z=4)
        ctx.add("fx", ring, z=5)


# ----------------------------------------------------------------------------- black flash / impact


class BlackFlash(VFX):
    default_dur = 0.7

    def sounds(self):
        return [(0.0, "crack", 1.0), (0.0, "hit", 0.9)]

    def pre(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        if lt < 2.0 / ctx.fps:
            ctx.impact = 1.0
        ctx.shake = max(ctx.shake, 0.9 * (1 - lt / self.dur))
        ctx.chroma = max(ctx.chroma, 0.7 * (1 - win(lt, 0, 0.35)))
        ctx.zoom_punch += 0.07 * (1 - win(lt, 0, 0.3)) ** 2
        for tg in self.ev.get("targets", []):
            if tg in actors:
                actors[tg].look.tint, actors[tg].look.tint_amt = "#dc2626", 0.4 * (1 - win(lt, 0, self.dur))

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        pos = anchor(ctx, self.ev.get("at", [0.5, 0.5]))
        size = float(self.ev.get("size", 420))

        def draw(c):
            g = out_expo(win(lt, 0, 0.12))
            fade = 1 - win(lt, 0.25, self.dur)
            rnd = random.Random(int(lt * ctx.fps / 2) + self.seed)
            gfx.glow_circle(c, *pos, 90 * g, "#dc2626", 0.6 * fade, spread=3.2)
            for _ in range(9):
                ang = rnd.random() * 2 * math.pi
                L = size * (0.4 + rnd.random() * 0.7) * g
                pts = bolt(rnd, *pos, pos[0] + math.cos(ang) * L, pos[1] + math.sin(ang) * L, segs=8, jag=0.22)
                draw_bolt(c, pts, core="#050505", rim="#ef1d1d", w=5, a=fade)
                if rnd.random() < 0.5:
                    m = pts[len(pts) // 2]
                    ang2 = ang + (rnd.random() - 0.5) * 1.6
                    draw_bolt(c, bolt(rnd, *m, m[0] + math.cos(ang2) * L * 0.4, m[1] + math.sin(ang2) * L * 0.4,
                                      segs=5), core="#050505", rim="#ef1d1d", w=3, a=fade)
            c.drawCircle(*pos, 26 * g, gfx.paint("black", fade))
            c.drawCircle(*pos, 26 * g, gfx.paint("#ff3b3b", fade, stroke=5))
        ctx.add("fx", draw, z=6)


class Impact(VFX):
    default_dur = 0.1

    def sounds(self):
        return [(0.0, "hit", float(self.ev.get("gain", 0.9)))]

    def pre(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t >= self.t0 and lt < float(self.ev.get("frames", 3)) / ctx.fps:
            ctx.impact = 1.0
            ctx.shake = max(ctx.shake, 0.7)


# ----------------------------------------------------------------------------- system window


class SystemWindow(VFX):
    default_dur = 2.6

    def sounds(self):
        return [(0.0, "chime", 0.8)]

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        W, H = ctx.W, ctx.H
        ev = self.ev
        color = ev.get("color", "#38bdf8")
        title = ev.get("title", "NOTIFICATION")
        lines = ev.get("lines", ["Daily quest completed."])
        y = float(ev.get("y", 0.3)) * H
        w = W * float(ev.get("w", 0.8))
        open_k = out_back(win(lt, 0, 0.28)) * (1 - in_quad(win(lt, self.dur - 0.25, self.dur)))
        lh = 58
        h = (110 + lh * len(lines)) * max(0.02, open_k)
        x0 = W / 2 - w / 2

        def draw(c):
            if open_k <= 0.01:
                return
            flick = 1.0 if lt > 0.3 else (0.6 + 0.4 * (int(lt * 40) % 2))
            top = y - h / 2
            gfx.rrect(c, x0, top, w, h, 6, gfx.paint("#04101e", 0.86 * flick))
            gfx.rrect(c, x0, top, w, h, 6, gfx.paint(color, 0.9 * flick, stroke=3, blur=10, blend=gfx.ADD))
            gfx.rrect(c, x0, top, w, h, 6, gfx.paint(color, flick, stroke=2))
            for i in range(int(h // 6)):
                c.drawLine(x0, top + i * 6, x0 + w, top + i * 6, gfx.paint(color, 0.05, stroke=1))
            br = 26
            for (bx, by, sx, sy) in ((x0, top, 1, 1), (x0 + w, top, -1, 1), (x0, top + h, 1, -1),
                                     (x0 + w, top + h, -1, -1)):
                c.drawLine(bx - sx * 8, by - sy * 8, bx + sx * br, by - sy * 8, gfx.paint("white", flick, stroke=4))
                c.drawLine(bx - sx * 8, by - sy * 8, bx - sx * 8, by + sy * br, gfx.paint("white", flick, stroke=4))
            if open_k > 0.85:
                ty = top + 70
                gfx.draw_text(c, f"[  {title}  ]", W / 2, ty, size=40, face=gfx.MONO_XB, c="white", spacing=6,
                              glow=14, glow_c=color)
                c.drawLine(x0 + 40, ty + 22, x0 + w - 40, ty + 22, gfx.paint(color, 0.6, stroke=2))
                for i, ln in enumerate(lines):
                    td = 0.3 + i * 0.25
                    if isinstance(ln, dict):
                        a0, a1 = ln.get("count", [0, 100])
                        n = int(gfx.lerp(a0, a1, out_cubic(win(lt, td, td + 0.8))))
                        txt = ln["text"].replace("{}", str(n))
                        cc = ln.get("color", "#e0f2fe")
                    else:
                        txt, cc = ln, "#e0f2fe"
                    shown = txt[: int(len(txt) * win(lt, td, td + 0.35))]
                    gfx.draw_text(c, shown, W / 2, ty + 34 + lh * (i + 1), size=34, face=gfx.MONO, c=cc,
                                  spacing=2, glow=6, glow_c=color)
        ctx.add("screen", draw, z=10)


# ----------------------------------------------------------------------------- shadow army


class ShadowRise(VFX):
    default_dur = 4.0

    def sounds(self):
        return [(0.0, "rumble", 0.8), (0.2, "riser", 0.4), (float(self.ev.get("rise", 1.2)), "boom", 0.6)]

    def build(self, ctx, actors):
        from . import rig
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        caster = actors.get(self.ev.get("caster"))
        n = int(self.ev.get("count", 6))
        rise = float(self.ev.get("rise", 1.2))
        if caster is None:
            return
        view = caster.pose.get("view", "front")
        s = caster.s * float(self.ev.get("scale", 0.92))
        floor = anchor(ctx, {"who": caster.id, "at": "feet"})[1]
        spread = float(self.ev.get("spread", 4.2)) * caster.s
        rnd = random.Random(self.seed)
        soldiers = []   # (x, delay, scale, side, depth_offset)
        rows = self.ev.get("rows")
        if rows:
            # formation behind the hero: [[scale, count, back(px in caster radii), width(caster radii)], ...]
            for ri, row in enumerate(rows):
                rs_, cnt, back = float(row[0]), int(row[1]), float(row[2])
                width = float(row[3]) if len(row) > 3 else spread / caster.s
                for i in range(cnt):
                    u = (i + 0.5) / cnt - 0.5
                    x = caster.x + u * width * caster.s + (rnd.random() - 0.5) * caster.s * 0.6
                    if abs(x - caster.x) < caster.s * 1.4 and ri == 0:
                        x += math.copysign(caster.s * 1.6, x - caster.x or 1)
                    soldiers.append((x, ri * 0.25 + rnd.random() * 0.45, caster.s * rs_, 1 if u > 0 else -1,
                                     back * caster.s))
        else:
            for i in range(n):
                side = -1 if i % 2 == 0 else 1
                rank = i // 2 + 1
                x = caster.x + side * (spread * 0.45 * rank / max(1, (n + 1) // 2) + caster.s * 1.2)
                soldiers.append((x, rnd.random() * 0.6, s * (0.9 - 0.06 * rank), side, 0.0))
        pose = rig.pose_dict("stand" if view == "front" else "stand_side")
        build = caster.look.build

        def draw(c):
            for x, delay, sc, side, back in sorted(soldiers, key=lambda q: (-q[4], q[2])):
                k = out_cubic(win(lt, delay, delay + rise))
                pool = out_cubic(win(lt, delay * 0.5, delay * 0.5 + 0.4))
                fl = floor - (caster.s - sc) * 0.2 - back
                c.save()
                c.scale(1, 0.22)
                c.drawCircle(x, fl / 0.22, sc * 1.9 * pool, gfx.paint("#020005", 0.95))
                gfx.glow_circle(c, x, fl / 0.22, sc * 1.9 * pool, "#6d28d9", 0.35 * pool, spread=1.4)
                c.restore()
                if k <= 0:
                    continue
                hip = fl - rig.ground_offset(pose, sc, 1, build) * k + sc * 0.2 * (1 - k)
                c.save()
                c.clipRect(skia.Rect(x - sc * 6, fl - sc * 16, x + sc * 6, fl + 2))
                rig.draw_figure(c, pose, x, hip + (1 - k) * sc * 4, sc, facing=-side if view == "side" else 1,
                                look=rig.Look(shadow_figure=True, glow=0, alpha=0.95, build=build))
                c.restore()
                rnd2 = random.Random(int(x))
                for j in range(8):
                    ph = (lt * 0.5 + rnd2.random()) % 1.0
                    px = x + (rnd2.random() - 0.5) * sc * 3
                    py = fl - ph * sc * 6
                    c.drawCircle(px, py, sc * (0.5 + ph), gfx.paint("#4c1d95", 0.18 * (1 - ph) * pool,
                                                                    blur=sc * 0.5, blend=gfx.ADD))
        ctx.add("main", draw, z=-3)


# ----------------------------------------------------------------------------- adaptation wheel


class Wheel(VFX):
    default_dur = 6.0

    def sounds(self):
        out = [(0.0, "chime", 0.3)]
        for tt in self.ev.get("turns", [1.0]):
            out.append((float(tt), "clank", 0.9))
        return out

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        who = self.ev.get("who")
        st = actors.get(who)
        if st is None:
            return
        turns = [float(x) for x in self.ev.get("turns", [1.0])]
        ang = 0.0
        glow = 0.0
        for tt in turns:
            p = win(lt, tt, tt + 0.35)
            ang += 45 * out_back(p, 2.2)
            if tt <= lt < tt + 0.6:
                glow = max(glow, 1 - (lt - tt) / 0.6)
        appear = out_back(win(lt, 0, 0.4))
        color = self.ev.get("color", "#e8d18a")

        def draw(c):
            hx, hy = st.joints.head
            s = st.s * float(self.ev.get("scale", 1.0))
            cy = hy - s * 3.3
            R = s * 1.35 * appear
            if R <= 1:
                return
            gfx.glow_circle(c, hx, cy, R, color, 0.2 + 0.6 * glow, spread=2.4)
            c.save()
            c.translate(hx, cy)
            c.rotate(ang)
            c.scale(1, 0.92)
            rim = gfx.paint(color, 0.95, stroke=s * 0.16)
            c.drawCircle(0, 0, R, rim)
            c.drawCircle(0, 0, R * 0.28, gfx.paint(color, 0.95))
            for i in range(8):
                a = math.radians(i * 45)
                ca, sa = math.cos(a), math.sin(a)
                c.drawLine(ca * R * 0.28, sa * R * 0.28, ca * R * 1.32, sa * R * 1.32,
                           gfx.paint(color, 0.95, stroke=s * 0.12))
                c.drawCircle(ca * R * 1.42, sa * R * 1.42, s * 0.16, gfx.paint(color, 0.95))
            c.restore()
        ctx.add("fx", draw, z=2)


# ----------------------------------------------------------------------------- king's aura


class Aura(VFX):
    default_dur = 2.5

    def sounds(self):
        return [(0.0, "boom", 0.9), (0.05, "rumble", 0.7), (0.1, "crack", 0.5)]

    def pre(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        ctx.shake = max(ctx.shake, 0.7 * (1 - win(lt, 0, 1.2)))
        ctx.tint, ctx.tint_amt = "#7f1d1d", max(ctx.tint_amt, 0.35 * (1 - win(lt, 0.3, self.dur)))
        if lt < 2 / ctx.fps:
            ctx.impact = 1.0
        for tg in self.ev.get("targets", []):
            st = actors.get(tg)
            if st is None:
                continue
            k = win(lt, 0.15, 0.6)
            st.y += st.s * 0.6 * out_cubic(k)
            st.look.tint, st.look.tint_amt = "#333333", 0.6 * k
            st.alpha = min(st.alpha, 1 - 0.55 * k)
            st.look.alpha = st.alpha
            st.glitch = max(st.glitch, 1 - k)

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        pos = anchor(ctx, {"who": self.ev.get("caster"), "at": "core"})

        def draw(c):
            for i in range(3):
                p = win(lt, i * 0.18, i * 0.18 + 0.9)
                if 0 < p < 1:
                    c.drawCircle(*pos, 60 + p * 1500, gfx.paint("white", (1 - p) * 0.8, stroke=16 * (1 - p) + 2))
                    c.drawCircle(*pos, 60 + p * 1500, gfx.paint("#dc2626", (1 - p) * 0.5, stroke=40 * (1 - p) + 4,
                                                                 blur=20, blend=gfx.ADD))
            rnd = random.Random(int(lt * 15) + self.seed)
            fade = 1 - win(lt, 1.0, self.dur)
            for _ in range(6):
                ang = rnd.random() * 2 * math.pi
                r0 = 80 + rnd.random() * 80
                L = 200 + rnd.random() * 300
                draw_bolt(c, bolt(rnd, pos[0] + math.cos(ang) * r0, pos[1] + math.sin(ang) * r0,
                                  pos[0] + math.cos(ang) * (r0 + L), pos[1] + math.sin(ang) * (r0 + L), segs=7),
                          core="#0a0a0a", rim="#ef4444", w=3.5, a=fade)
        ctx.add("fx", draw, z=4)


# ----------------------------------------------------------------------------- afterimages


class Afterimage(VFX):
    default_dur = 2.0
    COLORS = ["#22d3ee", "#e879f9", "#facc15", "#4ade80", "#f472b6", "#60a5fa"]

    def sounds(self):
        return [(0.0, "whoosh", 0.7), (0.0, "drone", 0.3)]

    def pre(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        k = win(lt, 0, 0.2) * (1 - win(lt, self.dur - 0.3, self.dur))
        ctx.tint, ctx.tint_amt = "#14b8a6", max(ctx.tint_amt, 0.18 * k)
        ctx.chroma = max(ctx.chroma, 0.25 * k)

    def build(self, ctx, actors):
        from . import rig
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        who = self.ev.get("who")
        objs = getattr(ctx, "actor_objs", {})
        if who not in objs:
            return
        n = int(self.ev.get("count", 6))
        gap = float(self.ev.get("gap", 0.07))

        def draw(c):
            for i in range(n, 0, -1):
                tt = ctx.t - i * gap
                if tt < self.t0:
                    continue
                st = objs[who].state(tt, ctx.W)
                look = rig.Look(color=self.COLORS[i % len(self.COLORS)], glow=0.5, alpha=0.55 * (1 - i / (n + 1)),
                                legs=st.look.legs, build=st.look.build)
                c.saveLayer(skia.Rect(st.x - st.s * 8, st.y - st.s * 9, st.x + st.s * 8, st.y + st.s * 6),
                            skia.Paint(BlendMode=gfx.ADD))
                rig.draw_figure(c, st.pose, st.x, st.y, st.s, facing=st.facing, look=look)
                c.restore()
        ctx.add("main", draw, z=-2)


# ----------------------------------------------------------------------------- misc


class SpeedLines(VFX):
    default_dur = 1.0

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        a = float(self.ev.get("a", 0.5)) * (1 - win(lt, self.dur - 0.2, self.dur))
        color = self.ev.get("color", "white")
        ctx.add("screen", lambda c: speed_lines(c, ctx.W / 2, ctx.H / 2, ctx.W * 1.1, ctx.T, color=color, a=a,
                                                n=50, inner=0.42), z=1)


class Slash(VFX):
    default_dur = 0.6

    def sounds(self):
        return [(0.0, "slash", 0.9)]

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        W, H = ctx.W, ctx.H
        rnd = random.Random(self.seed)
        n = int(self.ev.get("count", 5))

        def draw(c):
            for i in range(n):
                d = i * 0.05
                p = win(lt, d, d + 0.12)
                fade = 1 - win(lt, d + 0.15, self.dur)
                x0, y0 = rnd.random() * W * 0.4, rnd.random() * H
                ang = -0.6 + rnd.random() * 1.2
                L = W * 1.4
                x1, y1 = x0 + math.cos(ang) * L * p, y0 + math.sin(ang) * L * p
                c.drawLine(x0, y0, x1, y1, gfx.paint("white", fade, stroke=3))
                c.drawLine(x0, y0, x1, y1, gfx.paint(self.ev.get("color", "#ef4444"), 0.7 * fade, stroke=12, blur=8,
                                                     blend=gfx.ADD))
        ctx.add("fx", draw, z=6)


class LightPillar(VFX):
    """A vertical beam of light shoots up (finished tower, ascension, level up)."""
    default_dur = 4.0

    def sounds(self):
        return [(0.0, "boom", 0.7), (0.0, "chime", 0.5), (0.05, "riser", 0.25)]

    def pre(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        if lt < 0.12:
            ctx.flash = max(ctx.flash, 0.55 * (1 - lt / 0.12))
            ctx.flash_c = "white"
        ctx.zoom_punch += 0.03 * (1 - win(lt, 0, 0.4)) ** 2
        ctx.shake = max(ctx.shake, 0.25 * (1 - win(lt, 0, 0.5)))

    def build(self, ctx, actors):
        lt = self.lt(ctx)
        if ctx.t < self.t0 or lt > self.dur:
            return
        base = anchor(ctx, self.ev.get("at", [0.5, 0.6]))
        color = self.ev.get("color", "white")
        w0 = float(self.ev.get("width", 60))
        grow = out_expo(win(lt, 0, 0.35))
        fade = 1 - win(lt, self.dur - 0.6, self.dur)
        burst = 1 - win(lt, 0.0, 0.8)
        w = w0 * (0.55 + 0.9 * burst)
        top = base[1] - (base[1] + 400) * grow

        def draw(c):
            if grow <= 0:
                return
            for k_, al in ((3.2, 0.05), (2.0, 0.08), (1.2, 0.14), (0.55, 0.35), (0.22, 0.7)):
                ww = w * k_
                sh = gfx.linear(0, top, 0, base[1], [(0, color, 0.0), (0.25, color, al * fade),
                                                     (1, color, al * fade * 1.2)])
                c.drawRect(skia.Rect(base[0] - ww / 2, top, base[0] + ww / 2, base[1]),
                           skia.Paint(AntiAlias=True, Shader=sh, BlendMode=gfx.ADD,
                                      MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, max(2, ww * 0.25))))
            # flare at the base
            r = w * (1.2 + 1.6 * burst)
            gfx.glow_circle(c, *base, r * 0.5, color, 0.9 * fade, spread=3.5)
            c.save()
            c.translate(*base)
            for ang in (0, 90):
                c.save()
                c.rotate(ang + lt * 20)
                c.drawPath(gfx.poly([(0, -r * 1.6), (r * 0.08, 0), (0, r * 1.6), (-r * 0.08, 0)]),
                           gfx.paint(color, 0.8 * fade, blend=gfx.ADD))
                c.restore()
            c.restore()
            # ring on the floor
            ring = win(lt, 0.0, 0.9)
            if 0 < ring < 1:
                c.save()
                c.scale(1, 0.18)
                c.drawCircle(base[0], float(self.ev.get("floor", base[1])) / 0.18, 40 + ring * 520,
                             gfx.paint(color, (1 - ring) * 0.7, stroke=6 / 0.18 * 0.2 + 3))
                c.restore()
            # particles rising in the beam
            rnd = random.Random(self.seed + 5)
            for i in range(40):
                ph = (lt * (0.4 + rnd.random() * 0.8) + rnd.random()) % 1.0
                yy = base[1] - ph * (base[1] - top)
                xx = base[0] + (rnd.random() - 0.5) * w * 1.6
                c.drawCircle(xx, yy, 1.5 + rnd.random() * 2, gfx.paint(color, 0.7 * fade * (1 - ph), blend=gfx.ADD))
        ctx.add(self.ev.get("layer", "fx"), draw, z=3)


REGISTRY = {
    "hollow_purple": HollowPurple,
    "energy_orb": EnergyOrb,
    "domain": Domain,
    "black_flash": BlackFlash,
    "impact": Impact,
    "system": SystemWindow,
    "shadow_rise": ShadowRise,
    "wheel": Wheel,
    "aura": Aura,
    "afterimage": Afterimage,
    "speedlines": SpeedLines,
    "slash": Slash,
    "light_pillar": LightPillar,
}


def make(ev: dict, shot: dict):
    cls = REGISTRY.get(ev.get("type", ""))
    if cls is None:
        print(f"[vfx] unknown type: {ev.get('type')}")
        return None
    return cls(ev, shot)
