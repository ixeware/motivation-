"""Blender toolkit for the 3D look (white toon stick figures on a Mixamo rig).

Runs with Blender as a Python module (`pip install bpy`), headless, Cycles on CPU.

Pieces:
  scene / render setup        reset(), setup_render()
  materials                   toon(), outline_mat(), emission(), dark(), add_outline()
  meshes                      capsule(), box(), plane()
  Mixamo rig -> stick figure  import_rig(), stick_figure()
  procedural animation        Rig: IK targets for hands/feet + poles, spine/head bends, keyframe helpers
  text                        text()  (Silkscreen pixel font, like the reference account)
  lights / camera             spot(), camera()
  rendering                   render_frames()
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
FONT_PIXEL = str(ROOT / "assets" / "fonts" / "Silkscreen-Regular.ttf")
FONT_PIXEL_BOLD = str(ROOT / "assets" / "fonts" / "Silkscreen-Bold.ttf")
XBOT = str(ROOT / "assets" / "mocap" / "cache" / "Xbot.glb")
XBOT_URL = "https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/models/gltf/Xbot.glb"

MIX = "mixamorig:"


# ----------------------------------------------------------------------------- scene

def reset(fps: int = 60, w: int = 1080, h: int = 1920):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0
    sc.world = world
    return sc


def setup_render(sc, *, samples: int = 24, engine: str = "CYCLES", exposure: float = 0.0, bloom: bool = True):
    sc.render.engine = engine
    if engine == "CYCLES":
        cy = sc.cycles
        cy.device = "CPU"
        cy.samples = samples
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.04
        cy.use_denoising = True
        cy.max_bounces = 4
        cy.diffuse_bounces = 1
        cy.glossy_bounces = 2
        cy.transmission_bounces = 2
        cy.transparent_max_bounces = 12
        cy.caustics_reflective = False
        cy.caustics_refractive = False
        try:
            cy.denoiser = "OPENIMAGEDENOISE"
        except Exception:  # noqa: BLE001
            pass
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = exposure
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    if bloom:
        _compositor_glare(sc)


def _compositor_glare(sc):
    """Soft bloom on bright things (screens, lightning, labels) via the compositor."""
    try:
        sc.use_nodes = True
        tree = sc.node_tree
        if tree is None:
            return
        nodes, links = tree.nodes, tree.links
        nodes.clear()
        rl = nodes.new("CompositorNodeRLayers")
        glare = nodes.new("CompositorNodeGlare")
        glare.glare_type = "FOG_GLOW" if hasattr(glare, "glare_type") else glare.glare_type
        if hasattr(glare, "quality"):
            glare.quality = "MEDIUM"
        if hasattr(glare, "threshold"):
            glare.threshold = 0.9
        if hasattr(glare, "size"):
            glare.size = 7
        comp = nodes.new("CompositorNodeComposite")
        links.new(rl.outputs["Image"], glare.inputs["Image"])
        links.new(glare.outputs["Image"], comp.inputs["Image"])
    except Exception as e:  # noqa: BLE001 - bloom is optional; the render still works without it
        print("[kit] compositor glare skipped:", e)


# ----------------------------------------------------------------------------- materials

def _mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def toon(name="toon_white", color=(0.95, 0.95, 0.94, 1), flat: float = 0.92):
    """Flat white like the reference: mostly emission (constant) + a bit of diffuse (light from the spots)."""
    m, nt, out = _mat(name)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = flat
    df = nt.nodes.new("ShaderNodeBsdfDiffuse")
    df.inputs["Color"].default_value = color
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(em.outputs[0], add.inputs[0])
    nt.links.new(df.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m


def outline_mat(name="outline", color=(0.03, 0.03, 0.035, 1)):
    """Inverted-hull outline for Cycles: back side of the shell = dark, front side = transparent."""
    m, nt, out = _mat(name)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = 1.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def emission(name, color, strength=1.0):
    m, nt, out = _mat(name)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color[:3], 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def dark(name, color=(0.12, 0.12, 0.13, 1), rough=0.7, emit: float = 0.0):
    """Matte prop material (desks, chairs): principled + a little self-light so it reads on black."""
    m, nt, out = _mat(name)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = color
    p.inputs["Roughness"].default_value = rough
    if emit > 0:
        p.inputs["Emission Color"].default_value = color
        p.inputs["Emission Strength"].default_value = emit
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def glossy_floor(name="floor", color=(0.012, 0.012, 0.014, 1), rough=0.22):
    m, nt, out = _mat(name)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = color
    p.inputs["Roughness"].default_value = rough
    p.inputs["Specular IOR Level"].default_value = 0.6
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def set_mat(obj, *mats):
    obj.data.materials.clear()
    for m in mats:
        obj.data.materials.append(m)


def add_outline(obj, thickness=0.018, mat=None):
    """Solidify inverted hull -> constant-ish dark outline around the object."""
    if mat is None:
        mat = bpy.data.materials.get("outline") or outline_mat()
    if mat.name not in [m.name for m in obj.data.materials if m]:
        obj.data.materials.append(mat)
    mod = obj.modifiers.new("outline", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.use_rim = False
    mod.material_offset = len(obj.data.materials) - 1
    return mod


# ----------------------------------------------------------------------------- meshes

def _link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def capsule(name, length, r0, r1=None, seg=16, rings=6):
    """Capsule along +Y from (0,0,0) to (0,length,0), radius r0 at the start, r1 at the end."""
    r1 = r0 if r1 is None else r1
    bm = bmesh.new()
    verts_rings = []
    # bottom hemisphere (around y=0), cylinder, top hemisphere (around y=length)
    for k in range(rings, -1, -1):
        a = (math.pi / 2) * k / rings
        verts_rings.append((-math.sin(a) * r0, math.cos(a) * r0))
    for k in range(0, rings + 1):
        a = (math.pi / 2) * k / rings
        verts_rings.append((length + math.sin(a) * r1, math.cos(a) * r1))
    rows = []
    for (y, rad) in verts_rings:
        row = []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            row.append(bm.verts.new((math.cos(t) * rad, y, math.sin(t) * rad)))
        rows.append(row)
    for a_, b_ in zip(rows[:-1], rows[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            try:
                bm.faces.new((a_[i], a_[j], b_[j], b_[i]))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return _link(bpy.data.objects.new(name, me))


def sphere(name, radius, seg=24, rings=14):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=radius)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return _link(bpy.data.objects.new(name, me))


def box(name, size, loc=(0, 0, 0), bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = _link(bpy.data.objects.new(name, me))
    ob.location = loc
    if bevel > 0:
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = 2
    return ob


def plane(name, w, h, loc=(0, 0, 0), rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co.x *= w
        v.co.y *= h
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = _link(bpy.data.objects.new(name, me))
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def empty(name, loc=(0, 0, 0), size=0.05):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    e.location = loc
    return _link(e)


# ----------------------------------------------------------------------------- Mixamo rig -> stick figure

def ensure_xbot():
    p = Path(XBOT)
    if not p.exists():
        import urllib.request
        p.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(XBOT_URL, p)
    return str(p)


def import_rig(name: str, prebend: float = 3.0) -> bpy.types.Object:
    """Import the Mixamo X Bot rig (glTF from the three.js examples), drop its mesh, return the armature.

    TEMPERANCE bone tips point at the children (the default heuristic gives 10 m long bones, IK breaks).
    The T-pose arms are perfectly straight, a singular start for IK with a pole target (the elbow never
    bends), so elbows are pre-bent backwards and knees forwards by `prebend` cm in the rest pose.
    """
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ensure_xbot(), bone_heuristic="TEMPERANCE")
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    arm.name = name
    for o in new:
        if o.type == "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    if arm.animation_data:
        arm.animation_data.action = None
    if prebend:
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm.data.edit_bones
        for side in ("Left", "Right"):
            for upper, lower, d in ((f"{side}Arm", f"{side}ForeArm", Vector((0, prebend, 0))),
                                    (f"{side}UpLeg", f"{side}Leg", Vector((0, -prebend, 0)))):
                u, l = eb[MIX + upper], eb[MIX + lower]
                joint = l.head.copy() + d
                u.tail = joint
                l.head = joint
        bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    return arm


def bone_head(arm, bone):  # rest position in world space
    return arm.matrix_world @ arm.data.bones[MIX + bone].head_local


SEGMENTS = [  # (start bone, end bone, radius scale)
    ("LeftArm", "LeftForeArm", 1.0), ("LeftForeArm", "LeftHand", 0.95),
    ("RightArm", "RightForeArm", 1.0), ("RightForeArm", "RightHand", 0.95),
    ("LeftUpLeg", "LeftLeg", 1.08), ("LeftLeg", "LeftFoot", 1.0),
    ("RightUpLeg", "RightLeg", 1.08), ("RightLeg", "RightFoot", 1.0),
]


def stick_figure(arm, *, limb=0.052, torso=0.115, head=0.155, mat=None, outline=0.026, name="fig"):
    """Capsule limbs + capsule torso + big round head, each parented to its Mixamo bone."""
    mat = mat or bpy.data.materials.get("toon_white") or toon()
    parts = []
    bpy.context.view_layer.update()

    def attach(obj, bone_name, world_matrix):
        obj.parent = arm
        obj.parent_type = "BONE"
        obj.parent_bone = MIX + bone_name
        bpy.context.view_layer.update()
        obj.matrix_world = world_matrix
        set_mat(obj, mat)
        add_outline(obj, outline)
        parts.append(obj)

    def along(a, b):
        """World matrix whose +Y goes from a to b."""
        d = (b - a)
        L = d.length
        y = d.normalized()
        ref = Vector((0, 0, 1)) if abs(y.z) < 0.95 else Vector((1, 0, 0))
        x = y.cross(ref).normalized()
        z = x.cross(y).normalized()
        m = Matrix((x, y, z)).transposed().to_4x4()
        m.translation = a
        return m, L

    # limbs: capsule from joint to joint, a bit longer to cover the joints
    for a_name, b_name, k in SEGMENTS:
        a, b = bone_head(arm, a_name), bone_head(arm, b_name)
        if "Hand" in b_name:   # extend forearm to the knuckles
            b = b + (b - a).normalized() * 0.07
        if "Foot" in b_name:   # down to the sole
            b = b + Vector((0, 0, -0.06))
        m, L = along(a, b)
        cap = capsule(f"{name}_{a_name}", L, limb * k)
        attach(cap, a_name, m)
    # feet: short capsule forward
    for side in ("Left", "Right"):
        a = bone_head(arm, f"{side}Foot") + Vector((0, 0, -0.06))
        b = bone_head(arm, f"{side}ToeBase") + Vector((0, -0.02, -0.02))
        m, L = along(a, b)
        cap = capsule(f"{name}_{side}Foot", max(L, 0.08), limb * 0.9)
        attach(cap, f"{side}Foot", m)
    # torso: hips -> neck
    a = bone_head(arm, "Hips") + Vector((0, 0, -0.06))
    b = bone_head(arm, "Neck") + Vector((0, 0, -0.03))
    m, L = along(a, b)
    t = capsule(f"{name}_torso", L, torso * 0.92, torso)
    attach(t, "Spine", m)
    # head: big sphere above the neck
    hpos = (bone_head(arm, "Head") + bone_head(arm, "HeadTop_End")) / 2 + Vector((0, 0, 0.02))
    hd = sphere(f"{name}_head", head)
    hm = Matrix.Translation(hpos)
    attach(hd, "Head", hm)
    return parts


# ----------------------------------------------------------------------------- procedural animation (IK)

class Rig:
    """IK-driven poses on a Mixamo armature.

    Everything hangs under one root empty (the character's place in the set), so target positions are
    given in character space, in metres: +X = the character's left (screen right when it faces the
    camera), -Y = forward (towards the camera), +Z = up, origin on the floor under the hips.
    Targets: LeftHand/RightHand, LeftFoot/RightFoot (IK ends), LeftElbow/RightElbow, LeftKnee/RightKnee (poles).
    """

    def __init__(self, arm, name=None):
        self.arm = arm
        self.name = name or arm.name
        self.t = {}
        bpy.context.view_layer.update()
        self.root = empty(f"{self.name}_root", (0, 0, 0), 0.2)
        arm.parent = self.root
        self.hips = Vector((0, 0, 0))       # armature offset inside the root (lowered when seated)
        for side in ("Left", "Right"):
            sgn = 1 if side == "Left" else -1
            hand = empty(f"{self.name}_{side}Hand_t", bone_head(arm, f"{side}Hand"))
            foot = empty(f"{self.name}_{side}Foot_t", self._ankle(side))
            elbow = empty(f"{self.name}_{side}Elbow_p", bone_head(arm, f"{side}Arm") + Vector((sgn * 0.25, 0.25, -0.75)))
            knee = empty(f"{self.name}_{side}Knee_p", bone_head(arm, f"{side}UpLeg") + Vector((sgn * 0.06, -1.0, -0.2)))
            for e in (hand, foot, elbow, knee):
                e.parent = self.root
            self._ik(f"{side}ForeArm", hand, elbow)
            self._ik(f"{side}Leg", foot, knee)
            self.t.update({f"{side}Hand": hand, f"{side}Foot": foot, f"{side}Elbow": elbow, f"{side}Knee": knee})
        self._calibrate()

    def _ankle(self, side):
        pb = self.arm.pose.bones[MIX + f"{side}Leg"]
        return self.arm.matrix_world @ pb.tail

    def _ik(self, bone, target, pole):
        pb = self.arm.pose.bones[MIX + bone]
        c = pb.constraints.new("IK")
        c.name = "IK"
        c.target = target
        c.pole_target = pole
        c.pole_angle = math.radians(-90)
        c.chain_count = 2
        c.use_tail = True
        return c

    def _calibrate(self):
        """Pick each chain's pole angle so the elbow/knee really points at its pole (depends on bone roll)."""
        tests = {"LeftForeArm": ("LeftHand", Vector((0.05, -0.38, -0.25)), "LeftArm"),
                 "RightForeArm": ("RightHand", Vector((-0.05, -0.38, -0.25)), "RightArm"),
                 "LeftLeg": ("LeftFoot", Vector((0, -0.35, -0.75)), "LeftUpLeg"),
                 "RightLeg": ("RightFoot", Vector((0, -0.35, -0.75)), "RightUpLeg")}
        for bone, (tname, off, base) in tests.items():
            tgt = self.t[tname]
            keep = tgt.location.copy()
            tgt.location = bone_head(self.arm, base) + off
            c = self.arm.pose.bones[MIX + bone].constraints["IK"]
            pole = c.pole_target

            def dist(a):
                c.pole_angle = math.radians(a)
                self.arm.update_tag()
                bpy.context.view_layer.update()
                j = self.arm.matrix_world @ self.arm.pose.bones[MIX + bone].head
                return (j - pole.matrix_world.translation).length

            best = min(range(-180, 180, 15), key=dist)
            best = min((best + d for d in range(-12, 13)), key=dist)
            c.pole_angle = math.radians(best)
            tgt.location = keep
        self.arm.update_tag()
        bpy.context.view_layer.update()

    # --- placement -----------------------------------------------------------
    def place(self, loc, rot_z=0.0):
        self.root.location = loc
        self.root.rotation_euler = (0, 0, rot_z)

    def seat(self, drop=0.442):
        """Lower the hips by `drop` m (seat height ~0.46 m for the default) and keep the targets where they are."""
        self.arm.location = (0, 0, -drop)
        self.hips = Vector((0, 0, -drop))

    # --- keyframing helpers --------------------------------------------------
    def key_target(self, name, frame, loc, interp=None):
        e = self.t[name]
        e.location = loc
        e.keyframe_insert("location", frame=frame)
        if interp:
            _set_interp(e, frame, interp)

    def key_bone_rot(self, bone, frame, axis_deg: dict, interp=None):
        """Rotate a pose bone by Euler degrees in its local axes, e.g. {'x': 20}."""
        pb = self.arm.pose.bones[MIX + bone]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(axis_deg.get("x", 0)), math.radians(axis_deg.get("y", 0)),
                             math.radians(axis_deg.get("z", 0)))
        pb.keyframe_insert("rotation_euler", frame=frame)
        if interp:
            _set_interp(self.arm, frame, interp)

    def key_hips(self, frame, offset=(0, 0, 0)):
        """Armature offset inside the root (lean, slump, jump) relative to the seated height."""
        self.arm.location = self.hips + Vector(offset)
        self.arm.keyframe_insert("location", frame=frame)

    def key_root(self, frame, loc=None, rot_z=None):
        if loc is not None:
            self.root.location = loc
            self.root.keyframe_insert("location", frame=frame)
        if rot_z is not None:
            self.root.rotation_euler.z = rot_z
            self.root.keyframe_insert("rotation_euler", frame=frame)


def _set_interp(obj, frame, interp):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in _fcurves(ad.action):
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.01:
                kp.interpolation = interp


def linear_keys(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in _fcurves(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def _fcurves(action):
    """F-curves of an action (Blender 4.4+ layered actions or the legacy list)."""
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


# ----------------------------------------------------------------------------- text, lights, camera

_fonts = {}


def font(path=FONT_PIXEL):
    if path not in _fonts:
        _fonts[path] = bpy.data.fonts.load(path)
    return _fonts[path]


def text(name, body, size=0.2, loc=(0, 0, 0), rot=(math.radians(90), 0, 0), color=(1, 1, 1), strength=1.4,
         align="CENTER", spacing=1.25, bold=False, parent=None):
    cu = bpy.data.curves.new(name, type="FONT")
    cu.body = body
    cu.font = font(FONT_PIXEL_BOLD if bold else FONT_PIXEL)
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = spacing
    ob = _link(bpy.data.objects.new(name, cu))
    ob.location = loc
    ob.rotation_euler = rot
    if parent is not None:
        ob.parent = parent
    m = emission(f"txt_{name}", color, strength)
    cu.materials.append(m)
    return ob


def spot(name, loc, target_loc, energy=900.0, size_deg=48.0, blend=0.65, color=(1, 0.97, 0.92), radius=0.15):
    li = bpy.data.lights.new(name, "SPOT")
    li.energy = energy
    li.spot_size = math.radians(size_deg)
    li.spot_blend = blend
    li.color = color
    li.shadow_soft_size = radius
    ob = _link(bpy.data.objects.new(name, li))
    ob.location = loc
    d = Vector(target_loc) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def camera(name="cam", loc=(0, -10, 1.5), look_at=(0, 0, 1.2), lens=50.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_fit = "VERTICAL"
    cam.sensor_height = 36.0
    cam.clip_end = 300
    ob = _link(bpy.data.objects.new(name, cam))
    ob.location = loc
    d = Vector(look_at) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


# ----------------------------------------------------------------------------- rendering

def render_frames(sc, out_dir, frames, per_frame=None, verbose=True):
    """Render frame by frame (lets Python update texts/counters between frames)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    import time
    t_all = time.time()
    for i, f in enumerate(frames):
        sc.frame_set(f)
        if per_frame:
            per_frame(f)
        sc.render.filepath = str(out / f"f_{f:05d}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        if verbose and (i % 20 == 0 or i == len(frames) - 1):
            el = time.time() - t_all
            print(f"  frame {f} ({i + 1}/{len(frames)})  {time.time() - t0:.1f}s  elapsed {el / 60:.1f} min", flush=True)
    return out
