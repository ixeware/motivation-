"""PROCRASTINATOR vs PLANNER: 3D short in the reference style (Blender + Mixamo clips).

13 s at 30 fps (frames 1..390), every word on screen in English:
  1-60     30 DAYS LEFT. The planner types (progress 0 -> 25%), the procrastinator laughs at his phone.
  61-150   His calendar pages tear off 30 -> 7 and fly into a grey cloud that keeps growing (25 -> 75%).
  151-240  7 -> 3 -> 2 -> 1 DAY LEFT (red). Rain, lightning hits his desk. He drops the phone, grabs his
           head, then writes frantically: paper stacks and a coffee-cup tower grow. The planner hits 100%
           and sips coffee in warm light.
  241-300  DROP: DUE TODAY. The cloud bursts, every skipped day falls back as a slow paper hurricane,
           impact frame + shockwave. The planner keeps sipping.
  301-390  The planner's board turns into a glowing A+ (fist pump). He sits under the paper, face in
           hands; the calendar resets to 30 DAYS LEFT and he reaches for the phone again (loops).
Top text: YOU DIDN'T SAVE TIME. -> (on the drop) YOU BORROWED IT. / WITH INTEREST.
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Euler, Matrix, Vector

from .. import kit, mocap, props

SLUG = "procrastinator_vs_planner"
FPS = 30
N = 390
DROP = 241
RESET = 340            # new "30 DAYS LEFT" page starts falling onto the calendar
RESET_LAND = 347
XP, XL = -0.85, 0.85   # procrastinator (screen left), planner (screen right)
DESK_Y, DESK_H = -0.62, 0.69
CAL = Vector((XP + 0.50, 0.45, 2.00))
BOARD = Vector((XL - 0.02, 0.45, 2.00))
CLOUD = Vector((XP - 0.33, -0.10, 1.80))
CAM_LOC = Vector((0, -9.0, 1.95))
CAM_AIM = Vector((0, 0, 1.52))

META = {
    "slug": SLUG,
    "caption": "You didn't save time. You borrowed it, with interest. 30 days feels like forever until "
               "it's due today. Which desk are you sitting at right now?",
    "hashtags": ["procrastination", "discipline", "motivation", "studymotivation", "productivity",
                 "mindset", "selfimprovement", "3danimation"],
}


# ----------------------------------------------------------------------------- timing helpers

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=2.0):
    return 1 - (1 - clamp(x)) ** p


def ramp(f, f0, f1):
    return smooth((f - f0) / max(1e-6, f1 - f0))


def lerp(a, b, t):
    return a + (b - a) * t


def _tears():
    out = []

    def burst(first, last, f0, f1):
        nums = list(range(first, last, -1))
        for i, n in enumerate(nums):
            out.append((round(f0 + (f1 - f0) * i / max(1, len(nums) - 1)), n))

    burst(30, 21, 62, 90)     # 30..22 -> front shows 21
    burst(21, 14, 98, 118)    # -> 14
    burst(14, 7, 126, 146)    # -> 7
    burst(7, 3, 152, 160)     # -> 3
    out += [(185, 3), (210, 2), (DROP, 1)]
    return out


TEARS = _tears()
TEAR_DUR = 16
PROGRESS = [(1, 0), (60, 25), (100, 50), (140, 75), (165, 100)]


def front_page(f):
    """(number, caption, red) shown on the calendar at frame f."""
    if f >= RESET_LAND:
        return "30", "DAYS LEFT", False
    torn = [n for t, n in TEARS if t <= f]
    if not torn:
        return "30", "DAYS LEFT", False
    n = min(torn) - 1
    if n <= 0:
        return "DUE", "TODAY", True
    return str(n), "DAY LEFT" if n == 1 else "DAYS LEFT", n == 1


def progress(f):
    for (f0, v0), (f1, v1) in zip(PROGRESS, PROGRESS[1:]):
        if f <= f1:
            return lerp(v0, v1, smooth((f - f0) / (f1 - f0)))
    return PROGRESS[-1][1]


# ----------------------------------------------------------------------------- build

class Film:
    def __init__(self, w=1080, h=1920, samples=8):
        self.sc = kit.reset(fps=FPS, w=w, h=h)
        kit.setup_render(self.sc, samples=samples, bloom=False)
        sc = self.sc
        sc.render.use_persistent_data = True
        sc.cycles.glossy_bounces = 1
        sc.cycles.transmission_bounces = 0
        sc.cycles.volume_bounces = 0
        sc.cycles.adaptive_threshold = 0.05
        sc.frame_start, sc.frame_end = 1, N
        kit.toon()
        kit.outline_mat()
        self.rng = random.Random(7)
        self._last = {}
        self._characters()
        self._set()
        self._weather()
        self._clutter()
        self._hurricane()
        self._lights_camera()
        self._ik_and_props()

    # --- characters + mocap ---------------------------------------------------------------
    def _characters(self):
        fig = dict(limb=0.05, torso=0.095, head=0.15)
        self.proc = mocap.character("proc", "idle", **fig)
        self.plan = mocap.character("plan", "idle", **fig)
        self.proc.parent.location = (XP, 0, 0)
        self.plan.parent.location = (XL, 0, 0)
        mocap.sequence(self.proc, [
            ("laugh", 1, 154),
            ("disbelief", 154, 204, {"blend": 6, "offset": 6}),
            ("writing", 204, DROP, {"blend": 6, "speed": 1.9}),
            ("disbelief", DROP, 300, {"blend": 4, "offset": 14, "speed": 0.55}),
            ("slump", 300, 364, {"blend": 10, "offset": 18}),
            ("laugh", 364, N, {"blend": 10}),
        ])
        mocap.sequence(self.plan, [
            ("typing", 1, 168),
            ("idle", 168, 300, {"blend": 14}),
            ("victory", 300, N, {"blend": 10}),
        ])

    # --- desks, chairs, laptop, calendar, board --------------------------------------------
    def _set(self):
        for x, nm in ((XP, "p"), (XL, "l")):
            props.desk(f"desk_{nm}", (x, DESK_Y, 0), h=DESK_H)
            props.chair(f"chair_{nm}", (x, 0.02, 0))
        self.laptop = props.laptop("laptop", (XL, -0.60, DESK_H), w=0.32, d=0.21)
        self.cal = props.calendar("cal", tuple(CAL))
        self.cal["set"](self.cal["front"], "30", "DAYS LEFT", red=False)
        self.pages = [self.cal["page"](f"fly{i}", "29", "DAYS LEFT", y=-0.010 - 0.002 * i) for i in range(6)]
        for p in self.pages:
            self._show_page(p, False)
        self.reset_page = self.cal["page"]("reset", "30", "DAYS LEFT", y=-0.03)
        self._show_page(self.reset_page, False)
        self.board = props.progress_board("board", tuple(BOARD))
        self.aplus = kit.text("aplus", "A+", size=0.27, loc=(0, -0.02, -0.01), color=(0.45, 1.0, 0.6), strength=1.25,
                              bold=True, parent=self.board["root"])
        self.aplus.hide_render = True
        floor = kit.plane("floor", 30, 30, (0, 0, 0))
        kit.set_mat(floor, kit.glossy_floor())

    def _show_page(self, p, on):
        for k in ("bg", "num", "cap"):
            p[k].hide_render = not on

    # --- cloud, rain, lightning, shockwave ---------------------------------------------------
    def _weather(self):
        self.cloud = props.cloud("cloud", tuple(CLOUD), w=0.85, puffs=9, color=(0.42, 0.42, 0.44, 1))
        self.cloud_mat = self.cloud["balls"][0].active_material
        self.cloud_home = [b.location.copy() for b in self.cloud["balls"]]
        self.cloud_scale = [b.scale.copy() for b in self.cloud["balls"]]
        self.rain = props.rain("rain", (CLOUD.x, CLOUD.y - 0.1, 0), w=0.85, depth=0.35, top=CLOUD.z - 0.12,
                               bottom=DESK_H + 0.02, drops=48, speed=4.5, fps=FPS, frames=(1, N + 10))
        for d in self.rain["drops"]:
            d.hide_render = True
        tgt = (XP + 0.2, DESK_Y + 0.05, DESK_H + 0.01)
        self.bolts = [props.lightning("bolt1", (CLOUD.x + 0.15, CLOUD.y, CLOUD.z - 0.15), tgt, seed=11, branches=3),
                      props.lightning("bolt2", (CLOUD.x - 0.10, CLOUD.y, CLOUD.z - 0.15), (XP - 0.45, DESK_Y, DESK_H), seed=5,
                                      branches=2)]
        for b in self.bolts:
            for o in b["bolts"]:
                o.hide_render = True
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.018, major_segments=64, minor_segments=8,
                                         location=tuple(CLOUD), rotation=(math.radians(90), 0, 0))
        self.ring = bpy.context.active_object
        self.ring.name = "shockwave"
        self.ring_mat = kit.emission("shockwave", (1, 1, 1), 0.0)
        kit.set_mat(self.ring, self.ring_mat)
        self.ring.hide_render = True
        li = bpy.data.lights.new("burst", "POINT")
        li.energy = 0
        li.shadow_soft_size = 0.5
        self.burst = kit._link(bpy.data.objects.new("burst", li))
        self.burst.location = CLOUD
        self.burst.visible_glossy = False
        for b in self.bolts:
            b["flash"].visible_glossy = False

    # --- paper stacks + coffee cups (frantic phase) --------------------------------------------
    def _clutter(self):
        self.stacks = [props.paper_stack("stack1", (XP + 0.33, DESK_Y - 0.02, DESK_H), n=16, seed=3),
                       props.paper_stack("stack2", (XP - 0.20, DESK_Y - 0.12, DESK_H), n=11, seed=4)]
        for st in self.stacks:
            for s in st["sheets"]:
                s.hide_render = True
        self.cups = []
        for k in range(7):
            c = props.cup(f"cup{k}", (XP - 0.44, DESK_Y - 0.14, DESK_H + 0.095 * k))
            c["root"].rotation_euler.z = self.rng.uniform(-0.6, 0.6)
            self.cups.append(c)

    # --- the skipped days come back: slow paper hurricane ------------------------------------------
    def _hurricane(self):
        mat_paper = kit.toon("paper_toon", (0.96, 0.96, 0.94, 1), flat=0.75)
        self.sheets = []
        nums = list(range(29, 3, -1)) + [None] * 10
        self.rng.shuffle(nums)
        for i, n in enumerate(nums):
            sh = kit.plane(f"sheet{i}", 0.24, 0.31)
            kit.set_mat(sh, mat_paper)
            txt = None
            if n is not None:
                txt = kit.text(f"sheet{i}_n", str(n), size=0.15, loc=(0, 0.02, 0.003), rot=(0, 0, 0),
                               color=(0.05, 0.05, 0.05), strength=1.0, bold=True, parent=sh)
            on_desk = i % 5 < 3
            if on_desk:
                land = Vector((XP + self.rng.uniform(-0.48, 0.48), DESK_Y + self.rng.uniform(-0.24, 0.22),
                               DESK_H + 0.004 + 0.003 * (i % 7)))
            else:
                land = Vector((XP + self.rng.uniform(-1.05, 0.95), self.rng.uniform(-1.55, -1.0), 0.003 + 0.002 * (i % 5)))
            self.sheets.append({
                "obj": sh, "txt": txt, "land": land, "f_land": DROP + self.rng.randint(26, 58),
                "r": self.rng.uniform(0.35, 1.0), "th0": self.rng.uniform(0, 2 * math.pi),
                "turns": self.rng.uniform(0.6, 1.4) * self.rng.choice((-1, 1)),
                "rx": self.rng.uniform(2, 5) * self.rng.choice((-1, 1)), "ry": self.rng.uniform(1, 4),
                "rz_land": self.rng.uniform(-0.8, 0.8), "z0": CLOUD.z + self.rng.uniform(-0.1, 0.25),
                "delay": self.rng.randint(0, 6),
            })
            sh.hide_render = True

    # --- lights + camera ------------------------------------------------------------------------
    def _lights_camera(self):
        self.key_p = kit.spot("key_p", (XP, -1.3, 3.5), (XP, -0.35, 0.7), energy=420, size_deg=50, blend=1.0, radius=0.35)
        self.key_l = kit.spot("key_l", (XL, -1.3, 3.5), (XL, -0.35, 0.7), energy=420, size_deg=50, blend=1.0, radius=0.35)
        kit.spot("wall_p", (CAL.x, -1.5, 3.6), (CAL.x, 0.45, 2.0), energy=120, size_deg=30, blend=0.8, radius=0.3)
        kit.spot("wall_l", (BOARD.x, -1.5, 3.6), (BOARD.x, 0.45, 2.0), energy=120, size_deg=30, blend=0.8, radius=0.3)
        warm = bpy.data.lights.new("warm", "POINT")
        warm.color = (1.0, 0.76, 0.48)
        warm.shadow_soft_size = 0.6
        warm.energy = 0
        self.warm = kit._link(bpy.data.objects.new("warm", warm))
        self.warm.location = (XL - 0.1, -1.0, 1.7)
        glow = bpy.data.lights.new("aplus_glow", "POINT")
        glow.color = (0.45, 1.0, 0.6)
        glow.energy = 0
        self.aplus_glow = kit._link(bpy.data.objects.new("aplus_glow", glow))
        self.aplus_glow.location = BOARD + Vector((0, -0.35, 0))
        self.cam = kit.camera("cam", loc=tuple(CAM_LOC), look_at=tuple(CAM_AIM), lens=50)
        self.cam_rot = self.cam.rotation_euler.copy()

    # --- IK on top of the clips: phone in both hands, coffee sips ---------------------------------
    def _ik_and_props(self):
        sc = self.sc
        arm = self.proc
        chest = "Spine2"
        # hand + elbow targets glued to the chest, placed relative to the head while laughing (frame 30)
        sc.frame_set(30)
        head = arm.matrix_world @ arm.pose.bones[kit.MIX + "Head"].head
        hold = {"Right": head + Vector((-0.06, -0.25, -0.09)), "Left": head + Vector((0.06, -0.25, -0.09))}
        poles = {"Right": head + Vector((-0.45, 0.25, -0.75)), "Left": head + Vector((0.45, 0.25, -0.75))}
        self.p_targets, self.p_ik = {}, []
        for side in ("Right", "Left"):
            t = self._bone_child(f"proc_{side}_t", arm, chest, hold[side], 30)
            p = self._bone_child(f"proc_{side}_pole", arm, chest, poles[side], 30)
            c = self._ik(arm, f"{side}ForeArm", t, p, frame=30)
            self.p_targets[side] = (t, hold[side])
            self.p_ik.append(c)
        # phone in the hands: midpoint of both palms, screen turned to the face
        self.phone = props.phone("phone_hand", glow=3.2, light=5.0, size=1.25)
        ph = self.phone["root"]
        for side, infl in (("Right", 1.0), ("Left", 0.5)):
            cl = ph.constraints.new("COPY_LOCATION")
            cl.target, cl.subtarget, cl.head_tail, cl.influence = arm, kit.MIX + f"{side}Hand", 0.6, infl
        tt = ph.constraints.new("TRACK_TO")
        tt.target, tt.subtarget = arm, kit.MIX + "Head"
        tt.track_axis, tt.up_axis = "TRACK_Y", "UP_Z"
        # dropped phone on the desk (falls from the hands at f156, picked up again at f370)
        self.phone_desk = props.phone("phone_desk", glow=0.9, light=0.6)
        pd = self.phone_desk["root"]
        rest = Vector((XP + 0.16, DESK_Y + 0.12, DESK_H + 0.006))
        self.phone_rest = rest
        sc.frame_set(156)
        start = ph.matrix_world.translation.copy()
        for f, loc, rot in ((156, start, (0.3, 0.2, 0.1)), (160, (start + rest) / 2 + Vector((0, 0, 0.05)), (1.4, 0.6, 0.5)),
                            (163, rest + Vector((0, 0, 0.03)), (math.radians(92), 0, 0.3)),
                            (166, rest, (math.radians(90), 0, 0.32))):
            pd.location = loc
            pd.rotation_euler = rot
            pd.keyframe_insert("location", frame=f)
            pd.keyframe_insert("rotation_euler", frame=f)
        # hands reach the desk phone at the end: target keys in chest space
        for side, dx in (("Right", -0.04), ("Left", 0.05)):
            t, hold_w = self.p_targets[side]
            reach = rest + Vector((dx, 0.0, 0.05))
            self._key_bone_child(t, arm, chest, hold_w, 30, 1)
            self._key_bone_child(t, arm, chest, hold_w, 30, 361)
            self._key_bone_child(t, arm, chest, reach, 366, 366)
            self._key_bone_child(t, arm, chest, reach, 370, 370)
            self._key_bone_child(t, arm, chest, hold_w, 30, 380)
        for c in self.p_ik:
            for f, v in ((1, 1), (150, 1), (158, 0), (362, 0), (367, 1), (N, 1)):
                c.influence = v
                c.keyframe_insert("influence", frame=f)
        # planner: right arm IK for two coffee sips, cup follows the hand while held
        arm = self.plan
        cup_home = Vector((XL - 0.28, DESK_Y + 0.10, DESK_H))
        self.cup = props.cup("coffee", tuple(cup_home), r=0.045, h=0.12)
        mouth = Vector((XL - 0.05, -0.30, 1.00))
        root = arm.parent
        t = kit.empty("plan_R_t", tuple(cup_home + Vector((0, 0, 0.04)) - Vector((XL, 0, 0))))
        t.parent = root
        pole = kit.empty("plan_R_pole", (-0.45, 0.3, 0.35))
        pole.parent = root
        sc.frame_set(200)
        c = self._ik(arm, "RightForeArm", t, pole, frame=200)
        grab = cup_home + Vector((0, 0, 0.04)) - Vector((XL, 0, 0))
        lip = mouth - Vector((XL, 0, 0))
        keys = []
        for s0 in (176, 256):
            keys += [(s0, grab, 0), (s0 + 6, grab, 1), (s0 + 10, grab, 1), (s0 + 20, lip, 1), (s0 + 34, lip, 1),
                     (s0 + 44, grab, 1), (s0 + 47, grab, 1), (s0 + 53, grab, 0)]
        for f, loc, infl in keys:
            t.location = loc
            t.keyframe_insert("location", frame=f)
            c.influence = infl
            c.keyframe_insert("influence", frame=f)
        cl = self.cup["root"].constraints.new("COPY_LOCATION")
        cl.target, cl.subtarget, cl.head_tail = arm, kit.MIX + "RightHand", 0.3
        for s0 in (176, 256):
            for f, v in ((s0 + 9, 0), (s0 + 11, 1), (s0 + 44, 1), (s0 + 46, 0)):
                cl.influence = v
                cl.keyframe_insert("influence", frame=f)

    def _ik(self, arm, bone, target, pole, frame):
        pb = arm.pose.bones[kit.MIX + bone]
        c = pb.constraints.new("IK")
        c.target, c.pole_target, c.chain_count, c.use_tail = target, pole, 2, True

        def dist(a):
            c.pole_angle = math.radians(a)
            arm.update_tag()
            self.sc.frame_set(frame)
            j = arm.matrix_world @ arm.pose.bones[kit.MIX + bone].head
            return (j - pole.matrix_world.translation).length

        best = min(range(-180, 180, 30), key=dist)
        best = min((best + d for d in range(-15, 16, 3)), key=dist)
        c.pole_angle = math.radians(best)
        return c

    def _bone_matrix(self, arm, bone, frame):
        self.sc.frame_set(frame)
        pb = arm.pose.bones[kit.MIX + bone]
        return arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))

    def _bone_child(self, name, arm, bone, world, frame):
        e = kit.empty(name, (0, 0, 0), 0.04)
        e.parent = arm
        e.parent_type = "BONE"
        e.parent_bone = kit.MIX + bone
        e.matrix_parent_inverse = Matrix.Identity(4)
        e.matrix_basis = self._bone_matrix(arm, bone, frame).inverted() @ Matrix.Translation(world)
        return e

    def _key_bone_child(self, e, arm, bone, world, at_frame, key_frame):
        """Key e (bone child) so it sits at `world` as seen at frame `at_frame`."""
        m = self._bone_matrix(arm, bone, at_frame).inverted() @ Matrix.Translation(world)
        e.location = m.translation
        e.keyframe_insert("location", frame=key_frame)

    # ----------------------------------------------------------------------------- director
    def _text(self, ob, body):
        if self._last.get(ob.name) != body:
            ob.data.body = body
            self._last[ob.name] = body

    def _set_page_once(self, key, page, number, caption, red):
        state = (number, caption, red)
        if self._last.get(key) != state:
            self.cal["set"](page, number, caption, red=red)
            self._last[key] = state

    def glows(self, f):
        """Screen-space light blooms for the post pass: (x, y, radius, (r,g,b), strength), frame fractions."""
        from bpy_extras.object_utils import world_to_camera_view as w2c
        sc, cam = self.sc, self.cam

        def at(p):
            v = w2c(sc, cam, Vector(p))
            return v.x, 1 - v.y

        out = []
        held = f < 156 or f >= 370
        ph = (self.phone if held else self.phone_desk)["root"].matrix_world.translation
        x, y = at(ph)
        flick = 1 + 0.08 * math.sin(f * 0.9) + 0.05 * math.sin(f * 2.3)
        out.append((x, y, 0.055 if held else 0.03, (185, 215, 255), (0.85 if held else 0.35) * flick))
        x, y = at(self.laptop["screen"].matrix_world.translation)
        out.append((x, y, 0.07, (190, 220, 255), 0.30))
        for i, b in enumerate(self.bolts):
            e = b["flash"].data.energy
            if e > 0:
                x, y = at(b["flash"].location)
                out.append((x, y, 0.32, (215, 205, 255), 0.45 * e / 900))
        e = self.burst.data.energy
        if e > 0:
            x, y = at(CLOUD)
            out.append((x, y, 0.5, (255, 255, 255), 0.8 * e / 1200))
        if f >= 300:
            x, y = at(BOARD + Vector((0, -0.05, 0)))
            out.append((x, y, 0.10, (110, 255, 150), 0.32 * ramp(f, 300, 306) * (1 + 0.1 * math.sin(f * 0.3))))
        w = ramp(f, 165, 195)
        if w > 0:
            x, y = at(Vector((XL, -0.7, 1.1)))
            out.append((x, y, 0.22, (255, 185, 110), 0.22 * w))
        return out

    def update(self, f):
        self._calendar(f)
        self._progress(f)
        self._cloud(f)
        self._storm(f)
        self._frantic(f)
        self._burst(f)
        self._paper(f)
        self._phones(f)
        self._lights(f)
        self._camera(f)

    def _calendar(self, f):
        num, cap, red = front_page(f)
        self._set_page_once("front", self.cal["front"], num, cap, red)
        # torn pages in flight (pool)
        flying = [(t, n) for t, n in TEARS if t <= f < t + (TEAR_DUR if t != DROP else 10)]
        for i, p in enumerate(self.pages):
            if i >= len(flying):
                self._show_page(p, False)
                continue
            t0, n = flying[i]
            self._show_page(p, True)
            red_p = n <= 1
            self._set_page_once(f"fly{i}", p, str(n), "DAY LEFT" if n == 1 else "DAYS LEFT", red_p)
            self._fly(p, (f - t0) / (TEAR_DUR if t0 != DROP else 10), n, t0 == DROP)
        # reset page falls onto the calendar
        if RESET <= f < RESET_LAND + 6:
            self._show_page(self.reset_page, True)
            h = self.reset_page["hinge"]
            u = clamp((f - RESET) / (RESET_LAND - RESET))
            drop = (1 - u * u) * 0.9
            bounce = 0.03 * math.sin(clamp((f - RESET_LAND) / 6) * math.pi) if f >= RESET_LAND else 0
            h.location = (0, -0.03, self.cal["hinge_z"] + drop + bounce)
            h.rotation_euler = (math.radians(-25) * (1 - u), 0, math.radians(8) * (1 - u))
        else:
            self._show_page(self.reset_page, False)

    def _fly(self, p, u, n, blast):
        h = p["hinge"]
        top = Vector((0, -0.010, self.cal["hinge_z"]))
        if blast:   # DROP: blasted up and away
            e = ease_out(u, 1.6)
            h.location = top + Vector((-0.9 * e, -0.6 * e, 1.6 * e))
            h.rotation_euler = (-math.radians(80) - 6 * e, 3 * e, 4 * e)
            h.scale = (1, 1, 1)
            return
        if u < 0.25:
            k = smooth(u / 0.25)
            h.location = top
            h.rotation_euler = (-math.radians(80) * k, 0, 0)
            h.scale = (1, 1, 1)
            return
        v = (u - 0.25) / 0.75
        cloud_local = (CLOUD - CAL) + Vector((0.05 * math.sin(n), 0, 0.05 * math.cos(n)))
        p1 = top + Vector((-0.30, -0.35, 0.16))
        e = smooth(v)
        a = top.lerp(p1, e)
        b = p1.lerp(cloud_local, e)
        h.location = a.lerp(b, e)
        h.rotation_euler = (-math.radians(80) - 4.0 * v, 2.5 * v * (1 if n % 2 else -1), 3.0 * v)
        s = lerp(1.0, 0.25, e)
        h.scale = (s, s, s)

    def _progress(self, f):
        v = progress(f)
        b = self.board
        b["fill_pivot"].scale.x = max(0.001, v / 100)
        aplus = f >= 300
        for k in ("track", "fill_pivot", "pct"):
            b[k].hide_render = aplus
        b["fill"].hide_render = aplus
        self._text(b["pct"], f"{int(round(v))}%")
        self.aplus.hide_render = not aplus
        if aplus:
            k = clamp((f - 300) / 8)
            s = 1.0 + 0.25 * math.sin(k * math.pi) if k < 1 else 1.0
            s *= ease_out(clamp((f - 300) / 5))
            self.aplus.scale = (s, s, s)

    def _cloud_scale(self, f):
        arrived = sum(1 for t, n in TEARS if t + TEAR_DUR <= f and t < 200)
        s = 0.0 if arrived == 0 else 0.30 + 0.70 * arrived / 27
        s += 0.15 * ramp(f, 160, 235)
        return s

    def _cloud(self, f):
        balls = self.cloud["balls"]
        root = self.cloud["root"]
        if f >= DROP + 7 and f < 300:
            for b in balls:
                b.hide_render = True
            return
        for b, home, hs in zip(balls, self.cloud_home, self.cloud_scale):
            b.hide_render = False
            b.location = home
            b.scale = hs
        if f < DROP:
            s = self._cloud_scale(f)
            pop = ease_out(clamp((f - (TEARS[0][0] + TEAR_DUR)) / 4)) if s > 0 else 0
            s *= pop
            root.location = CLOUD + Vector((0, 0, 0.02 * math.sin(f * 0.12)))
            shake = 0.012 * ramp(f, 170, 240) * math.sin(f * 1.7)
            root.location.x += shake
            root.scale = (s, s, s)
            dark = ramp(f, 80, 220)
            col = lerp(0.42, 0.17, dark)
        elif f < DROP + 7:      # burst: puffs blown outwards, then gone
            k = (f - DROP) / 6
            s = self._cloud_scale(DROP - 1) * (1 + 0.9 * k)
            root.scale = (s, s, s)
            for b, home, hs in zip(balls, self.cloud_home, self.cloud_scale):
                b.location = home * (1 + 2.5 * k)
                b.scale = hs * (1 - 0.8 * k)
            col = lerp(0.17, 0.6, k)
        else:                   # small drizzle cloud after the storm
            s = 0.5 * ease_out(clamp((f - 300) / 10))
            root.scale = (s, s, s)
            root.location = CLOUD + Vector((0.05, 0, 0.05 + 0.02 * math.sin(f * 0.1)))
            col = 0.30
        q = round(col, 2)
        if self._last.get("cloud_col") != q:
            em = next(n for n in self.cloud_mat.node_tree.nodes if n.type == "EMISSION")
            em.inputs["Color"].default_value = (q, q, q * 1.04, 1)
            df = next(n for n in self.cloud_mat.node_tree.nodes if n.type == "BSDF_DIFFUSE")
            df.inputs["Color"].default_value = (q, q, q * 1.04, 1)
            self._last["cloud_col"] = q

    def _storm(self, f):
        drops = self.rain["drops"]
        if f < 156:
            n = 0
        elif f < DROP:
            n = int(len(drops) * ramp(f, 156, 172))
        elif f < 300:
            n = 0
        else:
            n = int(14 * ramp(f, 304, 316))
        for i, d in enumerate(drops):
            d.hide_render = i >= n
        flashes = {210: (0, 1.0), 211: (0, 0.5), 213: (0, 0.8), 214: (0, 0.2), 232: (1, 0.9), 233: (1, 0.4)}
        for i, b in enumerate(self.bolts):
            on = flashes.get(f, (None, 0))
            vis = on[0] == i
            for o in b["bolts"]:
                o.hide_render = not vis
            b["flash"].data.energy = 900 * on[1] if vis else 0

    def _frantic(self, f):
        for j, st in enumerate(self.stacks):
            n = 0 if f < 208 else int(len(st["sheets"]) * clamp((f - 208 - 6 * j) / 30))
            for i, s in enumerate(st["sheets"]):
                s.hide_render = i >= n
        for k, c in enumerate(self.cups):
            t0 = 206 + k * 5
            u = clamp((f - t0) / 5)
            s = 0 if f < t0 else (1 + 0.25 * math.sin(u * math.pi)) * ease_out(u)
            for o in (c["body"], c["sleeve"]):
                o.hide_render = s < 0.02
            c["root"].scale = (max(s, 0.02),) * 3

    def _burst(self, f):
        if DROP <= f < DROP + 14:
            k = (f - DROP) / 13
            s = 0.15 + 2.6 * ease_out(k, 2.5)
            self.ring.hide_render = False
            self.ring.scale = (s, s, s)
            em = next(n for n in self.ring_mat.node_tree.nodes if n.type == "EMISSION")
            em.inputs["Strength"].default_value = 4.0 * (1 - k) ** 1.5
            self.burst.data.energy = 1200 * (1 - k) ** 3
        else:
            self.ring.hide_render = True
            self.burst.data.energy = 0

    def _paper(self, f):
        for sd in self.sheets:
            ob = sd["obj"]
            f0 = DROP + 1 + sd["delay"]
            hidden = f < f0
            ob.hide_render = hidden
            if sd["txt"] is not None:
                sd["txt"].hide_render = hidden
            if hidden:
                continue
            u = clamp((f - f0) / (sd["f_land"] - f0))
            # spiral out of the burst, drift down slowly, settle flat
            th = sd["th0"] + sd["turns"] * 2 * math.pi * ease_out(u, 1.6)
            r = sd["r"] * math.sin(math.pi * min(1.0, u * 1.15)) * (1 - u) ** 0.3
            c = (CLOUD + Vector((0.28, 0, 0))).lerp(sd["land"], ease_out(u, 1.3))
            z = lerp(sd["z0"], sd["land"].z, u ** 1.15) + 0.06 * math.sin(7 * u) * (1 - u)
            loc = Vector((c.x + r * math.cos(th), c.y + 0.6 * r * math.sin(th), z))
            if u >= 1:
                loc = sd["land"]
            ob.location = loc
            w = smooth((u - 0.72) / 0.28)
            tx = sd["rx"] * (1 - u) * math.sin(3 * u)
            ty = sd["ry"] * (1 - u) * math.cos(2 * u)
            ob.rotation_euler = (lerp(math.radians(90) + tx, 0, w), lerp(ty, 0, w), lerp(th, sd["rz_land"], w))

    def _phones(self, f):
        held = f < 156 or f >= 370
        for o in (self.phone["body"], self.phone["screen"]):
            o.hide_render = not held
        self.phone["glow"].data.energy = 5.0 if held else 0.0
        for o in (self.phone_desk["body"], self.phone_desk["screen"]):
            o.hide_render = held
        self.phone_desk["glow"].data.energy = 0.0 if held else 0.6

    def _lights(self, f):
        storm = ramp(f, 156, 180) * (1 - ramp(f, 296, 320) * 0.6)
        self.key_p.data.energy = 420 * (1 - 0.45 * storm)
        self.key_p.data.color = (lerp(1, 0.82, storm), lerp(0.97, 0.9, storm), lerp(0.92, 1.0, storm))
        self.warm.data.energy = 55 * ramp(f, 165, 195)
        self.aplus_glow.data.energy = 4 * ramp(f, 300, 306) * (1 + 0.15 * math.sin(f * 0.3))
        self.laptop["glow"].data.energy = 18

    def _camera(self, f):
        lens = 50.0
        if f >= DROP:
            lens = 50 + 6.0 * ease_out(clamp((f - DROP) / 3)) - 4.0 * smooth((f - DROP - 3) / 40)
            lens -= 2.0 * smooth((f - 330) / 60)
        self.cam.data.lens = lens
        amp = 0.0
        for f0, a, dcy in ((210, 0.025, 5.0), (232, 0.012, 4.0), (DROP, 0.05, 7.0)):
            if f >= f0:
                amp += a * math.exp(-(f - f0) / dcy)
        rnd = random.Random(f)
        off = Vector((rnd.uniform(-1, 1) * amp, 0, rnd.uniform(-1, 1) * amp))
        self.cam.location = CAM_LOC + off
        self.cam.rotation_euler = Euler((self.cam_rot.x + off.z * 0.15, self.cam_rot.y, self.cam_rot.z + off.x * 0.1))


# ----------------------------------------------------------------------------- post: text overlay, bloom, impact

TOP = [(1, DROP - 1, ["YOU DIDN'T SAVE TIME."]),
       (DROP, N, ["YOU BORROWED IT.", "WITH INTEREST."])]


def overlay_ops(f):
    """2D draw ops for frame f: (text, x, y, size, bold, color, alpha, spacing)."""
    ops = [("PROCRASTINATOR", 0.267, 0.300, 38, False, (240, 240, 240), 1.0, 5),
           ("PLANNER", 0.733, 0.300, 38, False, (240, 240, 240), 1.0, 5),
           ("@EYEOFEGO", 0.5, 0.835, 24, False, (110, 110, 110), 1.0, 6)]
    for f0, f1, lines in TOP:
        if f0 <= f <= f1:
            for i, line in enumerate(lines):
                appear = f0 if i == 0 else f0 + 21
                if f < appear:
                    continue
                a = clamp((f - appear + 1) / (6 if f0 == 1 else 2))
                ops.append((line, 0.5, 0.095 + 0.042 * i, 54, True, (255, 255, 255), a, 3))
    return ops


IMPACT = {DROP: "invert", DROP + 1: "invert", DROP + 2: "flash"}


# ----------------------------------------------------------------------------- sound

def audio_cues():
    """(frame, sfx name, gain, until_frame or None)."""
    c = [(f, "keys", 0.15, None) for f in (1, 37, 73, 109, 145)]
    c += [(t, "paper", 0.18, None) for t, n in TEARS if t != DROP]
    c += [(f, "whoosh", 0.22, None) for f in (62, 98, 126, 152)]
    c += [(163, "clank", 0.22, None), (165, "chime", 0.40, None)]
    c += [(156, "rain", 0.42, DROP), (304, "rain", 0.14, N), (304 + 150, "rain", 0.14, N)]
    c += [(210, "thunder", 0.90, None), (232, "thunder", 0.50, None)]
    c += [(204, "keys", 0.22, None), (222, "keys", 0.22, None)]
    c += [(f, "paper", 0.12, None) for f in range(208, 240, 6)]
    c += [(206 + 5 * k, "tick", 0.22, None) for k in range(7)]
    c += [(DROP, "boom", 0.90, None), (DROP, "hit", 0.60, None), (DROP, "whoosh", 0.50, None)]
    rnd = random.Random(3)
    c += [(rnd.randint(DROP + 4, 300), "paper", rnd.uniform(0.08, 0.16), None) for _ in range(14)]
    c += [(300, "chime", 0.55, None), (RESET_LAND, "stamp", 0.50, None), (372, "tick", 0.30, None), (377, "tick", 0.24, None)]
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
        if until is not None:
            n = max(0, int((until - f) / FPS * sr))
            x = x[:n].copy()
            fo = min(len(x), int(0.15 * sr))
            if fo:
                x[-fo:] *= np.linspace(1, 0, fo)[:, None]
        x = x[: max(0, len(out) - i)]
        out[i:i + len(x)] += x
    if music:
        m, _ = bed.make_bed(total, (DROP - 1) / FPS, bpm=100, seed=4)
        m = m[: len(out)]
        out[: len(m)] += m * 0.75
    # loudness: lift the quiet intro, soft-limit the drop (TikTok plays it on a phone speaker)
    peak = float(np.max(np.abs(out))) or 1.0
    out = out / peak
    return (np.tanh(out * 1.8) / np.tanh(1.8) * 0.95).astype(np.float32)


COVER_FRAME = 330
