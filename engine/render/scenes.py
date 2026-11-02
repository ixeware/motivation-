"""Scene archetypes. Each one lays out its actors and draws its set.

Scenes (shot["scene"]):
  classroom  front view, rows of desks, labels + grade sheets (reference format)
  closeup    one actor, big, shallow depth of field
  study      side view, night grind at a desk: lamp, window night->dawn, clock, books
  board      side view, actor writing equations on a whiteboard
  arena      side view, dark void stage for fights / power moves
  void       front view, empty dark stage (good for domain / reveals)
  title      end card: big quote + mono subtitle + seal
"""
from __future__ import annotations

import math
import random

import skia

from . import gfx, props, rig
from .easing import out_back, out_cubic, window as win
from .timeline import ActorState, Ctx


# ----------------------------------------------------------------------------- shared drawing


def draw_actor(c: skia.Canvas, st: ActorState, ctx: Ctx, *, label=True, sheet_scale=1.0):
    if st.alpha <= 0.01:
        return
    j = rig.draw_figure(c, st.pose, st.x, st.y, st.s, facing=st.facing, look=st.look, t=ctx.t)
    st.joints = j
    head_top = j.head[1]
    hx = j.head[0]
    top = head_top - st.s * 1.0
    if label and st.show_label and st.label:
        top = rig.draw_label(c, hx, j.head[1] - st.s * 0.05 + st.s * min(0.0, -st.pose.get("head_drop", 0) * 0.0),
                             st.s, st.label, a=st.alpha, level=st.level, level_c=st.level_c,
                             level_text=st.level_text, glitch=st.glitch, t=ctx.t)
    if st.sheet:
        k = out_back(min(1.0, st.sheet_t / 0.32))
        rot = math.sin(ctx.t * 2.1 + st.x * 0.01) * 2.0
        stamp_t = max(0.0, (st.sheet_t - 0.18) / 0.22)
        rig.draw_sheet(c, hx, top - st.s * 0.25, st.s * sheet_scale, st.sheet, a=st.alpha * min(1, st.sheet_t / 0.12),
                       scale=0.6 + 0.4 * k, rot=rot, stamp_t=stamp_t)
    if st.zzz:
        rig.draw_zzz(c, hx + st.s * 1.15, j.head[1] + st.s * 0.2, st.s, ctx.t, a=st.alpha)


def _rnd(seed):
    return random.Random(seed)


class Scene:
    name = "base"
    default_focus = "main"

    def __init__(self, shot: dict, scenario: dict, W: int, H: int):
        self.shot = shot
        self.scenario = scenario
        self.p = shot.get("params", {})
        self.W, self.H = W, H

    def layout(self, aid: str, spec: dict, idx: int, n: int) -> dict:
        x01 = float(spec.get("x", (idx + 1) / (n + 1)))
        return dict(x=x01 * self.W, y=self.H * 0.6, s=70, layer="main", x01=x01, facing=1)

    def build(self, ctx: Ctx, actors: dict[str, ActorState]):
        raise NotImplementedError

    def focus_point(self, st: ActorState):
        return (st.x, st.y - st.s * 2.2)


# ----------------------------------------------------------------------------- classroom


class Classroom(Scene):
    """Reference look: dark classroom, three archetypes at desks, labels and grades."""
    name = "classroom"
    HORIZON = 905
    DESK_Y = 1330

    def layout(self, aid, spec, idx, n):
        n = max(n, 1)
        margin = 205 if n >= 3 else 300
        seat = spec.get("seat", idx)
        if "x" in spec:
            x01 = float(spec["x"])
        elif n == 1:
            x01 = 0.5
        else:
            x01 = (margin + (self.W - 2 * margin) * seat / (n - 1)) / self.W
        s = float(spec.get("s", 64))
        d = 300 * 0.22
        return dict(x=x01 * self.W, x01=x01, y=self.DESK_Y - d * 1.02 + (64 - s) * 0.0, s=s, layer="main",
                    facing=1, legs=False, pose="sit")

    def build(self, ctx, actors):
        W, H = self.W, self.H
        t = ctx.t
        sky = self.p.get("sky", "night")
        hours = self.p.get("clock", 9.2) + t * self.p.get("clock_speed", 0.01)

        def bg(c):
            props.room(c, W, H, self.HORIZON)
            props.window(c, -40, 470, 210, 330, sky=sky, glow=0.9)
            props.window(c, W - 170, 470, 210, 330, sky=sky, glow=0.9)
            props.wall_clock(c, W * 0.66, 560, 24, hours)
            c.drawRect(skia.Rect(W * 0.28, 600, W * 0.6, 820), gfx.paint("#2a2b30"))   # blackboard frame
            c.drawRect(skia.Rect(W * 0.29, 610, W * 0.59, 810), gfx.paint("#202226"))
        ctx.add("bg", bg)

        rnd = _rnd(7)
        extras = int(self.p.get("extras", 1))

        def back(c):
            if not extras:
                return
            for row, (dy, s, xs) in enumerate([(1010, 26, [150, 360, 560, 760, 960]),
                                               (1110, 38, [70, 310, 545, 780, 1010])]):
                for i, x in enumerate(xs):
                    pose = rig.pose_dict("sit" if (i + row) % 3 else "sit_relaxed")
                    hip_y = dy - 300 * 0.22 * (s / 64) * 1.0
                    rig.draw_figure(c, pose, x, hip_y, s, look=rig.Look(color="#a9aaae", glow=0.1, legs=False))
                    props.desk_front(c, x, dy, 300 * s / 64, 330 * s / 64, shade_k=0.8 - 0.1 * row,
                                     paper_glow=0.3)
        ctx.add("back", back)

        # main row: actor then its desk (desk occludes legs)
        def main(c):
            order = sorted(actors.values(), key=lambda a: a.y)
            for st in order:
                if st.layer != "main":
                    continue
                draw_actor(c, st, ctx)
                props.desk_front(c, st.x, self.DESK_Y + (st.s - 64) * 0.9, 300 * st.s / 64, 360 * st.s / 64)
        ctx.add("main", main)

        walker = self.p.get("walker")

        def front(c):
            # foreground: big blurry desks + backs of heads (reference depth)
            props.desk_front(c, -60, 1760, 560, 420, shade_k=0.75, paper=False)
            props.desk_front(c, W + 60, 1790, 560, 420, shade_k=0.75, paper=False)
            if self.p.get("front_heads", True):
                rig.draw_figure(c, rig.pose_dict("sit"), W - 40, 1830, 120,
                                look=rig.Look(color="#cfcfcf", glow=0.0, legs=False))
            if walker:
                ws = walker.get("s", 86)
                p_ = win(t, walker.get("t0", 0), walker.get("t1", ctx.dur))
                x = gfx.lerp(walker.get("from", -0.15), walker.get("to", 1.15), p_) * W
                fy = walker.get("floor", 1960)
                pose = rig.apply_mods(rig.pose_dict("stand_side"), {"walk": 1.0}, t)
                hip = fy - rig.ground_offset(pose, ws)
                face = 1 if walker.get("to", 1.15) > walker.get("from", -0.15) else -1
                if 0 < p_ < 1:
                    rig.draw_figure(c, pose, x, hip, ws, facing=face, look=rig.Look(color="#d8d8d8", glow=0.0))
                    if walker.get("carry", True):
                        j = rig.solve(pose, x, hip, ws, face)
                        hx, hy = j.ha["r"]
                        c.drawRect(skia.Rect(hx - ws * 0.6, hy - ws * 0.9, hx + ws * 0.6, hy + ws * 0.1),
                                   gfx.paint("paper"))
        ctx.add("front", front)

        for st in actors.values():
            if st.layer in ("back", "front"):
                ctx.add(st.layer, lambda c, st=st: draw_actor(c, st, ctx))


# ----------------------------------------------------------------------------- close-up


class Closeup(Scene):
    name = "closeup"

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 190))
        x01 = float(spec.get("x", 0.5))
        return dict(x=x01 * self.W, x01=x01, y=float(spec.get("hip_y", 1560)), s=s, layer="main", facing=1,
                    legs=False, pose="sit")

    def build(self, ctx, actors):
        W, H = self.W, self.H
        sky = self.p.get("sky", "night")

        def bg(c):
            props.room(c, W, H, 1000)
            props.window(c, 40, 380, 260, 420, sky=sky, glow=1.0)
            props.window(c, W - 300, 380, 260, 420, sky=sky, glow=1.0)
            props.wall_clock(c, W * 0.72, 300, 40, 9.5 + ctx.t * 0.02)
            for i, x in enumerate([180, 520, 880]):
                rig.draw_figure(c, rig.pose_dict("sit"), x, 1060, 55, look=rig.Look(color="#8f9094", glow=0.0,
                                                                                    legs=False))
                props.desk_front(c, x, 1110, 260, 300, shade_k=0.7)
        ctx.add("bg", bg)

        def main(c):
            for st in actors.values():
                draw_actor(c, st, ctx, sheet_scale=0.9)
                if self.p.get("desk", True):
                    props.desk_front(c, st.x, st.y + st.s * 1.05, st.s * 4.6, st.s * 4.0, paper=True)
        ctx.add("main", main)

    def focus_point(self, st):
        return (st.x, st.y - st.s * 2.6)


# ----------------------------------------------------------------------------- study (grind montage)


class Study(Scene):
    """Night grind: lamp, window night->dawn, spinning clock, growing book stack."""
    name = "study"
    FLOOR = 1500

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 82))
        x01 = float(spec.get("x", 0.34))
        pose = rig.pose_dict(spec.get("pose", "write"))
        hip_y = self.FLOOR - s * 2.05
        return dict(x=x01 * self.W, x01=x01, y=hip_y, s=s, layer="main", facing=1, pose="write")

    def build(self, ctx, actors):
        W, H = self.W, self.H
        t, dur = ctx.t, ctx.dur
        prog = win(t, 0, dur)
        dawn = gfx.clamp((prog - self.p.get("dawn_at", 0.55)) / 0.45) if self.p.get("dawn", True) else 0.0
        sky = gfx.mix("night", "dawn", dawn)
        h0, h1 = self.p.get("hours", [23.0, 30.5])
        hours = gfx.lerp(h0, h1, prog)
        lamp_on = 1.0 - gfx.clamp((dawn - 0.85) / 0.15) * float(self.p.get("lamp_off", 0))
        st0 = next(iter(actors.values()), None)
        ax = st0.x if st0 else W * 0.34
        s = st0.s if st0 else 82
        desk_y = self.FLOOR - s * 3.55
        desk_x0, desk_x1 = ax + s * 1.4, ax + s * 7.4
        n0, n1 = self.p.get("books", [1, 7])
        nbooks = int(round(gfx.lerp(n0, n1, prog)))

        def bg(c):
            props.room(c, W, H, self.FLOOR - 40, wall_top="#1f2024", wall_bot="#18191c")
            props.window(c, 70, 330, 300, 470, sky=sky, glow=1.0 + dawn)
            props.wall_clock(c, W * 0.64, 430, 46, hours)
            props.whiteboard(c, W * 0.8, 360, 420, 560, ["2X+7=19", "X=6"], 1.0, a=0.85)
            if dawn > 0:
                # morning sun shaft from the window
                shaft = gfx.poly([(70, 330), (370, 330), (W * 0.95, self.FLOOR + 60), (W * 0.2, self.FLOOR + 60)])
                c.drawPath(shaft, skia.Paint(AntiAlias=True, BlendMode=gfx.ADD,
                                             Shader=gfx.linear(0, 330, 0, self.FLOOR, [(0, "dawn", 0.22 * dawn),
                                                                                      (1, "dawn", 0.0)]),
                                             MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)))
        ctx.add("bg", bg)

        def main(c):
            props.chair_side(c, ax - s * 0.2, (st0.y if st0 else desk_y) + s * 0.32, self.FLOOR, s)
            props.desk_side(c, desk_x0, desk_y, desk_x1, self.FLOOR) if False else props.desk_side(
                c, desk_x0, desk_x1, desk_y, self.FLOOR)
            props.books(c, desk_x0 + s * 3.3, desk_y, s, nbooks)
            c.drawRect(skia.Rect(desk_x0 + s * 0.4, desk_y - 4, desk_x0 + s * 2.0, desk_y), gfx.paint("paper"))
            for st in actors.values():
                draw_actor(c, st, ctx)
            bulb = props.desk_lamp(c, desk_x1 - s * 0.9, desk_y, s, facing=-1, on=lamp_on)
            self._bulb = bulb
        ctx.add("main", main)

        def light(c):
            bulb = getattr(self, "_bulb", (desk_x1 - s * 2.0, desk_y - s * 3.6))
            props.lamp_light(c, bulb, desk_y, s, facing=-1, on=lamp_on * (0.95 + 0.05 * math.sin(t * 30)))
            # dust in the lamp light
            rnd = _rnd(11)
            for i in range(26):
                px = bulb[0] + (rnd.random() - 0.7) * s * 6
                py = bulb[1] + rnd.random() * s * 4 - (t * 12 * (0.5 + rnd.random())) % (s * 4)
                c.drawCircle(px, py, 1.6 + rnd.random() * 1.6, gfx.paint("lamp", 0.35 * lamp_on, blend=gfx.ADD))
        ctx.add("fx", light)

    def focus_point(self, st):
        return (st.x + st.s * 2.5, st.y - st.s * 1.5)


# ----------------------------------------------------------------------------- whiteboard


class Board(Scene):
    name = "board"
    FLOOR = 1680

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 96))
        x01 = float(spec.get("x", 0.22))
        pose = rig.pose_dict(spec.get("pose", "board_write"))
        return dict(x=x01 * self.W, x01=x01, y=self.FLOOR - rig.ground_offset(pose, s), s=s, layer="main",
                    facing=1, pose="board_write")

    def build(self, ctx, actors):
        W, H = self.W, self.H
        lines = self.p.get("lines", ["2X + 7 = 19", "X = 6", "3X + 6", "  ----- = 9", "    2", "X = 4", "Y = 4X + 1"])
        reveal = win(ctx.t, self.p.get("reveal_from", 0.0), ctx.dur * self.p.get("reveal_until", 0.95))
        bx, by, bw, bh = W * 0.30, 430, W * 0.78, 760

        def bg(c):
            props.room(c, W, H, self.FLOOR - 30)
        ctx.add("bg", bg)

        def main(c):
            props.whiteboard(c, bx, by, bw, bh, lines, reveal, size=64)
            for st in actors.values():
                draw_actor(c, st, ctx)
        ctx.add("main", main)


# ----------------------------------------------------------------------------- arena


class Arena(Scene):
    """Dark stage, side view. For fights, reveals and power moves."""
    name = "arena"
    HORIZON = 1180
    FLOOR = 1500

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 70))
        x01 = float(spec.get("x", (idx + 1) / (n + 1)))
        pose = rig.pose_dict(spec.get("pose", "stance"))
        floor = float(spec.get("floor", self.p.get("floor", self.FLOOR)))
        y = floor - rig.ground_offset(pose, s, int(spec.get("facing", 1)))
        return dict(x=x01 * self.W, x01=x01, y=y, s=s, layer=spec.get("layer", "main"),
                    facing=int(spec.get("facing", 1 if x01 < 0.5 else -1)), pose="stance")

    def build(self, ctx, actors):
        W, H = self.W, self.H
        tint = self.p.get("tint", "#1a1b20")
        spot = float(self.p.get("spot", 0.6))
        floor = float(self.p.get("floor", self.FLOOR))

        def bg(c):
            props.void_floor(c, W, H, float(self.p.get("horizon", self.HORIZON)), tint=tint, spot=spot,
                             spot_c=self.p.get("spot_c", "white"))
        ctx.add("bg", bg)

        def main(c):
            for st in sorted(actors.values(), key=lambda a: a.s):
                if st.layer != "main":
                    continue
                if self.p.get("shadows", True):
                    props.floor_shadow(c, st.x, floor + 6, st.s * 1.6, 0.55 * st.alpha)
                draw_actor(c, st, ctx)
        ctx.add("main", main)
        for st in actors.values():
            if st.layer in ("back", "front"):
                ctx.add(st.layer, lambda c, st=st: draw_actor(c, st, ctx))


class Void(Arena):
    """Front-view empty stage (good for a hero reveal / domain)."""
    name = "void"

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 90))
        x01 = float(spec.get("x", (idx + 1) / (n + 1)))
        pose = rig.pose_dict(spec.get("pose", "stand"))
        floor = float(spec.get("floor", self.p.get("floor", 1560)))
        return dict(x=x01 * self.W, x01=x01, y=floor - rig.ground_offset(pose, s), s=s,
                    layer=spec.get("layer", "main"), facing=1, pose="stand")


# ----------------------------------------------------------------------------- title card


class Title(Scene):
    name = "title"

    def layout(self, aid, spec, idx, n):
        return dict(x=self.W / 2, x01=0.5, y=self.H * 0.7, s=60, layer="main", facing=1)

    def build(self, ctx, actors):
        W, H = self.W, self.H
        t = ctx.t
        lines = self.p.get("lines", ["SOMETIMES", "PRIDE IS FUEL."])
        sub = self.p.get("sub", "")
        accent = self.p.get("accent", self.scenario.get("style", {}).get("accent", "violet"))
        size = float(self.p.get("size", 104))
        seal = self.p.get("seal", self.scenario.get("style", {}).get("seal", ""))

        def bg(c):
            c.drawRect(skia.Rect(-W, -H, 2 * W, 2 * H), gfx.paint("#0a0a0c"))
            gfx.glow_circle(c, W / 2, H * 0.5, W * 0.35, accent, 0.10 + 0.04 * math.sin(t * 2), spread=2.4)
        ctx.add("bg", bg)

        def screen(c):
            fnt = gfx.font(gfx.DISPLAY, size)
            wrapped = []
            for ln in lines:
                wrapped += gfx.wrap(ln, fnt, W * 0.84)
            total_h = len(wrapped) * size * 1.12
            y0 = H * 0.46 - total_h / 2 + size
            k = 0
            for i, ln in enumerate(wrapped):
                words = ln.split(" ")
                x = W / 2 - gfx.text_width(ln, fnt) / 2
                for wd in words:
                    td = 0.15 + k * 0.09
                    a = out_cubic(win(t, td, td + 0.35))
                    dy = (1 - a) * 24
                    c_ = accent if wd.endswith("*") else "#f2f2f0"
                    wd_ = wd.rstrip("*")
                    gfx.draw_text(c, wd_, x, y0 + i * size * 1.12 + dy, size=size, face=gfx.DISPLAY, c=c_, a=a,
                                  align="left", glow=6 if c_ == accent else 0)
                    x += gfx.text_width(wd_ + " ", fnt)
                    k += 1
            ly = y0 + (len(wrapped) - 1) * size * 1.12 + size * 0.7
            lw = W * 0.18 * out_cubic(win(t, 0.4 + k * 0.09, 0.9 + k * 0.09))
            c.drawLine(W / 2 - lw, ly, W / 2 + lw, ly, gfx.paint(accent, 0.9, stroke=4))
            gfx.glow_circle(c, W / 2, ly, 10, accent, 0.6 * (lw > 1), spread=5)
            if sub:
                a = out_cubic(win(t, 0.9 + k * 0.09, 1.4 + k * 0.09))
                gfx.draw_text(c, sub, W / 2, ly + 90, size=34, face=gfx.MONO, c="#cfcfcb", a=a, spacing=7)
            if seal:
                a = win(t, 1.2 + k * 0.09, 1.35 + k * 0.09)
                sc = 1 + (1 - a) * 0.6
                sx, sy, ss = W / 2, H * 0.78, 64 * sc
                c.save()
                c.translate(sx, sy)
                c.rotate(-6)
                gfx.rrect(c, -ss, -ss, ss * 2, ss * 2, 10, gfx.paint("stamp", 0.9 * a))
                gfx.rrect(c, -ss * 0.84, -ss * 0.84, ss * 1.68, ss * 1.68, 6,
                          gfx.paint("#0a0a0c", 0.9 * a, stroke=5, cap_round=False))
                gfx.draw_text(c, seal, 0, ss * 0.36, size=ss * 1.0, face=gfx.DISPLAY, c="#0a0a0c", a=a)
                c.restore()
        ctx.add("screen", screen)


SCENES = {cls.name: cls for cls in (Classroom, Closeup, Study, Board, Arena, Void, Title)}
