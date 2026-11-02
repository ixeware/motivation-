"""Scenario -> frames -> mp4.

Pipeline per frame:
  shot lookup -> actor states -> scene + VFX fill layers -> per-layer depth of
  field + parallax camera -> grade, bloom, vignette -> UI (screen) -> grain
  -> impact frame / chroma / flash -> ffmpeg pipe.
"""
from __future__ import annotations

import math
import random
import shutil
import subprocess
from pathlib import Path

import numpy as np
import skia

from . import gfx, rig, vfx as vfxmod
from .easing import ease, window as win
from .scenes import SCENES
from .timeline import Actor, Ctx, LAYERS

DEPTH = {"bg": 4.0, "bgfx": 4.0, "back": 2.4, "main": 1.0, "front": 0.42, "fx": 1.0}
PARALLAX = {"bg": 0.3, "bgfx": 1.0, "back": 0.55, "main": 1.0, "front": 1.7, "fx": 1.0}


def _cm_saturation(s: float, contrast: float = 1.0, bright: float = 0.0):
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    sr, sg, sb = (1 - s) * lr, (1 - s) * lg, (1 - s) * lb
    m = [sr + s, sg, sb, 0, 0,
         sr, sg + s, sb, 0, 0,
         sr, sg, sb + s, 0, 0,
         0, 0, 0, 1, 0]
    off = 0.5 * (1 - contrast) + bright
    for r in range(3):
        for k in range(3):
            m[r * 5 + k] *= contrast
        m[r * 5 + 4] = off
    return skia.ColorFilters.Matrix(m)


def _cm_threshold(th=0.62, gain=2.6):
    return skia.ColorFilters.Matrix([gain, 0, 0, 0, -th * gain,
                                     0, gain, 0, 0, -th * gain,
                                     0, 0, gain, 0, -th * gain,
                                     0, 0, 0, 1, 0])


def _cm_manga():
    k = 3.6
    lr, lg, lb = 0.299 * k, 0.587 * k, 0.114 * k
    off = 1 + 0.38 * k
    return skia.ColorFilters.Matrix([-lr, -lg, -lb, 0, off,
                                     -lr, -lg, -lb, 0, off,
                                     -lr, -lg, -lb, 0, off,
                                     0, 0, 0, 1, 0])


def _cm_channel(ch: int):
    m = [0.0] * 20
    m[ch * 5 + ch] = 1.0
    m[18] = 1.0
    return skia.ColorFilters.Matrix(m)


def _cm_tint(c, amt):
    r, g, b = gfx.rgb(c)
    a = amt
    return skia.ColorFilters.Matrix([1 - a + a * r * 0.6, a * r * 0.3, a * r * 0.1, 0, 0,
                                     a * g * 0.3, 1 - a + a * g * 0.6, a * g * 0.1, 0, 0,
                                     a * b * 0.3, a * b * 0.1, 1 - a + a * b * 0.6, 0, 0,
                                     0, 0, 0, 1, 0])


class Renderer:
    def __init__(self, scenario: dict, *, scale: float = 1.0):
        self.sc = scenario
        st = scenario.setdefault("style", {})
        self.W = int(st.get("width", 1080))
        self.H = int(st.get("height", 1920))
        self.fps = int(st.get("fps", 30))
        self.k = scale
        self.w, self.h = int(self.W * scale) // 2 * 2, int(self.H * scale) // 2 * 2
        self._surfs: dict = {}
        self.comp = skia.Surface(self.w, self.h)
        self.out = skia.Surface(self.w, self.h)
        self.beats: list[float] = scenario.get("_beats", [])
        rnd = np.random.default_rng(5)
        self.grain = []
        for _ in range(6):
            g = rnd.integers(0, 255, size=(self.h // 2, self.w // 2), dtype=np.uint8)
            rgba = np.dstack([g, g, g, np.full_like(g, 255)])
            self.grain.append(skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType))
        self._build_timeline()

    def _surface(self, name: str, f: float) -> skia.Surface:
        key = (name, f)
        if key not in self._surfs:
            self._surfs[key] = skia.Surface(max(2, int(self.w * f)), max(2, int(self.h * f)))
        return self._surfs[key]

    # ------------------------------------------------------------------ timeline
    def _build_timeline(self):
        self.shots = []
        T = 0.0
        cast = self.sc.get("cast", {})
        self.cues: list[tuple[float, str, float]] = []
        for i, shot in enumerate(self.sc["shots"]):
            dur = float(shot.get("dur", 2.0))
            scene_cls = SCENES.get(shot.get("scene", "arena"), SCENES["arena"])
            scene = scene_cls(shot, self.sc, self.W, self.H)
            specs = shot.get("actors", {})
            actors = {}
            for idx, (aid, spec) in enumerate(specs.items()):
                spec = spec or {}
                base = scene.layout(aid, spec, idx, len(specs))
                actors[aid] = Actor(aid, cast.get(aid, {"label": aid.upper()}), spec, base)
            vfx = []
            for ev in shot.get("events", []):
                do = ev.get("do")
                if do == "vfx":
                    fx = vfxmod.make(ev, shot)
                    if fx:
                        vfx.append(fx)
                        for tl, name, gain in fx.cues():
                            self.cues.append((T + tl, name, gain))
                elif ev.get("who") in actors:
                    actors[ev["who"]].apply(ev)
                elif ev.get("who") == "*" or isinstance(ev.get("who"), list):
                    who = list(actors) if ev["who"] == "*" else ev["who"]
                    for w in who:
                        if w in actors:
                            actors[w].apply({**ev, "who": w})
                if ev.get("sfx"):
                    self.cues.append((T + float(ev.get("t", 0)), ev["sfx"], float(ev.get("gain", 1.0))))
                if do == "sheet" and ev.get("sfx", "auto") == "auto":
                    self.cues.append((T + float(ev.get("t", 0)), "paper", 0.6))
                    self.cues.append((T + float(ev.get("t", 0)) + 0.2, "stamp", 0.8))
                if do == "text" and ev.get("sfx", "auto") == "auto":
                    self.cues.append((T + float(ev.get("t", 0)), "tick", 0.25))
            if shot.get("in") in ("flash", "impact"):
                self.cues.append((T, "hit", 0.7))
            if shot.get("in") == "whoosh":
                self.cues.append((T, "whoosh", 0.6))
            self.shots.append(dict(start=T, dur=dur, shot=shot, scene=scene, actors=actors, vfx=vfx, idx=i))
            T += dur
        self.total = T

    def shot_at(self, T: float):
        for s in self.shots:
            if s["start"] <= T < s["start"] + s["dur"]:
                return s
        return self.shots[-1]

    def beat_pulse(self, T: float) -> float:
        if not self.beats:
            return 0.0
        i = np.searchsorted(self.beats, T) - 1
        if i < 0:
            return 0.0
        dt = T - self.beats[i]
        return math.exp(-dt * 7.0)

    # ------------------------------------------------------------------ camera
    def _cam_key(self, key: dict, scene, states):
        x = float(key.get("x", 0.0))
        y = float(key.get("y", 0.0))
        if key.get("on") and key["on"] in states:
            fx, fy = scene.focus_point(states[key["on"]])
            x += fx - self.W / 2
            y += fy - self.H / 2
        return x, y, float(key.get("zoom", 1.0)), float(key.get("rot", 0.0))

    def camera(self, sh, t, states):
        cam = sh["shot"].get("camera", {})
        a = self._cam_key(cam.get("from", {}), sh["scene"], states)
        b = self._cam_key(cam.get("to", cam.get("from", {})), sh["scene"], states)
        p = ease(cam.get("ease", "sine"), win(t, 0, sh["dur"]))
        x, y, z, r = (a[i] + (b[i] - a[i]) * p for i in range(4))
        return x, y, z, r

    # ------------------------------------------------------------------ frame
    def frame(self, T: float) -> skia.Image:
        sh = self.shot_at(T)
        t = T - sh["start"]
        shot = sh["shot"]
        W, H, k = self.W, self.H, self.k
        beat = self.beat_pulse(T)
        ctx = Ctx(W=W, H=H, t=t, T=T, dur=sh["dur"], fps=self.fps, shot=shot, scenario=self.sc, beat=beat)
        states = {aid: a.state(t, W, beat) for aid, a in sh["actors"].items()}
        for st in states.values():
            st.joints = rig.solve(st.pose, st.x, st.y, st.s, st.facing, st.look.build)
        ctx.actors = states
        ctx.actor_objs = sh["actors"]
        for fx in sh["vfx"]:
            fx.pre(ctx, states)
        for st in states.values():
            st.joints = rig.solve(st.pose, st.x, st.y, st.s, st.facing, st.look.build)
        _cx, _cy, _z, _r = self.camera(sh, t, states)
        ctx.cam = (_cx, _cy, _z)
        sh["scene"].build(ctx, states)
        for fx in sh["vfx"]:
            fx.build(ctx, states)
        self._transition(ctx, shot, t, sh["dur"])
        self._screen_ui(ctx, T)

        cx, cy, zoom, rot = self.camera(sh, t, states)
        zoom *= 1.0 + ctx.zoom_punch
        rnd = random.Random(int(T * self.fps) * 7919 + 13)
        shx = (rnd.random() - 0.5) * 2 * ctx.shake * 26
        shy = (rnd.random() - 0.5) * 2 * ctx.shake * 26
        cam = shot.get("camera", {})
        dof = float(cam.get("dof", 1.0))
        focus = cam.get("focus", "main")
        if isinstance(focus, str):
            if focus in states:
                focus = DEPTH.get(states[focus].layer, 1.0)
            else:
                focus = DEPTH.get(focus, 1.0)
        focus = float(focus)

        comp = self.comp.getCanvas()
        comp.clear(gfx.col("#0b0b0d"))
        refl = sh["scene"].reflection(ctx)
        camp = (W, H, shx, shy, rot, zoom, cx, cy)
        for name in ["bg", "bgfx", "back", "main", "front", "fx"]:
            if refl is not None and name in ("back", "main"):
                self._reflection(comp, ctx, refl, camp)
                refl = None
            items = ctx.layers.get(name)
            if not items:
                continue
            alpha = ctx.layer_alpha.get(name, 1.0)
            if alpha <= 0.001:
                continue
            sig = 0.0
            if name not in ("fx", "bgfx"):
                sig = dof * 8.5 * abs(math.log(DEPTH[name] / focus))
            # blurred layers are rendered at reduced resolution (cheap + softer)
            f = 1.0 if sig < 2.5 else 0.5 if sig < 7 else 0.25
            surf = self._surface(name, f)
            c = surf.getCanvas()
            c.clear(skia.ColorTRANSPARENT)
            c.save()
            c.scale(k * f, k * f)
            self._apply_cam(c, name, camp)
            for _, fn in sorted(items, key=lambda it: it[0]):
                fn(c)
            c.restore()
            img = surf.makeImageSnapshot()
            if sig >= 0.4:
                tmp = self._surface(name + "_blur", f)
                tc = tmp.getCanvas()
                tc.clear(skia.ColorTRANSPARENT)
                bs = sig * k * f
                tc.drawImage(img, 0, 0, skia.SamplingOptions(),
                             skia.Paint(ImageFilter=skia.ImageFilters.Blur(bs, bs, skia.TileMode.kDecal)))
                img = tmp.makeImageSnapshot()
            pnt = skia.Paint()
            pnt.setAlphaf(alpha)
            comp.drawImageRect(img, skia.Rect(0, 0, self.w, self.h),
                               skia.SamplingOptions(skia.FilterMode.kLinear), pnt)

        # ---- grade + bloom + vignette
        base = self.comp.makeImageSnapshot()
        out = self.out.getCanvas()
        out.clear(skia.ColorBLACK)
        g = self.sc["style"].get("grade", {})
        sat = float(g.get("saturation", 0.92)) * (1 - ctx.desat)
        con = float(g.get("contrast", 1.06))
        bri = float(g.get("brightness", 0.0)) - ctx.darken * 0.35
        gp = skia.Paint(ColorFilter=_cm_saturation(sat, con, bri))
        if ctx.tint is not None and ctx.tint_amt > 0:
            gp.setColorFilter(skia.ColorFilters.Compose(_cm_tint(ctx.tint, ctx.tint_amt), gp.getColorFilter()))
        out.drawImage(base, 0, 0, skia.SamplingOptions(), gp)
        bloom = float(g.get("bloom", 0.55))
        if bloom > 0:
            q = 0.25
            bs = self._surface("bloom_src", q)
            bc = bs.getCanvas()
            bc.clear(skia.ColorTRANSPARENT)
            bc.drawImageRect(base, skia.Rect(0, 0, self.w * q, self.h * q), skia.SamplingOptions(skia.FilterMode.kLinear),
                             skia.Paint(ColorFilter=_cm_threshold()))
            bb = self._surface("bloom_blur", q)
            bbc = bb.getCanvas()
            bbc.clear(skia.ColorTRANSPARENT)
            bbc.drawImage(bs.makeImageSnapshot(), 0, 0, skia.SamplingOptions(),
                          skia.Paint(ImageFilter=skia.ImageFilters.Blur(22 * k * q, 22 * k * q, skia.TileMode.kDecal)))
            bp = skia.Paint(BlendMode=gfx.ADD)
            bp.setAlphaf(min(1.0, bloom))
            out.drawImageRect(bb.makeImageSnapshot(), skia.Rect(0, 0, self.w, self.h),
                              skia.SamplingOptions(skia.FilterMode.kLinear), bp)
        out.save()
        out.scale(k, k)
        vg = float(g.get("vignette", 0.62))
        out.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=gfx.radial(W / 2, H * 0.48, H * 0.62,
                                                                         [(0, "black", 0), (0.55, "black", 0.0),
                                                                          (1, "black", vg)])))
        for _, fn in sorted(ctx.layers.get("screen", []), key=lambda it: it[0]):
            fn(out)
        out.restore()
        grain = float(g.get("grain", 0.07))
        if grain > 0:
            gi = self.grain[int(T * self.fps) % len(self.grain)]
            gpn = skia.Paint(BlendMode=skia.BlendMode.kOverlay)
            gpn.setAlphaf(grain)
            out.drawImageRect(gi, skia.Rect(0, 0, self.w, self.h), skia.SamplingOptions(), gpn)

        img = self.out.makeImageSnapshot()
        if ctx.impact > 0 or ctx.chroma > 0 or ctx.flash > 0:
            fin = self.comp.getCanvas()
            fin.clear(skia.ColorBLACK)
            if ctx.impact > 0:
                fin.drawImage(img, 0, 0, skia.SamplingOptions(), skia.Paint(ColorFilter=_cm_manga()))
                vfxmod.speed_lines(fin, self.w / 2, self.h / 2, self.w, ctx.T, color="black", a=0.9, n=70)
            elif ctx.chroma > 0:
                d = ctx.chroma * 14 * k
                for ch, dx in ((0, -d), (1, 0), (2, d)):
                    p = skia.Paint(ColorFilter=_cm_channel(ch), BlendMode=gfx.ADD)
                    fin.drawImage(img, dx, 0, skia.SamplingOptions(), p)
            else:
                fin.drawImage(img, 0, 0)
            if ctx.flash > 0:
                fin.drawRect(skia.Rect(0, 0, self.w, self.h), gfx.paint(ctx.flash_c, min(1.0, ctx.flash)))
            img = self.comp.makeImageSnapshot()
        return img

    @staticmethod
    def _apply_cam(c: skia.Canvas, name: str, camp):
        W, H, shx, shy, rot, zoom, cx, cy = camp
        par = PARALLAX[name]
        z = zoom ** (par if name != "fx" else 1.0)
        c.translate(W / 2 + shx * (0.5 + par * 0.5), H / 2 + shy * (0.5 + par * 0.5))
        c.rotate(rot * par)
        c.scale(z, z)
        c.translate(-W / 2 - cx * par, -H / 2 - cy * par)

    def _reflection(self, comp: skia.Canvas, ctx: Ctx, refl: dict, camp):
        """Glossy floor: mirror the actor/effect layers around the floor line, fade + blur them."""
        W, H = self.W, self.H
        k, f = self.k, 0.5
        fy, fade = refl["floor"], refl["fade"]
        rs = self._surface("refl", f)
        c = rs.getCanvas()
        c.clear(skia.ColorTRANSPARENT)
        drawn = False
        for name in refl.get("layers", ["main"]):
            items = ctx.layers.get(name)
            if not items or ctx.layer_alpha.get(name, 1.0) <= 0.001:
                continue
            drawn = True
            c.save()
            c.scale(k * f, k * f)
            self._apply_cam(c, name, camp)
            c.clipRect(skia.Rect(-2 * W, fy, 3 * W, fy + fade * 1.05))
            c.translate(0, 2 * fy)
            c.scale(1, -1)
            for _, fn in sorted(items, key=lambda it: it[0]):
                fn(c)
            c.restore()
        if not drawn:
            return
        c.save()
        c.scale(k * f, k * f)
        self._apply_cam(c, "main", camp)
        mask = gfx.linear(0, fy, 0, fy + fade, [(0, "white", 1.0), (0.3, "white", 0.5), (1, "white", 0.0)])
        c.drawRect(skia.Rect(-2 * W, fy - 4, 3 * W, fy + fade * 1.1),
                   skia.Paint(Shader=mask, BlendMode=skia.BlendMode.kDstIn))
        c.restore()
        img = rs.makeImageSnapshot()
        b = float(refl.get("blur", 3.0)) * k * f
        if b > 0.3:
            tmp = self._surface("refl_blur", f)
            tc = tmp.getCanvas()
            tc.clear(skia.ColorTRANSPARENT)
            tc.drawImage(img, 0, 0, skia.SamplingOptions(),
                         skia.Paint(ImageFilter=skia.ImageFilters.Blur(b, b, skia.TileMode.kDecal)))
            img = tmp.makeImageSnapshot()
        p = skia.Paint()
        p.setAlphaf(min(1.0, float(refl["strength"])))
        comp.drawImageRect(img, skia.Rect(0, 0, self.w, self.h), skia.SamplingOptions(skia.FilterMode.kLinear), p)

    # ------------------------------------------------------------------ overlays
    def _transition(self, ctx: Ctx, shot: dict, t: float, dur: float):
        kind = shot.get("in", "cut")
        if kind in ("flash", "impact"):
            ctx.flash = max(ctx.flash, 1.0 - win(t, 0, 0.18))
            ctx.flash_c = shot.get("in_color", "white")
            if kind == "impact" and t < 2.5 / self.fps:
                ctx.impact = 1.0
        elif kind == "fade":
            ctx.darken = max(ctx.darken, 1.0 - win(t, 0, 0.35))
            ctx.flash_c = "black"
            ctx.flash = max(ctx.flash, 1.0 - win(t, 0, 0.35))
        elif kind == "glitch" and t < 0.2:
            ctx.chroma = max(ctx.chroma, 1.0 - t / 0.2)
        out = shot.get("out", "cut")
        if out == "fade":
            ctx.flash_c = "black"
            ctx.flash = max(ctx.flash, win(t, dur - 0.4, dur))
        for ev in shot.get("events", []):
            if ev.get("do") == "shake":
                t0 = float(ev.get("t", 0))
                d = float(ev.get("dur", 0.4))
                if t0 <= t < t0 + d:
                    ctx.shake = max(ctx.shake, float(ev.get("amp", 0.6)) * (1 - (t - t0) / d))
            elif ev.get("do") == "flash":
                t0 = float(ev.get("t", 0))
                d = float(ev.get("dur", 0.25))
                if t0 <= t < t0 + d:
                    ctx.flash = max(ctx.flash, float(ev.get("amp", 0.9)) * (1 - (t - t0) / d))
                    ctx.flash_c = ev.get("color", "white")
            elif ev.get("do") == "impact":
                t0 = float(ev.get("t", 0))
                if t0 <= t < t0 + float(ev.get("frames", 3)) / self.fps:
                    ctx.impact = 1.0
            elif ev.get("do") == "punch":
                t0 = float(ev.get("t", 0))
                d = float(ev.get("dur", 0.35))
                if t0 <= t < t0 + d:
                    ctx.zoom_punch += float(ev.get("amp", 0.06)) * (1 - (t - t0) / d) ** 2
            elif ev.get("do") == "text":
                t0 = float(ev.get("t", 0))
                d = float(ev.get("dur", 2.0))
                if t0 <= t < t0 + d:
                    self._caption(ctx, ev, t - t0, d)

    def _caption(self, ctx: Ctx, ev: dict, lt: float, d: float):
        """On-screen text. style 'sub' (default): thin mono subtitle like the reference account;
        style 'bold': heavy mono with a dark glow (hooks, shouts)."""
        W, H = self.W, self.H
        style = ev.get("style", "sub")
        pos = ev.get("pos", "top")
        y = {"top": H * 0.135, "center": H * 0.45, "bottom": H * 0.8}.get(pos, H * 0.135)
        if isinstance(ev.get("y"), (int, float)):
            y = float(ev["y"]) * H
        fade_in, fade_out = float(ev.get("fade", 0.25)), float(ev.get("fade", 0.25))
        a = min(1.0, lt / max(0.01, fade_in)) * min(1.0, (d - lt) / max(0.01, fade_out))
        typing = float(ev.get("type", 0.0 if style == "sub" else 0.35))
        full = ev["text"]
        n = len(full) if typing <= 0 else int(len(full) * min(1.0, lt / typing))
        accent = ev.get("color", "#ecece9" if style == "sub" else "#f2f2f0")
        size = float(ev.get("size", 30 if style == "sub" else 46))
        face = gfx.MONO_MED if style == "sub" else gfx.MONO_XB
        spacing = size * (0.3 if style == "sub" else 0.12)
        lines = []
        for part in full[:n].split("\n"):
            lines += gfx.wrap(part, gfx.font(face, size), W * 0.88, spacing=spacing) if part else [""]

        def draw(c):
            for i, ln in enumerate(lines):
                yy = y + i * size * 1.55
                if style == "sub":
                    gfx.draw_text(c, ln, W / 2, yy, size=size, face=gfx.MONO_MED, c=accent, a=0.92 * a,
                                  spacing=size * 0.3, glow=size * 0.5, glow_c="black")
                else:
                    gfx.draw_text(c, ln, W / 2, yy, size=size, face=gfx.MONO_XB, c=accent, a=a,
                                  spacing=size * 0.12, glow=size * 0.3, glow_c="black")
        ctx.add("screen", draw, z=5)

    def _screen_ui(self, ctx: Ctx, T: float):
        st = self.sc.get("style", {})
        W, H = self.W, self.H
        hook = st.get("hook")
        if hook and hook.get("text"):
            t0, t1 = float(hook.get("from", 0.0)), float(hook.get("to", 2.6))
            if t0 <= T < t1:
                a = min(1.0, (T - t0) / 0.2) * min(1.0, (t1 - T) / 0.25)

                def draw_hook(c):
                    size = float(hook.get("size", 44))
                    lines = hook["text"].split("\n")
                    for i, ln in enumerate(lines):
                        gfx.draw_text(c, ln, W / 2, H * 0.14 + i * size * 1.3, size=size, face=gfx.MONO_XB,
                                      c="#f4f4f2", a=a, spacing=size * 0.14, glow=size * 0.4, glow_c="black")
                ctx.add("screen", draw_hook, z=4)
        wm = st.get("watermark")
        if wm and self.shot_at(T)["shot"].get("scene") != "title":
            wy = float(st.get("watermark_y", 0.82))

            def draw_wm(c):
                gfx.draw_text(c, wm, W / 2, H * wy, size=22, face=gfx.MONO, c="white", a=0.2, spacing=7)
            ctx.add("screen", draw_wm, z=-1)

    # ------------------------------------------------------------------ output
    def render(self, out_path: str | Path, *, start: float = 0.0, end: float | None = None, crf: int = 18):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        end = self.total if end is None else min(end, self.total)
        n = int(round((end - start) * self.fps))
        ff = shutil.which("ffmpeg") or "ffmpeg"
        cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{self.w}x{self.h}",
               "-r", str(self.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        assert proc.stdin is not None
        for i in range(n):
            T = start + i / self.fps
            img = self.frame(T)
            proc.stdin.write(img.tobytes())
            if i % max(1, self.fps * 2) == 0:
                print(f"  frame {i + 1}/{n}  t={T:5.2f}s", flush=True)
        proc.stdin.close()
        proc.wait()
        return out_path

    def still(self, T: float, path: str | Path):
        img = self.frame(T)
        img.save(str(path))
        return path
