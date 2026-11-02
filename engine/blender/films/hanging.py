"""LAST ONE HANGING: four minds on one pull-up bar, who lets go last (3D, Blender + Mixamo clips).

14 s at 30 fps (frames 1..420), every word on screen in English:
  1-30     dark stage; spotlights slam on one by one: MOTIVATION, TALENT, DISCIPLINE, EGO hang from one bar.
  30-100   timer runs 0:00 -> 0:47. MOTIVATION shakes, his light flickers, he drops and sits on the floor.
  100-163  -> 1:52. TALENT hangs one-handed, scratches his head, bored, lets go.
  163-238  -> 3:07. EGO trembles and sweats, his grip slips: hard landing, the music cuts.
  238-272  silence. On his knees he looks at his red, torn palms, then up at the bar. His eyes ignite,
           black lightning with red edges crackles around him, the floor cracks. He jumps.
  272      DROP: he grabs the bar again. Impact frame, shockwave, the bar bends under his grip.
  272-372  -> 4:58. DISCIPLINE and EGO hang; DISCIPLINE shakes and drops, kneels with respect.
  372-420  -> 5:01. EGO alone under the only light, lightning crackling, the timer keeps going.
Top text: LAST ONE HANGING WINS. -> YOU CAN'T OUTLAST SOMEONE / WITH SOMETHING TO PROVE.
Hidden reference (never named): willpower as black lightning with a red rim.
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Matrix, Vector

from .. import kit, mocap, props

SLUG = "last_one_hanging"
FPS = 30
N = 420
DROP = 272
BAR_Z = 2.36
GRIP_Z = 2.29                     # wrists' height on the bar (the hang clip's hands)
XS = {"motivation": -1.29, "talent": -0.43, "discipline": 0.43, "ego": 1.29}
LABELS = {"motivation": "MOTIVATION", "talent": "TALENT", "discipline": "DISCIPLINE", "ego": "EGO"}
SPOT_ON = {"motivation": 3, "talent": 8, "discipline": 13, "ego": 18}
RELEASE = {"motivation": 100, "talent": 163, "ego": 238, "discipline": 372}
CAM_WIDE = (Vector((0, -11.7, 1.9)), Vector((0, 0, 1.52)), 50.0)
EGO_X = XS["ego"]
RED = (1.0, 0.10, 0.07)

META = {
    "slug": SLUG,
    "caption": "Motivation left first. Talent got bored. Discipline lasted almost five minutes. "
               "But you can't outlast someone with something to prove. Which one are you?",
    "hashtags": ["motivation", "discipline", "ego", "mindset", "selfimprovement", "grind", "gym", "3danimation"],
}

TIMER = [(30, 0), (100, 47), (163, 112), (238, 187), (DROP, 189), (372, 298), (390, 300), (N, 301)]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ramp(f, f0, f1):
    return smooth((f - f0) / max(1e-6, f1 - f0))


def lerp(a, b, t):
    return a + (b - a) * t


def timer_seconds(f):
    if f <= TIMER[0][0]:
        return 0.0
    for (f0, s0), (f1, s1) in zip(TIMER, TIMER[1:]):
        if f <= f1:
            return s0 + (s1 - s0) * (f - f0) / (f1 - f0)
    return TIMER[-1][1]


def _face_axis(arm, bone):
    """Damped-track axis of a bone that points where the face looks (world -Y in the rest pose)."""
    m = (arm.matrix_world.to_3x3() @ arm.data.bones[kit.MIX + bone].matrix_local.to_3x3()).normalized()
    best, name = -2.0, "TRACK_NEGATIVE_Z"
    for i, ax in enumerate("XYZ"):
        col = Vector((m[0][i], m[1][i], m[2][i]))
        for sign, pre in ((1, ""), (-1, "NEGATIVE_")):
            d = (col * sign).dot(Vector((0, -1, 0)))
            if d > best:
                best, name = d, f"TRACK_{pre}{ax}"
    return name


# ----------------------------------------------------------------------------- film

class Film:
    def __init__(self, w=1080, h=1920, samples=8):
        self.sc = kit.reset(fps=FPS, w=w, h=h)
        kit.setup_render(self.sc, samples=samples, bloom=False)
        sc = self.sc
        sc.render.use_persistent_data = True
        sc.cycles.glossy_bounces = 1
        sc.cycles.transmission_bounces = 0
        sc.cycles.volume_bounces = 0
        sc.cycles.transparent_max_bounces = 16
        sc.cycles.adaptive_threshold = 0.05
        sc.frame_start, sc.frame_end = 1, N
        kit.outline_mat()
        self.rng = random.Random(11)
        self._last = {}
        mocap.recenter("hard_land", 16, (0.0, -0.03))
        self._stage()
        self._cast()
        self._fx()
        self._camera()

    # --- stage: bar, floor, spots + light shafts ------------------------------------------------
    def _stage(self):
        self.bar = props.pullup_bar("bar", z=BAR_Z)
        floor = kit.plane("floor", 40, 40, (0, 0, 0))
        kit.set_mat(floor, kit.glossy_floor(center=(0.0, -0.6), radius=(3.4, 2.8)))
        self.spots, self.beams = {}, {}
        for k, x in XS.items():
            self.spots[k] = kit.spot(f"spot_{k}", (x, -0.9, 5.4), (x, 0, 1.0), energy=720, size_deg=30, blend=0.5,
                                     radius=0.25)
            self.beams[k] = props.light_beam(f"beam_{k}", (x, -0.5, 5.35), bottom_z=0.2, r_top=0.07, r_bottom=0.78,
                                             strength=0.28)

    # --- the four characters on Mixamo clips --------------------------------------------------------
    def _cast(self):
        self.chars = {}
        for k, x in XS.items():
            mat = kit.toon(f"toon_{k}", (0.95, 0.95, 0.94, 1), flat=0.92)
            arm = mocap.character(k, "hang", limb=0.05, torso=0.095, head=0.15, mat=mat)
            arm.parent.location = (x, 0, 0)
            em = next(n for n in mat.node_tree.nodes if n.type == "EMISSION")
            df = next(n for n in mat.node_tree.nodes if n.type == "BSDF_DIFFUSE")
            self.chars[k] = {"arm": arm, "root": arm.parent, "x": x, "mat_em": em, "mat_df": df,
                             "seed": len(self.chars) * 17 + 3}
        # TALENT: right hand off the bar (one-arm hang), scratches his head
        t = self.chars["talent"]
        root = t["root"]
        self.t_target = kit.empty("talent_R_t", (0, 0, 0), 0.04)
        self.t_pole = kit.empty("talent_R_pole", (-0.6, 0.3, 1.2), 0.04)
        self.t_target.parent = self.t_pole.parent = root
        self.t_ik = mocap.ik_arm(t["arm"], "Right", self.t_target, self.t_pole, influence=0.0)
        # EGO: hands up in front of his face to look at the torn palms; head tracks hands, then the bar
        e = self.chars["ego"]
        root = e["root"]
        self.e_targets = {}
        self.e_ik = []
        for side, sx in (("Left", 1), ("Right", -1)):
            tg = kit.empty(f"ego_{side}_t", (sx * 0.09, -0.42, 0.95), 0.04)
            pl = kit.empty(f"ego_{side}_pole", (sx * 0.45, 0.1, 0.45), 0.04)
            tg.parent = pl.parent = root
            self.e_targets[side] = tg
            self.e_ik.append(mocap.ik_arm(e["arm"], side, tg, pl, influence=0.0))
        self.look = kit.empty("ego_look", (0, -0.45, 0.95), 0.05)
        self.look.parent = root
        hb = e["arm"].pose.bones[kit.MIX + "Head"]
        self.head_track = hb.constraints.new("DAMPED_TRACK")
        self.head_track.target = self.look
        self.head_track.track_axis = _face_axis(e["arm"], "Head")
        self.head_track.influence = 0.0
        # red torn palms (EGO), glowing eyes (EGO)
        self.red_hands = []
        m_red = kit.emission("palms_red", RED, 1.3)
        for k, ch in self.chars.items():
            for side, sx in (("Left", 1), ("Right", -1)):
                s = kit.sphere(f"{k}_{side}_palm", 0.056, seg=16, rings=10)
                kit.set_mat(s, m_red)
                mocap.attach(s, ch["arm"], f"{side}Hand", loc=(sx * 0.075, 0, 0))
                s.hide_render = True
                if k == "ego":
                    self.red_hands.append(s)
        bpy.context.view_layer.update()
        arm = e["arm"]
        hd = arm.matrix_world @ arm.pose.bones[kit.MIX + "Head"].head
        top = arm.matrix_world @ arm.pose.bones[kit.MIX + "HeadTop_End"].head
        hc = (hd + top) / 2 + Vector((0, 0, 0.02))
        self.eyes = []
        m_eye = kit.emission("eyes_red", (1.0, 0.25, 0.18), 7.0)
        for sx in (1, -1):
            s = kit.sphere(f"ego_eye{sx}", 0.021, seg=12, rings=8)
            kit.set_mat(s, m_eye)
            mocap.attach(s, arm, "Head", loc=(hc - hd) + Vector((sx * 0.055, -0.138, 0.015)))
            s.hide_render = True
            self.eyes.append(s)

        # clips (after the rest-pose attachments above)
        off = {"motivation": 0, "talent": 23, "discipline": 41, "ego": 11}
        R = RELEASE
        mocap.sequence(self.chars["motivation"]["arm"], [
            ("hang", 1, R["motivation"], {"offset": off["motivation"]}),
            ("hard_land", R["motivation"], R["motivation"] + 14, {"blend": 3, "offset": 15}),
            ("floor_sit", R["motivation"] + 14, N, {"blend": 12}),
        ])
        mocap.sequence(self.chars["talent"]["arm"], [
            ("hang", 1, R["talent"], {"offset": off["talent"]}),
            ("hard_land", R["talent"], R["talent"] + 14, {"blend": 3, "offset": 15}),
            ("floor_sit", R["talent"] + 14, N, {"blend": 12, "offset": 120}),
        ])
        mocap.sequence(self.chars["discipline"]["arm"], [
            ("hang", 1, R["discipline"], {"offset": off["discipline"]}),
            ("hard_land", R["discipline"], R["discipline"] + 16, {"blend": 3, "offset": 15}),
            ("kneel_one", R["discipline"] + 16, N, {"blend": 12}),
        ])
        mocap.sequence(self.chars["ego"]["arm"], [
            ("hang", 1, R["ego"], {"offset": off["ego"]}),
            ("hard_land", R["ego"], 252, {"blend": 3, "offset": 15}),
            ("kneel", 252, 264, {"blend": 8}),
            ("defeated", 264, 268, {"blend": 5}),
            ("hang", 268, N, {"blend": 4, "offset": 30}),
        ])
        # IK pole angles depend on bone roll: calibrate where each overlay is used
        self.t_target.location = (-0.22, -0.05, 1.33)
        mocap.calibrate_pole(self.chars["talent"]["arm"], "Right", 130)
        for side, sx in (("Left", 1), ("Right", -1)):
            self.e_targets[side].location = (sx * 0.085, -0.40, 0.98)
            mocap.calibrate_pole(self.chars["ego"]["arm"], side, 258)

    # --- lightning aura, floor crack, shockwave, sweat, red light ---------------------------------------
    def _fx(self):
        self.bolts = props.bolt_pool("aura", n=10, pts=7)
        self.cracks = []
        rnd = random.Random(5)
        m_core = bpy.data.materials["bolt_core"]
        m_sh = bpy.data.materials["aura_sheath"]
        c0 = Vector((EGO_X, -0.25, 0.002))
        for i in range(7):
            ang = 2 * math.pi * i / 7 + rnd.uniform(-0.3, 0.3)
            pts = [c0]
            p = c0.copy()
            for k in range(6):
                ang += rnd.uniform(-0.5, 0.5)
                step = rnd.uniform(0.09, 0.16) * (1 - k * 0.08)
                p = p + Vector((math.cos(ang) * step, math.sin(ang) * step * 0.8, 0))
                pts.append(p.copy())
            objs = []
            for kind, rad, mat in (("core", 0.003, m_core), ("sheath", 0.008, m_sh)):
                cu = bpy.data.curves.new(f"crack{i}_{kind}", "CURVE")
                cu.dimensions = "3D"
                cu.bevel_depth = rad
                cu.bevel_resolution = 1
                sp = cu.splines.new("POLY")
                sp.points.add(len(pts) - 1)
                for q, co in zip(sp.points, pts):
                    q.co = (*co, 1)
                ob = kit._link(bpy.data.objects.new(f"crack{i}_{kind}", cu))
                cu.materials.append(mat)
                ob.hide_render = True
                objs.append(ob)
            self.cracks.append(objs)
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.016, major_segments=64, minor_segments=8,
                                         location=(EGO_X, -0.05, BAR_Z), rotation=(math.radians(90), 0, 0))
        self.ring = bpy.context.active_object
        self.ring.name = "shockwave"
        self.ring_mat = kit.emission("shockwave", (1, 0.85, 0.82), 0.0)
        kit.set_mat(self.ring, self.ring_mat)
        self.ring.hide_render = True
        li = bpy.data.lights.new("aura_light", "POINT")
        li.color = RED
        li.energy = 0
        li.shadow_soft_size = 0.4
        self.aura_light = kit._link(bpy.data.objects.new("aura_light", li))
        self.aura_light.visible_glossy = False
        m_sw = kit.emission("sweat", (0.85, 0.92, 1.0), 1.6)
        self.sweat = []
        for i in range(16):
            s = kit.sphere(f"sweat{i}", 0.013, seg=8, rings=6)
            kit.set_mat(s, m_sw)
            s.hide_render = True
            self.sweat.append(s)
        # sweat emitters: (character, first frame, last frame) -> drops thrown from the head
        self.sweat_plan = []
        for k, f0, f1 in (("motivation", 76, 100), ("ego", 198, 238), ("discipline", 345, 372)):
            for f in range(f0, f1, 3):
                self.sweat_plan.append((k, f, rnd.uniform(-1, 1), rnd.uniform(0.6, 1.2)))
        self.hand_marks = []
        m_mark = kit.emission("handmark", RED, 1.8)
        for sx in (-0.27, 0.27):
            b = kit.box(f"mark{sx}", (0.07, 0.055, 0.055), (EGO_X + sx, 0, BAR_Z))
            kit.set_mat(b, m_mark)
            b.hide_render = True
            self.hand_marks.append(b)

    def _camera(self):
        loc, aim, lens = CAM_WIDE
        self.cam = kit.camera("cam", loc=tuple(loc), look_at=tuple(aim), lens=lens)

    # ----------------------------------------------------------------------------- per-frame director
    def update(self, f):
        self._lights(f)
        self._grips(f)
        self._talent(f)
        self._ego(f)
        self._bar(f)
        self._aura(f)
        self._sweat(f)
        self._cam(f)

    def lit(self, k, f):
        """0 dark, 1 lit, flicker/off after the drop."""
        if f < SPOT_ON[k]:
            return 0.0
        r = RELEASE[k]
        if k == "motivation" and 86 <= f < r:
            return 0.15 if (f * 7) % 5 in (0, 3) else 1.0
        if k == "ego":
            if 238 <= f < 244:
                return 0.25 if f % 2 else 0.9
            return 1.0
        if k == "discipline" and 360 <= f < r:
            return 0.4 if f in (362, 366, 367, 370) else 1.0
        if f >= r + 1:
            return 0.0
        return 1.0

    def _lights(self, f):
        for k in XS:
            v = self.lit(k, f)
            pop = 1.0 + 0.6 * math.exp(-(f - SPOT_ON[k]) / 2.0) if f >= SPOT_ON[k] else 1.0
            self.spots[k].data.energy = 720 * v * pop
            self.beams[k]["gain"].inputs[1].default_value = self.beams[k]["strength"] * v * pop
            ch = self.chars[k]
            dropped = f >= RELEASE[k] + 4 and k != "ego"
            if f < SPOT_ON[k]:
                em = 0.05
            elif dropped:
                em = 0.30
            else:
                em = 0.92
            key = (k, round(em, 3))
            if self._last.get(k) != key:
                ch["mat_em"].inputs["Strength"].default_value = em
                g = 0.95 if not dropped else 0.55
                ch["mat_df"].inputs["Color"].default_value = (g, g, g * 0.99, 1)
                self._last[k] = key

    def _hands_mid(self, k, which="mid"):
        arm = self.chars[k]["arm"]
        lh = arm.matrix_world @ arm.pose.bones[kit.MIX + "LeftHand"].head
        rh = arm.matrix_world @ arm.pose.bones[kit.MIX + "RightHand"].head
        return lh if which == "left" else (lh + rh) / 2

    def _grip_weight(self, k, f):
        if k == "ego":
            if f < RELEASE["ego"]:
                return 1.0
            if f < 268:
                return 0.0
            return ramp(f, 268, DROP)
        return 1.0 - ramp(f, RELEASE[k], RELEASE[k] + 3)

    def _grips(self, f):
        """Keep hanging hands exactly on the bar: shift each body so its wrists sit at the grip point."""
        for k, ch in self.chars.items():
            root = ch["root"]
            base = Vector((ch["x"], 0, 0))
            root.location = base
            w = self._grip_weight(k, f)
            shake = self._shake(k, f)
            if w > 0:
                self.sc.frame_set(f)   # evaluate the clip with the root at its base
                which = "left" if (k == "talent" and 120 <= f < RELEASE[k]) else "mid"
                hm = self._hands_mid(k, which)
                gx = ch["x"] + (0.26 if which == "left" else -0.01)
                sag = self._sag(f) if k == "ego" else 0.0
                target = Vector((gx, 0.0, GRIP_Z - sag))
                delta = target - hm
                root.location = base + delta * w + shake
            else:
                root.location = base + shake

    def _shake(self, k, f):
        amp = 0.0
        if k == "motivation":
            amp = 0.012 * ramp(f, 68, 98) * (f < RELEASE[k])
        elif k == "ego":
            amp = 0.02 * ramp(f, 192, 236) * (f < RELEASE[k])
        elif k == "discipline":
            amp = 0.012 * ramp(f, 338, 370) * (f < RELEASE[k])
        if amp <= 0:
            return Vector((0, 0, 0))
        r = random.Random(f * 131 + self.chars[k]["seed"])
        return Vector((r.uniform(-1, 1) * amp, r.uniform(-1, 1) * amp * 0.4, r.uniform(-1, 1) * amp * 0.6))

    def _talent(self, f):
        t = self.chars["talent"]
        if f < 120 or f >= RELEASE["talent"] + 2:
            self.t_ik.influence = 0.0
            return
        base = Vector((-0.22, -0.05, 1.33))          # hand down by his side (body is ~0.5 m off the floor)
        head = Vector((-0.10, -0.06, 2.05))           # scratching the back of the head
        k = ramp(f, 140, 146) * (1 - ramp(f, 152, 158))
        wob = 0.025 * math.sin(f * 1.7) * k
        self.t_target.location = base.lerp(head, k) + Vector((wob, 0, 0))
        self.t_ik.influence = ramp(f, 120, 125) * (1 - ramp(f, RELEASE["talent"] - 1, RELEASE["talent"] + 2))

    def _ego(self, f):
        palms = ramp(f, 254, 259) * (1 - ramp(f, 262, 266))
        for c in self.e_ik:
            c.influence = palms
        for side, sx in (("Left", 1), ("Right", -1)):
            self.e_targets[side].location = (sx * 0.085, -0.40, 0.98 + 0.02 * math.sin(f * 0.5))
        # head: down at the palms, then up at the bar
        up = ramp(f, 261, 265)
        self.look.location = Vector((0, -0.45, 0.95)).lerp(Vector((0, -0.25, BAR_Z + 0.6)), up)
        self.head_track.influence = ramp(f, 253, 257) * (1 - ramp(f, 266, 270))
        for s in self.red_hands:
            s.hide_render = f < 245
        for s in self.eyes:
            on = f >= 262
            s.hide_render = not on
            if on:
                k = 1 + 0.6 * math.exp(-(f - 262) / 4)
                s.scale = (k, k, k)
        for b in self.hand_marks:
            b.hide_render = f < DROP

    def _sag(self, f):
        if f < DROP:
            return 0.0
        t = (f - DROP) / FPS
        return 0.055 + 0.06 * math.exp(-t * 5) * math.cos(t * 26)

    def _bar(self, f):
        dips = [(EGO_X, self._sag(f), 0.38)] if f >= DROP else []
        if self._last.get("bar") != tuple(round(d[1], 4) for d in dips):
            self.bar["set_bend"](dips)
            self._last["bar"] = tuple(round(d[1], 4) for d in dips)
        for b in self.hand_marks:
            b.location.z = BAR_Z - self._sag(f)
        # shockwave
        if DROP <= f < DROP + 14:
            k = (f - DROP) / 13
            s = 0.1 + 2.4 * (1 - (1 - k) ** 2.5)
            self.ring.hide_render = False
            self.ring.scale = (s, s, s)
            em = next(n for n in self.ring_mat.node_tree.nodes if n.type == "EMISSION")
            em.inputs["Strength"].default_value = 4.5 * (1 - k) ** 1.5
        else:
            self.ring.hide_render = True

    def _ego_points(self):
        arm = self.chars["ego"]["arm"]
        names = ["LeftHand", "RightHand", "LeftForeArm", "RightForeArm", "LeftArm", "RightArm", "Head", "Spine1",
                 "Hips", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot"]
        return {n: arm.matrix_world @ arm.pose.bones[kit.MIX + n].head for n in names}

    def aura_level(self, f):
        if f < 262:
            return 0.0
        if f < DROP:
            return lerp(0.35, 0.9, ramp(f, 262, DROP - 1))
        if f < DROP + 10:
            return 1.0
        return 0.5 + 0.12 * math.sin(f * 0.37)

    def _aura(self, f):
        lvl = self.aura_level(f)
        pool = self.bolts
        if lvl <= 0:
            for i in range(pool["n"]):
                pool["set"](i, None, False)
            for objs in self.cracks:
                for o in objs:
                    o.hide_render = True
            self.aura_light.data.energy = 0
            return
        self.sc.frame_set(f)
        pts = self._ego_points()
        keys = list(pts)
        r = random.Random(f * 977)
        burst = DROP <= f < DROP + 8
        for i in range(pool["n"]):
            vis = r.random() < (lvl if not burst else 1.0)
            if not vis:
                pool["set"](i, None, False)
                continue
            if burst and i < 4:   # along the bar from his grip
                a = Vector((EGO_X + r.uniform(-0.3, 0.3), -0.02, BAR_Z - self._sag(f)))
                d = Vector((r.choice((-1, 1)), 0, r.uniform(-0.15, 0.15))).normalized()
                L = r.uniform(0.6, 1.3)
            else:
                a = pts[r.choice(keys)] + Vector((r.uniform(-0.05, 0.05), -0.06, r.uniform(-0.05, 0.05)))
                ang = r.uniform(0, 2 * math.pi)
                d = Vector((math.cos(ang), r.uniform(-0.35, 0.1), math.sin(ang))).normalized()
                L = r.uniform(0.22, 0.6) * (1.6 if burst else 1.0)
            side = d.cross(Vector((0, 1, 0)))
            if side.length < 1e-3:
                side = Vector((1, 0, 0))
            side.normalize()
            n = pool["pts"]
            path = []
            for j in range(n):
                u = j / (n - 1)
                jit = (r.uniform(-1, 1) * 0.06 * L) * math.sin(math.pi * u) if 0 < j < n - 1 else 0.0
                path.append(a + d * (L * u) + side * jit + Vector((0, r.uniform(-0.02, 0.02), 0)))
            pool["set"](i, path, True)
        rev = ramp(f, 264, 271)
        for i, objs in enumerate(self.cracks):
            for o in objs:
                o.hide_render = rev <= 0
                o.data.bevel_factor_end = max(0.001, rev * (0.85 + 0.15 * ((i * 37) % 7) / 6))
        chest = pts["Spine1"]
        self.aura_light.location = chest + Vector((0, -0.4, 0.1))
        self.aura_light.data.energy = (60 if burst else 22) * lvl * (0.6 + 0.4 * r.random())

    def _sweat(self, f):
        live = []
        for k, f0, sx, sp in self.sweat_plan:
            age = f - f0
            if 0 <= age < 9:
                live.append((k, f0, sx, sp, age))
        arm_cache = {}
        for i, s in enumerate(self.sweat):
            if i >= len(live):
                s.hide_render = True
                continue
            k, f0, sx, sp, age = live[i]
            if k not in arm_cache:
                arm = self.chars[k]["arm"]
                arm_cache[k] = arm.matrix_world @ arm.pose.bones[kit.MIX + "HeadTop_End"].head
            head = arm_cache[k]
            t = age / FPS
            s.hide_render = False
            s.location = head + Vector((sx * 0.9 * sp * t, -0.3 * t, -0.08 + 1.2 * sp * t - 4.9 * t * t))

    def _cam(self, f):
        wide_loc, wide_aim, _ = CAM_WIDE
        close_loc, close_aim = Vector((EGO_X - 0.35, -5.4, 1.25)), Vector((EGO_X, 0, 0.95))
        mid_loc, mid_aim = Vector((EGO_X * 0.45, -8.4, 1.8)), Vector((EGO_X * 0.55, 0, 1.6))
        end_loc, end_aim = Vector((EGO_X * 0.75, -7.6, 2.0)), Vector((EGO_X, 0, 1.75))
        if f < 240:
            loc, aim = wide_loc, wide_aim
        elif f < 266:
            k = ramp(f, 240, 262)
            loc, aim = wide_loc.lerp(close_loc, k), wide_aim.lerp(close_aim, k)
        elif f < DROP:
            k = ramp(f, 266, DROP)
            loc, aim = close_loc.lerp(mid_loc, k), close_aim.lerp(mid_aim, k)
        elif f < 380:
            k = ramp(f, DROP + 8, 315)
            loc, aim = mid_loc.lerp(wide_loc, k), mid_aim.lerp(wide_aim, k)
        else:
            k = ramp(f, 380, N + 25)
            loc, aim = wide_loc.lerp(end_loc, k), wide_aim.lerp(end_aim, k)
        amp = 0.0
        for f0, a, dcy in ((244, 0.03, 4.0), (DROP, 0.07, 7.0)):
            if f >= f0:
                amp += a * math.exp(-(f - f0) / dcy)
        r = random.Random(f * 7 + 1)
        loc = loc + Vector((r.uniform(-1, 1) * amp, 0, r.uniform(-1, 1) * amp))
        self.cam.location = loc
        self.cam.rotation_euler = (aim - loc).to_track_quat("-Z", "Y").to_euler()
        lens = 50.0
        if f >= DROP:
            lens += 7.0 * math.exp(-(f - DROP) / 5.0)
        self.cam.data.lens = lens

    # ----------------------------------------------------------------------------- screen-space extras
    def _screen(self, p):
        from bpy_extras.object_utils import world_to_camera_view as w2c
        v = w2c(self.sc, self.cam, Vector(p))
        return v.x, 1 - v.y

    def glows(self, f):
        out = []
        for k, x in XS.items():
            v = self.lit(k, f)
            if v > 0:
                sx, sy = self._screen((x, -0.9, 5.4))
                out.append((sx, sy, 0.05, (255, 245, 225), 0.55 * v))
        lvl = self.aura_level(f)
        if lvl > 0:
            self.sc.frame_set(f)
            pts = self._ego_points()
            sx, sy = self._screen(pts["Spine1"])
            out.append((sx, sy, 0.16, (255, 40, 25), 0.30 * lvl))
            hx, hy = self._screen(pts["Head"] + Vector((0, -0.15, 0.08)))
            out.append((hx, hy, 0.035, (255, 70, 50), 0.6))
        if DROP <= f < DROP + 10:
            sx, sy = self._screen((EGO_X, 0, BAR_Z))
            out.append((sx, sy, 0.45, (255, 235, 230), 0.9 * (1 - (f - DROP) / 10)))
        return out

    def overlay(self, f):
        """Text ops for the post pass: labels follow the characters, timer, top text, watermark."""
        ops = []
        for k, x in XS.items():
            if f < SPOT_ON[k]:
                continue
            sx, sy = self._screen((x, 0, BAR_Z + 0.30))
            dropped = f >= RELEASE[k] + 2 and k != "ego"
            col = (95, 95, 95) if dropped else (240, 240, 240)
            if k == "ego" and f >= 262:
                col = (255, 120, 105)
            a = 1.0 - ramp(f, 240, 246) * (1 - ramp(f, 296, 306))   # hidden while the camera is close
            if a > 0:
                ops.append((LABELS[k], sx, sy, 21, False, col, a, 2))
        if f >= 22:
            s = int(timer_seconds(f))
            pop = 1.0 + 0.25 * math.exp(-(f - 390) / 3) if f >= 390 else 1.0
            col = (255, 110, 95) if 238 <= f < DROP else (255, 255, 255)
            ops.append((f"{s // 60}:{s % 60:02d}", 0.5, 0.215, int(78 * pop), True, col, clamp((f - 21) / 4), 6))
        if 20 <= f < 398:
            ops.append(("LAST ONE HANGING WINS.", 0.5, 0.115, 50, True, (255, 255, 255), clamp((f - 19) / 6), 3))
        if f >= 398:
            ops.append(("YOU CAN'T OUTLAST SOMEONE", 0.5, 0.100, 46, True, (255, 255, 255), clamp((f - 397) / 3), 3))
        if f >= 405:
            ops.append(("WITH SOMETHING TO PROVE.", 0.5, 0.140, 46, True, (255, 255, 255), clamp((f - 404) / 3), 3))
        ops.append(("@EYEOFEGO", 0.5, 0.86, 24, False, (110, 110, 110), 1.0, 6))
        return ops


def overlay_ops(f):
    return []          # this film stores its per-frame text ops next to each frame (Film.overlay)


IMPACT = {DROP: "invert", DROP + 1: "invert", DROP + 2: "flash"}
COVER_FRAME = 300


# ----------------------------------------------------------------------------- sound

def audio_cues():
    c = [(SPOT_ON[k], "switch", 0.55, None) for k in XS]
    c += [(f, "creak", 0.16, None) for f in (45, 135, 215, 320)]
    for k in ("motivation", "talent", "discipline"):
        c += [(RELEASE[k], "whoosh", 0.18, None), (RELEASE[k] + 6, "thud", 0.65, None)]
    c += [(RELEASE["ego"], "whoosh", 0.3, None), (RELEASE["ego"] + 6, "thud", 0.95, None), (RELEASE["ego"] + 6, "hit", 0.5, None)]
    c += [(250, "heart", 0.8, None), (259, "heart", 0.9, None)]
    c += [(262, "zap", 0.45, None), (264, "crack", 0.55, None), (268, "zap", 0.55, None)]
    c += [(DROP, "boom", 1.0, None), (DROP, "thunder", 0.75, None), (DROP, "clank", 0.6, None), (DROP, "zap", 0.6, None)]
    c += [(f, "zap", 0.22 + 0.06 * ((f // 7) % 3), None) for f in range(292, N, 19)]
    c += [(f, "creak", 0.2, None) for f in (300, 350)]
    c += [(390, "tick", 0.4, None), (N - 1, "tick", 0.35, None)]
    return c


def soundtrack(music=True):
    import numpy as np

    from ...audio import bed, sfx
    sr = sfx.SR
    total = N / FPS
    out = np.zeros((int(sr * total), 2), np.float32)
    for f, name, gain, until in audio_cues():
        x = sfx.make(name) * gain
        i = int((f - 1) / FPS * sr)
        x = x[: max(0, len(out) - i)]
        out[i:i + len(x)] += x
    if music:
        m, _ = bed.make_bed(total, (DROP - 1) / FPS, bpm=100, seed=9)
        m = m[: len(out)].copy()
        a, b = int((RELEASE["ego"] - 1) / FPS * sr), int((DROP - 1) / FPS * sr)
        fade = int(0.12 * sr)
        m[a:a + fade] *= np.linspace(1, 0, fade)[:, None]
        m[a + fade:b] = 0.0      # silence while he is on his knees
        out[: len(m)] += m * 0.75
    peak = float(np.max(np.abs(out))) or 1.0
    out = out / peak
    return (np.tanh(out * 1.8) / np.tanh(1.8) * 0.95).astype(np.float32)
