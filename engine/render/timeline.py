"""Tweens, actor tracks and the per-frame context."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

from . import rig
from .easing import ease


def _lerp(a, b, t):
    return a + (b - a) * t


class Track:
    """A value animated by a list of tweens (t, dur, to, ease)."""

    def __init__(self, init, lerp: Callable = _lerp):
        self.init = init
        self.lerp = lerp
        self.tw: list[tuple[float, float, Any, str]] = []
        self._starts: list | None = None

    def add(self, t: float, to, dur: float = 0.3, ez: str = "inout_cubic"):
        self.tw.append((float(t), float(dur), to, ez))
        self.tw.sort(key=lambda x: x[0])
        self._starts = None

    def _eval(self, t, n, starts):
        v = self.init
        for i in range(n):
            t0, d, to, ez = self.tw[i]
            if t < t0:
                break
            p = 1.0 if d <= 0 else min(1.0, (t - t0) / d)
            v = self.lerp(starts[i], to, ease(ez, p))
        return v

    def __call__(self, t: float):
        if self._starts is None:
            starts: list = []
            for i, (t0, _, _, _) in enumerate(self.tw):
                starts.append(self._eval(t0, i, starts))
            self._starts = starts
        return self._eval(t, len(self.tw), self._starts)


@dataclass
class ActorState:
    id: str
    x: float
    y: float
    s: float
    facing: int
    pose: dict
    look: rig.Look
    label: str
    layer: str = "main"
    alpha: float = 1.0
    level: float | None = None
    level_text: str | None = None
    level_c: Any = "violet"
    sheet: str | None = None
    sheet_t: float = 0.0          # seconds since sheet appeared
    zzz: bool = False
    glitch: float = 0.0
    show_label: bool = True
    joints: Any = None
    label_pos: str = "head"       # head | floor
    floor: float | None = None
    spot: float = 0.0             # this actor's spotlight intensity (stage)
    dim: float = 0.0
    tower: int = 0                # blocks in this actor's tower (stage)
    tower_side: int = 1
    tower_base: int = 0
    carrying: bool = False        # holding a block right now
    sparkle: float = 0.0
    extra: dict = field(default_factory=dict)


class Actor:
    """An actor inside one shot: base placement + animated tracks from events."""

    NUM = ["x", "y", "s", "alpha", "core", "band", "eyes", "marks", "level", "glitch", "tint", "yoff"]

    def __init__(self, aid: str, cast: dict, spec: dict, base: dict):
        self.id = aid
        self.cast = cast
        self.spec = spec
        self.base = base  # x, y, s, layer, facing set by the scene layout
        pose0 = rig.pose_dict(spec.get("pose", base.get("pose", "stand")))
        self.pose = Track(pose0, rig.blend)
        self.tracks = {
            "x": Track(0.0), "y": Track(0.0), "yoff": Track(float(spec.get("yoff", 0.0))),
            "s": Track(1.0), "alpha": Track(float(spec.get("alpha", 1.0))),
            "core": Track(float(spec.get("core", cast.get("core_amt", 1.0)))),
            "band": Track(float(spec.get("band", cast.get("band", 0.0)))),
            "eyes": Track(float(spec.get("eyes", 0.0))),
            "marks": Track(float(spec.get("marks", 0.0))),
            "level": Track(float(spec["level"]) if spec.get("level") is not None else -1.0),
            "glitch": Track(0.0),
            "tint": Track(float(spec.get("tint", 0.0))),
            "dim": Track(float(spec.get("dim", 0.0))),
            "flame": Track(float(spec.get("flame", cast.get("flame", 0.0)))),
            "spot": Track(float(spec.get("spot", base.get("spot", 1.0)))),
            "sparkle": Track(float(spec.get("sparkle", 0.0))),
        }
        self.facing = int(spec.get("facing", base.get("facing", 1)))
        self.flips: list[tuple[float, int]] = []
        self.sheets: list[tuple[float, str | None]] = []
        if spec.get("sheet"):
            self.sheets.append((-10.0, spec["sheet"]))
        self.labels: list[tuple[float, str]] = []
        self.level_texts: list[tuple[float, str]] = []
        if spec.get("level_text"):
            self.level_texts.append((-10.0, spec["level_text"]))
        self.zzz: list[tuple[float, bool]] = [(-10.0, bool(spec.get("zzz", False)))]
        self.mods = dict(spec.get("mods", {}))
        self.mod_events: list[tuple[float, dict]] = []
        self.show_label = spec.get("label", True) is not False
        tw = spec.get("tower") or {}
        self.tower_base = int(tw.get("base", 0)) if isinstance(tw, dict) else int(tw)
        self.tower_side = int(tw.get("side", 1)) if isinstance(tw, dict) else 1
        self.stacks: list[tuple[float, float, float]] = []   # (t0, t1, rate)
        self.build = spec.get("build", cast.get("build", base.get("build", "chunky")))

    # --- event application -------------------------------------------------
    def apply(self, ev: dict):
        t = float(ev.get("t", 0))
        do = ev["do"]
        dur = float(ev.get("dur", 0.35))
        ez = ev.get("ease", "inout_cubic")
        if do == "pose":
            self.pose.add(t, rig.pose_dict(ev["pose"]), dur, ez)
            if "mods" in ev:
                self.mod_events.append((t, ev["mods"]))
        elif do == "move":
            if "x" in ev:
                self.tracks["x"].add(t, float(ev["x"]) - self.base_x01(), dur, ez)
            if "dy" in ev:
                self.tracks["y"].add(t, float(ev["dy"]), dur, ez)
            if "yoff" in ev:
                self.tracks["yoff"].add(t, float(ev["yoff"]), dur, ez)
        elif do == "scale":
            self.tracks["s"].add(t, float(ev["to"]), dur, ez)
        elif do in ("fade", "alpha"):
            self.tracks["alpha"].add(t, float(ev.get("to", 0.0)), dur, ez)
        elif do == "hide":
            self.tracks["alpha"].add(t, 0.0, float(ev.get("dur", 0.0)), ez)
        elif do == "show":
            self.tracks["alpha"].add(t, 1.0, float(ev.get("dur", 0.0)), ez)
        elif do == "core":
            self.tracks["core"].add(t, float(ev.get("to", 1.0)), dur, ez)
        elif do == "band":
            self.tracks["band"].add(t, float(ev.get("to", 0.0)), dur, ez)
        elif do == "eyes":
            self.tracks["eyes"].add(t, float(ev.get("to", 1.0)), dur, ez)
        elif do == "marks":
            self.tracks["marks"].add(t, float(ev.get("to", 1.0)), dur, ez)
        elif do == "tint":
            self.tracks["tint"].add(t, float(ev.get("to", 1.0)), dur, ez)
        elif do == "level":
            self.tracks["level"].add(t, float(ev.get("to", 1.0)), float(ev.get("dur", 1.0)), ez)
            if ev.get("text"):
                self.level_texts.append((t + float(ev.get("dur", 1.0)) * float(ev.get("text_at", 1.0)), ev["text"]))
        elif do == "glitch":
            self.tracks["glitch"].add(t, 1.0, 0.05, "linear")
            self.tracks["glitch"].add(t + float(ev.get("dur", 0.5)), 0.0, 0.1, "linear")
        elif do == "sheet":
            self.sheets.append((t, ev.get("mark")))
        elif do == "sheet_off":
            self.sheets.append((t, None))
        elif do == "label":
            self.labels.append((t, ev.get("text", "")))
        elif do == "zzz":
            self.zzz.append((t, bool(ev.get("on", True))))
        elif do == "face":
            self.flips.append((t, int(ev.get("facing", -self.facing))))
        elif do == "mods":
            self.mod_events.append((t, ev.get("mods", {})))
        elif do == "dim":
            self.tracks["dim"].add(t, float(ev.get("to", 1.0)), float(ev.get("dur", 0.8)), ez)
        elif do == "flame":
            self.tracks["flame"].add(t, float(ev.get("to", 0.0)), float(ev.get("dur", 1.0)), ez)
        elif do == "spot":
            self.tracks["spot"].add(t, float(ev.get("to", 0.0)), float(ev.get("dur", 0.6)), ez)
        elif do == "sparkle":
            self.tracks["sparkle"].add(t, float(ev.get("to", 1.0)), float(ev.get("dur", 0.2)), ez)
            if ev.get("hold"):
                self.tracks["sparkle"].add(t + float(ev["hold"]), 0.0, 0.3, ez)
        elif do == "stack":
            until = float(ev.get("until", t + float(ev.get("dur", 2.0))))
            self.stacks.append((t, until, float(ev.get("rate", 1.0))))
            self.stacks.sort()

    def base_x01(self) -> float:
        return float(self.base.get("x01", 0.5))

    def tower_count(self, t: float) -> int:
        n = self.tower_base
        for t0, t1, rate in self.stacks:
            if t >= t0:
                n += int((min(t, t1) - t0) * rate + 0.2)
        return n

    def stacking(self, t: float):
        """(phase, rate) if a stacking cycle is running at t, else None."""
        for t0, t1, rate in self.stacks:
            if t0 <= t < t1:
                return ((t - t0) * rate + 0.1) % 1.0, rate
        return None

    # --- state -------------------------------------------------------------
    def state(self, t: float, W: float, beat: float = 0.0) -> ActorState:
        tr = {k: v(t) for k, v in self.tracks.items()}
        pose = self.pose(t)
        mods = dict(self.mods)
        for te, m in self.mod_events:
            if t >= te:
                mods.update(m)
        carrying = False
        st_ph = self.stacking(t)
        if st_ph is not None:
            # blend in/out of the stacking cycle over 0.15 s so it starts and stops smoothly
            cyc, carrying = rig.stack_pose(st_ph[0], self.tower_side)
            k = 1.0
            for t0, t1, _ in self.stacks:
                if t0 <= t < t1:
                    k = min(1.0, (t - t0) / 0.15, (t1 - t) / 0.15)
            pose = rig.blend(pose, cyc, k) if k < 1.0 else cyc
        pose = rig.apply_mods(pose, mods, t)
        facing = self.facing
        for te, f in self.flips:
            if t >= te:
                facing = f
        sheet, sheet_t = None, 0.0
        for te, m in self.sheets:
            if t >= te:
                sheet, sheet_t = m, t - te
        label = self.cast.get("label", self.id.upper())
        for te, txt in self.labels:
            if t >= te:
                label = txt
        lvl_text = None
        for te, txt in self.level_texts:
            if t >= te:
                lvl_text = txt
        zz = False
        for te, on in self.zzz:
            if t >= te:
                zz = on
        bob = 0.0
        if mods.get("float"):
            bob = math.sin(t * 2.2) * 0.12 * self.base["s"] * mods["float"]
        s = self.base["s"] * tr["s"]
        floor = self.base.get("floor")
        if floor is not None and not self.spec.get("no_ground"):
            # stay on the floor whatever the pose (squats, kicks, walking bob)
            y0 = floor - rig.ground_offset(pose, s, facing, self.build)
        else:
            y0 = self.base["y"]
        core_c = self.cast.get("core")
        look = rig.Look(
            color=self.cast.get("color", "figure"),
            alpha=tr["alpha"],
            core=core_c,
            core_amt=tr["core"] * (1.0 + 0.25 * beat),
            band=tr["band"],
            eyes=self.cast.get("eyes", "ice"),
            eyes_amt=tr["eyes"],
            marks=tr["marks"],
            legs=self.base.get("legs", True),
            tint=self.cast.get("tint_c", "violet"),
            tint_amt=tr["tint"],
            glow=self.base.get("glow", 0.22),
            build=self.build,
            dim=tr["dim"],
            flame=tr["flame"],
            flame_c=self.cast.get("flame_c", "#ff4b2b"),
        )
        return ActorState(
            id=self.id,
            x=self.base["x"] + tr["x"] * W,
            y=y0 + tr["y"] + tr["yoff"] + bob,
            s=s,
            facing=facing,
            pose=pose,
            look=look,
            label=label,
            layer=self.spec.get("layer", self.base.get("layer", "main")),
            alpha=tr["alpha"],
            level=tr["level"] if tr["level"] >= 0 else None,
            level_text=lvl_text,
            level_c=self.cast.get("core", "violet"),
            sheet=sheet,
            sheet_t=sheet_t,
            zzz=zz,
            glitch=tr["glitch"],
            show_label=self.show_label,
            label_pos=self.spec.get("label_pos", self.cast.get("label_pos", self.base.get("label_pos", "head"))),
            floor=floor,
            spot=tr["spot"],
            dim=tr["dim"],
            tower=self.tower_count(t),
            tower_side=self.tower_side,
            tower_base=self.tower_base,
            carrying=carrying,
            sparkle=tr["sparkle"],
        )


@dataclass
class Ctx:
    """Everything a scene / VFX needs for one frame."""
    W: int
    H: int
    t: float            # shot-local time
    T: float            # global time
    dur: float          # shot duration
    fps: int
    shot: dict
    scenario: dict
    beat: float = 0.0   # 0..1 pulse on music beats
    layers: dict = field(default_factory=dict)
    actors: dict = field(default_factory=dict)          # id -> ActorState
    layer_alpha: dict = field(default_factory=dict)
    shake: float = 0.0
    shake_seed: int = 0
    impact: float = 0.0       # >0 -> manga impact frame (inverted)
    chroma: float = 0.0
    flash: float = 0.0
    flash_c: Any = "white"
    desat: float = 0.0
    darken: float = 0.0
    zoom_punch: float = 0.0
    tint: Any = None
    tint_amt: float = 0.0
    sfx: list = field(default_factory=list)

    def add(self, layer: str, fn: Callable, z: float = 0.0):
        self.layers.setdefault(layer, []).append((z, fn))


LAYERS = ["bg", "bgfx", "back", "main", "front", "fx", "screen"]
