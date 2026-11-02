"""Scene archetypes. Each one lays out its actors and draws its set.

Scenes (shot["scene"]):
  classroom  front view, rows of desks, labels + grade sheets (reference format)
  closeup    one actor, big, shallow depth of field
  study      side view, night grind at a desk: lamp, window night->dawn, clock, books
  board      side view, actor writing equations on a whiteboard
  arena      side view, dark void stage for fights / power moves
  void       front view, empty dark stage (good for domain / reveals)
  stage      front view, black stage, glossy floor, spotlights, block towers (newer reference look)
  tunnel     perspective fly-back through a perfectly round hole punched through the school
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
    hx = j.head[0]
    top = j.head[1] - st.s * 1.0
    lab_c = gfx.mix("#f4f4f2", "#8a8b90", 0.8 * st.dim)
    lab_a = st.alpha * (1 - 0.35 * st.dim)
    if label and st.show_label and st.label:
        if st.label_pos == "floor" and st.floor is not None:
            rig.draw_label(c, st.x, j.head[1], st.s * 1.25, st.label, a=lab_a, level=st.level, level_c=st.level_c,
                           level_text=st.level_text, glitch=st.glitch, t=ctx.t, color=lab_c,
                           base_y=st.floor + st.s * 1.7, size_k=0.6)
        else:
            top = rig.draw_label(c, hx, j.head[1] - st.s * 0.05, st.s, st.label, a=lab_a, level=st.level,
                                 level_c=st.level_c, level_text=st.level_text, glitch=st.glitch, t=ctx.t,
                                 color=lab_c)
    if st.sheet:
        k = out_back(min(1.0, st.sheet_t / 0.32))
        rot = math.sin(ctx.t * 2.1 + st.x * 0.01) * 2.0
        stamp_t = max(0.0, (st.sheet_t - 0.18) / 0.22)
        rig.draw_sheet(c, hx, top - st.s * 0.25, st.s * sheet_scale, st.sheet, a=st.alpha * min(1, st.sheet_t / 0.12),
                       scale=0.6 + 0.4 * k, rot=rot, stamp_t=stamp_t)
    if st.zzz:
        rig.draw_zzz(c, hx + st.s * 1.15, j.head[1] + st.s * 0.2, st.s, ctx.t, a=st.alpha)
    if st.sparkle > 0.01:
        rig.draw_sparkle(c, hx + st.s * 1.25, j.head[1] - st.s * 1.15, st.s * 0.55, ctx.t, a=st.sparkle * st.alpha)
    if st.emote:
        draw_bubble(c, hx + st.s * 1.05, j.head[1] - st.s * 1.25, st.s, st.emote, st.emote_t, st.emote_dur,
                    a=st.alpha)


def draw_bubble(c: skia.Canvas, x: float, y: float, s: float, text: str, lt: float, dur: float, *, a=1.0):
    """Small white speech bubble with dark mono text (reference style): '?', '!', 'HUH?'."""
    k = out_back(min(1.0, lt / 0.22))
    fade = min(1.0, (dur - lt) / 0.2) if dur > 0 else 1.0
    al = a * min(1.0, lt / 0.08) * max(0.0, fade)
    if al <= 0.01:
        return
    size = max(14.0, s * 0.62)
    fnt = gfx.font(gfx.MONO_XB, size)
    w = gfx.text_width(text, fnt, size * 0.05) + size * 0.9
    h = size * 1.45
    c.save()
    c.translate(x, y)
    c.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k)
    gfx.rrect(c, -w * 0.15 - 2, -h - 2, w + 4, h + 4, h * 0.45, gfx.paint(rig.OUTLINE_C, 0.9 * al))
    gfx.rrect(c, -w * 0.15, -h, w, h, h * 0.45, gfx.paint("#f4f4f2", al))
    tail = gfx.poly([(w * 0.05, -h * 0.12), (w * 0.28, -h * 0.12), (-w * 0.05, h * 0.38)])
    c.drawPath(tail, gfx.paint("#f4f4f2", al))
    gfx.draw_text(c, text, -w * 0.15 + w / 2, -h * 0.3, size=size, face=gfx.MONO_XB, c="#141416", a=al,
                  spacing=size * 0.05)
    c.restore()


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

    def reflection(self, ctx: Ctx) -> dict | None:
        """Glossy floor: {'floor': y, 'strength': 0..1, 'fade': px, 'blur': px} or None."""
        k = float(self.p.get("reflect", self.default_reflect))
        floor = getattr(self, "floor_y", None)
        if k <= 0 or floor is None:
            return None
        return {"floor": float(floor), "strength": k, "fade": float(self.p.get("reflect_fade", 560)),
                "blur": float(self.p.get("reflect_blur", 3.0)), "layers": ["back", "main", "fx"]}

    default_reflect = 0.0


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
    default_reflect = 0.22

    @property
    def floor_y(self):
        return self.FLOOR

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
    default_reflect = 0.2

    @property
    def floor_y(self):
        return self.FLOOR

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
    default_reflect = 0.3

    @property
    def floor_y(self):
        return float(self.p.get("floor", self.FLOOR))

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 70))
        x01 = float(spec.get("x", (idx + 1) / (n + 1)))
        floor = float(spec.get("floor", self.floor_y))
        return dict(x=x01 * self.W, x01=x01, y=floor - 4 * s, s=s, layer=spec.get("layer", "main"),
                    facing=int(spec.get("facing", 1 if x01 < 0.5 else -1)), pose="stance", floor=floor)

    def build(self, ctx, actors):
        W, H = self.W, self.H
        tint = self.p.get("tint", "#1a1b20")
        spot = float(self.p.get("spot", 0.6))
        floor = self.floor_y

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

    @property
    def floor_y(self):
        return float(self.p.get("floor", 1560))

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 90))
        x01 = float(spec.get("x", (idx + 1) / (n + 1)))
        floor = float(spec.get("floor", self.floor_y))
        return dict(x=x01 * self.W, x01=x01, y=floor - 4 * s, s=s, layer=spec.get("layer", "main"), facing=1,
                    pose="stand", floor=floor)


# ----------------------------------------------------------------------------- stage (newer reference videos)


class Stage(Scene):
    """Black stage, glossy floor, a volumetric spotlight per actor, block towers,
    labels on the floor. Front view, slim figures."""
    name = "stage"
    FLOOR = 1340
    default_reflect = 0.42

    @property
    def floor_y(self):
        return float(self.p.get("floor", self.FLOOR))

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", self.p.get("s", 30)))
        x01 = float(spec.get("x", (idx + 1) / (n + 1)))
        return dict(x=x01 * self.W, x01=x01, y=self.floor_y - 9 * s, s=s, layer=spec.get("layer", "main"),
                    facing=1, pose="stand", floor=self.floor_y, build=spec.get("build", "slim"),
                    label_pos=spec.get("label_pos", self.p.get("label_pos", "floor")), glow=0.3,
                    spot=1.0)

    def build(self, ctx, actors):
        W, H = self.W, self.H
        floor = self.floor_y
        t = ctx.t
        objs = getattr(ctx, "actor_objs", {})
        spot_k = float(self.p.get("spot", 1.0))
        bw_k, bh_k = float(self.p.get("block_w", 1.9)), float(self.p.get("block_h", 0.62))

        def bg(c):
            props.stage_backdrop(c, W, H, floor, haze=float(self.p.get("haze", 0.7)))
        ctx.add("bg", bg)

        def beams(c):
            for st in actors.values():
                a = spot_k * st.spot * st.alpha
                if a <= 0.01:
                    continue
                props.spotlight(c, st.x + st.s * 1.2 * (1 if objs.get(st.id) and objs[st.id].stacks else 0),
                                floor, top_y=float(self.p.get("spot_top", -150)),
                                w_top=st.s * 2.6, w_bottom=st.s * float(self.p.get("spot_w", 14)), a=a,
                                t=t, seed=hash(st.id) % 100)
            for extra in self.p.get("spots", []):
                props.spotlight(c, extra.get("x", 0.5) * W, floor, w_top=extra.get("w_top", 70),
                                w_bottom=extra.get("w", 420), a=extra.get("a", 0.6), t=t, seed=7)
        ctx.add("bgfx", beams)

        def main(c):
            for st in sorted(actors.values(), key=lambda a: a.s):
                if st.layer != "main":
                    continue
                ob = objs.get(st.id)
                side = ob.tower_side if ob else 1
                bw, bh = st.s * bw_k, st.s * bh_k
                tx = st.x + side * st.s * 3.1
                has_tower = ob is not None and (ob.stacks or ob.tower_base > 0 or ob.spec.get("tower"))
                if has_tower:
                    pile0 = int(ob.spec.get("pile", 12))
                    pile_n = max(3, pile0 - (st.tower - st.tower_base))
                    props.block_pile(c, st.x - side * st.s * 3.0, floor, bw * 0.85, bh * 0.9, pile_n,
                                     a=st.alpha, dim=0.45 + 0.3 * st.dim, cols=2)
                    props.pedestal(c, tx, floor, bw * 1.25, bh * 0.7, a=st.alpha)
                    base_y = floor - bh * 0.7
                    for i in range(st.tower):
                        rig.draw_block(c, tx, base_y - i * (bh + 2), bw, bh, a=st.alpha,
                                       glow=0.55 * (1 - 0.8 * st.dim),
                                       c=gfx.mix("#f2f2f0", "#8d8e92", 0.75 * st.dim))
                draw_actor(c, st, ctx)
                if st.carrying and st.joints is not None:
                    j = st.joints
                    hx = (j.ha["l"][0] + j.ha["r"][0]) / 2
                    hy = (j.ha["l"][1] + j.ha["r"][1]) / 2 + bh * 0.4
                    rig.draw_block(c, hx, hy, bw, bh, a=st.alpha, glow=0.5,
                                   c=gfx.mix("#f2f2f0", "#8d8e92", 0.75 * st.dim))
        ctx.add("main", main)

    def focus_point(self, st):
        return (st.x, st.y - st.s * 3.0)


# ----------------------------------------------------------------------------- tunnel (the hole through the school)


class Tunnel(Scene):
    """Perspective view down a perfectly round hole punched through the school.

    The camera flies backwards, away from the hero, through the holes:
    hero's classroom -> classroom wall (lockers on the corridor side) -> corridor ->
    the next room's wall -> the school facade -> night outside. The hero stays at the
    far end of the hole.

    Units: x/y in 'local px' (100 = 1 m), hole axis at (0, 0), y down;
    z in metres along the hole (hero plane z = 0, camera at negative z).
    """
    name = "tunnel"
    R = 125.0
    FLOOR = 111.0
    CEIL = -265.0
    BX = 900.0
    BTOP, BBOT = -650.0, 460.0

    def __init__(self, shot, scenario, W, H):
        super().__init__(shot, scenario, W, H)
        from scipy.interpolate import PchipInterpolator
        path = self.p.get("cam", [[0.0, -1.6], [0.7, -2.0], [3.3, -21.0], [4.6, -24.0]])
        ts = [float(a) for a, _ in path]
        zs = [float(b) for _, b in path]
        self._cam = PchipInterpolator(ts, zs, extrapolate=True)
        self._t0, self._t1 = ts[0], ts[-1]
        self.F = float(self.p.get("F", 4.5))
        self.AY = float(self.p.get("axis_y", 0.46)) * H
        self.walls = self.p.get("walls", [
            {"z": -3.0, "th": 0.3, "kind": "lockers"},
            {"z": -6.0, "th": 0.3, "kind": "lab"},
            {"z": -12.0, "th": 0.45, "kind": "facade"},
        ])
        self.back_z = float(self.p.get("back_z", 3.0))

    def layout(self, aid, spec, idx, n):
        s = float(spec.get("s", 21.7))
        x = float(spec.get("lx", 0.0))
        if spec.get("seated"):
            return dict(x=x, x01=0.5, y=float(spec.get("ly", 66.0)), s=s, layer="main", facing=1, pose="sit",
                        legs=False)
        return dict(x=x, x01=0.5, y=0.0, s=s, layer="main", facing=1, pose="stand", floor=self.FLOOR)

    # --- projection --------------------------------------------------------
    def cam_z(self, t):
        return float(self._cam(min(max(t, self._t0), self._t1)))

    def k(self, z, cz):
        return self.F / max(1e-3, z - cz)

    def P(self, x, y, z, cz):
        kk = self.k(z, cz)
        return (self.W / 2 + x * kk, self.AY + y * kk)

    def _plane_quad(self, c, cz, y, z0, z1, x0, x1, color0, color1, a=1.0):
        """Horizontal plane (floor / ceiling / ground) between z0..z1, x0..x1 at height y."""
        near = cz + 0.06
        z0 = max(z0, near)
        if z1 <= z0:
            return
        q = [self.P(x0, y, z0, cz), self.P(x1, y, z0, cz), self.P(x1, y, z1, cz), self.P(x0, y, z1, cz)]
        ya, yb = q[0][1], q[2][1]
        sh = gfx.linear(0, ya, 0, yb, [(0, color0, a), (1, color1, a)])
        c.drawPath(gfx.poly(q), skia.Paint(AntiAlias=True, Shader=sh))

    def _side_quad(self, c, cz, x, z0, z1, y0, y1, color, a=1.0):
        near = cz + 0.06
        z0 = max(z0, near)
        if z1 <= z0:
            return
        q = [self.P(x, y0, z0, cz), self.P(x, y0, z1, cz), self.P(x, y1, z1, cz), self.P(x, y1, z0, cz)]
        c.drawPath(gfx.poly(q), gfx.paint(color, a))

    # --- wall faces (drawn in local px of the face plane) -----------------
    def _face_details(self, c, kind, t):
        R, F_, C_ = self.R, self.FLOOR, self.CEIL
        if kind == "lockers":
            c.drawRect(skia.Rect(-self.BX, C_ - 140, self.BX, F_ + 140), skia.Paint(
                Shader=gfx.linear(0, C_, 0, F_, [(0, "#2a2c33", 1), (1, "#202128", 1)])))
            c.drawRect(skia.Rect(-self.BX, C_ - 140, self.BX, C_), gfx.paint("#121215"))
            c.drawRect(skia.Rect(-self.BX, F_, self.BX, F_ + 140), gfx.paint("#121215"))
            for i in range(-20, 21):
                x0 = i * 46.0
                top = F_ - 190
                c.drawRect(skia.Rect(x0 + 2, top, x0 + 44, F_ - 6), skia.Paint(
                    Shader=gfx.linear(0, top, 0, F_, [(0, "#4a4f5c", 1), (1, "#353945", 1)])))
                c.drawRect(skia.Rect(x0 + 2, top, x0 + 44, F_ - 6), gfx.paint("#121317", 1, stroke=2.5,
                                                                               cap_round=False))
                for v in range(4):
                    c.drawLine(x0 + 12, top + 16 + v * 7, x0 + 34, top + 16 + v * 7, gfx.paint("#20222a", 1, stroke=2))
                c.drawRect(skia.Rect(x0 + 34, top + 90, x0 + 38, top + 112), gfx.paint("#8a8f9c"))
            c.drawRect(skia.Rect(-self.BX, F_ - 8, self.BX, F_), gfx.paint("#0e0e11"))
            for x in (-640, -260, 260, 640):   # ceiling lights + their glow on the wall
                c.drawRect(skia.Rect(x - 70, C_ + 4, x + 70, C_ + 14), gfx.paint("#e8eef7", 0.75))
                gfx.glow_circle(c, x, C_ + 30, 120, "#dfe8ff", 0.12, spread=2.2)
        elif kind == "lab":
            c.drawRect(skia.Rect(-self.BX, C_ - 140, self.BX, F_ + 140), gfx.paint("#23242a"))
            c.drawRect(skia.Rect(-self.BX, C_ - 140, self.BX, C_), gfx.paint("#121215"))
            c.drawRect(skia.Rect(-self.BX, F_, self.BX, F_ + 140), gfx.paint("#121215"))
            # whiteboard cut by the hole + formulas (callback to the grind montage)
            c.drawRect(skia.Rect(-430, -205, 430, 25), gfx.paint("#4a4c53"))
            c.drawRect(skia.Rect(-420, -195, 420, 15), gfx.paint("#d9d9d4"))
            for i, txt in enumerate(["2X+7=19", "X=6", "3X+6=9"]):
                gfx.draw_text(c, txt, -400, -160 + i * 42, size=30, face=gfx.MONO_MED, c="#3a3b40", align="left")
            for i, txt in enumerate(["F=ma", "E=mc2"]):
                gfx.draw_text(c, txt, 190, -140 + i * 50, size=30, face=gfx.MONO_MED, c="#3a3b40", align="left")
            props.wall_clock(c, 600, -170, 32, 9.1)
            c.drawRect(skia.Rect(-800, -150, -600, 60), gfx.paint("#2b2c33"))       # poster
            c.drawRect(skia.Rect(-790, -140, -610, 50), gfx.paint("#1d3557", 0.6))
        elif kind == "facade":
            bx0, bx1, by0, by1 = -self.BX, self.BX, self.BTOP, self.BBOT
            c.drawRect(skia.Rect(bx0, by0, bx1, by1), skia.Paint(
                Shader=gfx.linear(0, by0, 0, by1, [(0, "#1c1d23", 1), (1, "#141519", 1)])))
            c.drawRect(skia.Rect(bx0 - 30, by0 - 30, bx1 + 30, by0 + 10), gfx.paint("#0f1013"))  # roof ledge
            for yy in (-280, 110):  # slab lines between storeys
                c.drawRect(skia.Rect(bx0, yy, bx1, yy + 14), gfx.paint("#101114"))
            rnd = random.Random(4)
            for row, cy in enumerate((-470, -85, 285)):
                for cx in (-760, -500, -240, 240, 500, 760):
                    lit = rnd.random() < 0.35
                    col_ = "#f5c77e" if lit else "#16233a"
                    c.drawRect(skia.Rect(cx - 82, cy - 100, cx + 82, cy + 100), gfx.paint("#0c0c0f"))
                    c.drawRect(skia.Rect(cx - 72, cy - 90, cx + 72, cy + 90), gfx.paint(col_, 0.85 if lit else 0.9))
                    c.drawLine(cx, cy - 90, cx, cy + 90, gfx.paint("#0c0c0f", 1, stroke=8, cap_round=False))
                    c.drawLine(cx - 72, cy, cx + 72, cy, gfx.paint("#0c0c0f", 1, stroke=8, cap_round=False))
                    if lit:
                        gfx.glow_circle(c, cx, cy, 90, "#f5c77e", 0.12, spread=2.0)
            # entrance + sign
            c.drawRect(skia.Rect(-110, 250, 110, by1), gfx.paint("#0b0b0d"))
            c.drawRect(skia.Rect(-96, 264, 96, by1), gfx.paint("#e8d9b5", 0.35))
            gfx.draw_text(c, "H I G H   S C H O O L", 0, 228, size=34, face=gfx.MONO_XB, c="#d6d6d2", a=0.85)

    def _wall(self, c, cz, wall, t, heat):
        zf, th, kind = float(wall["z"]), float(wall.get("th", 0.3)), wall.get("kind", "lockers")
        zb = zf + th
        R = self.R
        W, H = self.W, self.H
        if zb <= cz + 0.02:
            return  # completely behind the camera
        if zf <= cz + 0.02 < zb:
            # the camera is inside the cut: the cylinder wall surrounds the frame
            kb = self.k(zb, cz)
            cx, cy = W / 2, self.AY
            pth = skia.Path()
            pth.setFillType(skia.PathFillType.kEvenOdd)
            pth.addRect(skia.Rect(-W, -H, 2 * W, 2 * H))
            pth.addCircle(cx, cy, R * kb)
            c.drawPath(pth, gfx.paint("#2a2a30"))
            c.drawCircle(cx, cy, R * kb, gfx.paint("#a855f7", 0.9 * heat, stroke=6, blur=6, blend=gfx.ADD))
            return
        kf, kb = self.k(zf, cz), self.k(zb, cz)
        c.save()
        c.translate(W / 2, self.AY)
        c.scale(kf, kf)
        if kind == "facade":
            bounds = skia.Rect(-self.BX - 30, self.BTOP - 30, self.BX + 30, self.BBOT)
        else:
            bounds = skia.Rect(-self.BX, self.CEIL - 140, self.BX, self.FLOOR + 140)
        hole = skia.Path()
        hole.setFillType(skia.PathFillType.kEvenOdd)
        hole.addRect(bounds)
        hole.addCircle(0, 0, R)
        c.save()
        c.clipPath(hole, doAntiAlias=True)
        self._face_details(c, kind, t)
        c.restore()
        # the cut: inner surface of the cylinder between the front and back face
        rb = R * kb / kf
        ring = skia.Path()
        ring.setFillType(skia.PathFillType.kEvenOdd)
        ring.addCircle(0, 0, R)
        ring.addCircle(0, 0, rb)
        c.drawPath(ring, skia.Paint(AntiAlias=True, Shader=gfx.radial(0, 0, R, [
            (0, "#3a3046", 1), (rb / R, "#2f2a38", 1), (1, "#1a1a1f", 1)])))
        c.drawPath(ring, skia.Paint(AntiAlias=True, Shader=gfx.radial(0, 0, R, [
            (rb / R, "#a855f7", 0.0), (1, "#a855f7", 0.18 * heat)]), BlendMode=gfx.ADD))
        # still-hot rims (front and back edge); widths are kept constant on screen
        inv = 1.0 / max(kf, 1e-3)
        c.drawCircle(0, 0, R, gfx.paint("#7c3aed", 0.6 * heat, stroke=18 * inv, blur=9 * inv, blend=gfx.ADD))
        c.drawCircle(0, 0, R, gfx.paint("#e9d5ff", 0.85 * heat, stroke=2.4 * inv))
        c.drawCircle(0, 0, rb, gfx.paint("#c084fc", 0.45 * heat, stroke=1.8 * inv))
        c.restore()

    def build(self, ctx, actors):
        W, H = self.W, self.H
        t = ctx.t
        cz = self.cam_z(t)
        heat = 1.0 - 0.6 * gfx.clamp(t / 4.5)
        rnd_stars = random.Random(9)

        def bg(c):
            c.drawRect(skia.Rect(-W, -H, 2 * W, 2 * H), skia.Paint(
                Shader=gfx.linear(0, 0, 0, H, [(0, "#04060c", 1), (0.55, "#0b1222", 1), (1, "#141a2a", 1)])))
            for _ in range(160):
                x, y = rnd_stars.random() * W, rnd_stars.random() * H * 0.62
                c.drawCircle(x, y, 0.6 + rnd_stars.random() * 1.6,
                             gfx.paint("white", 0.25 + 0.6 * rnd_stars.random() * (0.6 + 0.4 * math.sin(t * 3 + x))))
            gfx.glow_circle(c, W * 0.8, H * 0.12, 46, "#e7ecff", 0.5, spread=3.5)
            c.drawCircle(W * 0.8, H * 0.12, 44, gfx.paint("#eef2ff", 0.95))
        ctx.add("bg", bg)

        def main(c):
            # ground outside (seen once the camera leaves the building)
            self._plane_quad(c, cz, self.BBOT, cz, 80.0, -8000, 8000, "#0e1016", "#07080b")
            # hero's classroom: back wall billboard, floor, ceiling, side walls
            kb_ = self.k(self.back_z, cz)
            c.save()
            c.translate(W / 2, self.AY)
            c.scale(kb_, kb_)
            c.drawRect(skia.Rect(-self.BX, self.CEIL, self.BX, self.FLOOR + 2), skia.Paint(
                Shader=gfx.linear(0, self.CEIL, 0, self.FLOOR, [(0, "#23252c", 1), (1, "#1a1b20", 1)])))
            for wx in (-560, 400):
                props.window(c, wx, -215, 170, 190, sky="night", glow=0.8)
            props.wall_clock(c, 60, -200, 26, 9.3 + t * 0.002)
            c.restore()
            z_front = float(self.walls[0]["z"]) + float(self.walls[0].get("th", 0.3))
            self._plane_quad(c, cz, self.FLOOR, z_front, self.back_z, -self.BX, self.BX, "#16171b", "#1d1e23")
            self._plane_quad(c, cz, self.CEIL, z_front, self.back_z, -self.BX, self.BX, "#0f1013", "#17181c")
            for sx in (-self.BX, self.BX):
                self._side_quad(c, cz, sx, z_front, self.back_z, self.CEIL, self.FLOOR, "#1b1c21")
            # residual violet glow where the sphere was born + the people at z = 0
            k0 = self.k(0.0, cz)
            c.save()
            c.translate(W / 2, self.AY)
            c.scale(k0, k0)
            gfx.glow_circle(c, 0, 0, 120, "#7c3aed", 0.25 * heat, spread=2.4)
            props.floor_shadow(c, 0, self.FLOOR + 2, 60, 0.6)
            for st in sorted(actors.values(), key=lambda a: abs(a.x)):
                if st.look.legs is False:
                    draw_actor(c, st, ctx)
                    props.desk_front(c, st.x, self.FLOOR - 40, 120, 42, paper=True, paper_glow=0.4)
                else:
                    draw_actor(c, st, ctx)
            rnd = random.Random(21)
            for i in range(14):  # smoke settling around him
                ph = (t * 0.12 + rnd.random()) % 1.0
                sx_ = (rnd.random() - 0.5) * 520
                sy_ = self.FLOOR - 20 - ph * 220
                c.drawCircle(sx_, sy_, 40 + 70 * ph, gfx.paint("#8b8a99", 0.10 * (1 - ph), blur=30))
            c.restore()
            # walls and rooms, far to near
            ws = sorted(self.walls, key=lambda w: -float(w["z"]))
            for i, wall in enumerate(ws):
                self._wall(c, cz, wall, t, heat)
                if i + 1 < len(ws):
                    nxt = ws[i + 1]
                    z0 = float(nxt["z"]) + float(nxt.get("th", 0.3))
                    z1 = float(wall["z"])
                    if nxt.get("kind") == "facade" or wall.get("kind") != "facade":
                        self._plane_quad(c, cz, self.FLOOR, z0, z1, -self.BX, self.BX, "#141519", "#1a1b1f")
                        self._plane_quad(c, cz, self.CEIL, z0, z1, -self.BX, self.BX, "#0d0e10", "#141518")
        ctx.add("main", main)

        def fx(c):
            # embers and dust drifting inside the hole (always visible through the holes)
            rnd = random.Random(33)
            for i in range(90):
                zz = -12.5 + rnd.random() * 12.3
                if zz <= cz + 0.08:
                    continue
                ang = rnd.random() * 2 * math.pi
                rr = self.R * (0.35 + 0.6 * rnd.random())
                x = math.cos(ang) * rr + math.sin(t * 0.9 + i) * 12
                y = math.sin(ang) * rr - ((t * 18 * (0.4 + rnd.random())) % 160) + 60
                kk = self.k(zz, cz)
                px, py = W / 2 + x * kk, self.AY + y * kk
                rad = max(0.8, 2.2 * kk)
                col_ = "#c084fc" if i % 3 else "#fde68a"
                c.drawCircle(px, py, rad, gfx.paint(col_, 0.75 * heat * min(1.0, kk), blend=gfx.ADD))
        ctx.add("fx", fx)

    def focus_point(self, st):
        return (self.W / 2, self.H / 2)


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
                sf = gfx.font(gfx.MONO, 34)
                for i, sl in enumerate(gfx.wrap(sub, sf, W * 0.86, spacing=7)):
                    gfx.draw_text(c, sl, W / 2, ly + 90 + i * 50, size=34, face=gfx.MONO, c="#cfcfcb", a=a,
                                  spacing=7)
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


SCENES = {cls.name: cls for cls in (Classroom, Closeup, Study, Board, Arena, Void, Stage, Tunnel, Title)}
