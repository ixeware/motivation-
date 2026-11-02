"""Mixamo FBX clips on the stick-figure rig.

  arm = mocap.character("plan")                     # armature from the base clip + stick figure parts
  mocap.sequence(arm, [("typing", 1, 120), ("victory", 120, 200, {"blend": 8})])

Clips are downloaded once with `python -m engine mocap fetch` (your Mixamo token) into the
gitignored assets/mocap/cache/. Every clip is the same X Bot skeleton ("mixamorig:*" bones), so one
character can play any of them; NLA strips crossfade between them.
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

from . import kit

CACHE = kit.ROOT / "assets" / "mocap" / "cache"

from .mixamo import LIBRARY as CLIPS  # noqa: E402  short name -> (fetch spec, cached file stem)


def path(clip: str) -> Path:
    p = CACHE / f"{CLIPS[clip][1]}.fbx"
    if not p.exists():
        raise FileNotFoundError(f"{p.name} is not downloaded: python -m engine mocap fetch \"{CLIPS[clip][0]}\"")
    return p


def _import(clip):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path(clip)))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    for o in new:
        if o is not arm:
            bpy.data.objects.remove(o, do_unlink=True)
    return arm


_actions: dict[str, bpy.types.Action] = {}


def action(clip: str) -> bpy.types.Action:
    """The clip's action (imported once per scene)."""
    if clip in _actions and _actions[clip].name in bpy.data.actions:
        return _actions[clip]
    arm = _import(clip)
    act = arm.animation_data.action
    act.name = f"clip_{clip}"
    act.use_fake_user = True
    data = arm.data
    bpy.data.objects.remove(arm, do_unlink=True)
    bpy.data.armatures.remove(data)
    _actions[clip] = act
    return act


def character(name: str, base: str = "idle", **figure):
    """Armature (from the base clip's FBX) + white toon stick figure parented to its bones.

    Returns the armature; its root empty is `arm.parent` (move that to place the character).
    """
    arm = _import(base)
    arm.name = name
    act = arm.animation_data.action
    act.name = f"clip_{base}"
    act.use_fake_user = True
    _actions[base] = act
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    kit.stick_figure(arm, name=name, **figure)
    root = kit.empty(f"{name}_root", (0, 0, 0), 0.2)
    arm.parent = root
    return arm


def sequence(arm, strips):
    """Play clips on the NLA one after another, crossfading at each cut.

    strips: [(clip, start_frame, end_frame[, opts]), ...]; opts:
      offset - clip frame to start from (default 0)
      speed  - playback speed (2.0 = twice as fast; frantic typing)
      blend  - crossfade frames into this strip (default 8)
      hold   - True: freeze on clip frame `offset` (a still pose)
    Each strip sits on its own track above the previous one and lasts until the next strip has fully
    blended in. Clips shorter than their slot loop.
    """
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    out = []
    for i, item in enumerate(strips):
        clip, f0, f1, *rest = item
        opts = rest[0] if rest else {}
        nxt = strips[i + 1] if i + 1 < len(strips) else None
        nxt_blend = (nxt[3].get("blend", 8) if len(nxt) > 3 else 8) if nxt else 0
        end = f1 + nxt_blend
        act = action(clip)
        a0, a1 = act.frame_range
        start_a = a0 + opts.get("offset", 0.0)
        speed = float(opts.get("speed", 1.0))
        L = float(end - f0)
        tr = ad.nla_tracks.new()
        tr.name = f"{i:02d}_{clip}"
        st = tr.strips.new(f"{clip}_{i}", int(f0), act)
        if getattr(act, "slots", None) and hasattr(st, "action_slot"):
            st.action_slot = act.slots[0]
        st.use_sync_length = False
        if opts.get("hold"):
            st.action_frame_start = start_a
            st.action_frame_end = start_a + 1
            st.scale = max(1.0, L)
        else:
            avail = a1 - start_a
            st.action_frame_start = start_a
            if avail * (1 / speed) >= L:
                st.action_frame_end = start_a + L * speed
                st.scale = 1.0 / speed
            else:
                st.action_frame_end = a1
                st.scale = 1.0 / speed
                st.repeat = L / (avail / speed)
        st.blend_type = "REPLACE"
        st.use_auto_blend = False
        st.blend_in = float(opts.get("blend", 8)) if i else 0.0
        st.blend_out = 0.0
        st.extrapolation = "HOLD" if i == 0 else ("HOLD_FORWARD" if nxt is None else "NOTHING")
        out.append(st)
    return out


def world_of(arm, bone, frame):
    bpy.context.scene.frame_set(frame)
    return arm.matrix_world @ arm.pose.bones[kit.MIX + bone].head


def attach(obj, arm, bone, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Parent a prop to a bone of the rest pose at a world offset from the bone head (e.g. phone in the hand)."""
    bpy.context.view_layer.update()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = kit.MIX + bone
    bpy.context.view_layer.update()
    head = arm.matrix_world @ arm.pose.bones[kit.MIX + bone].head
    obj.matrix_world = Matrix.Translation(head + Vector(loc)) @ Euler(rot).to_matrix().to_4x4()
    return obj


def recenter(clip: str, frame: float, target_xy=(0.0, 0.0), bone: str = "Hips"):
    """Shift a clip's root (Hips) location keys so that at `frame` the hips stand at target_xy (z kept).

    Removes a clip's walk-in / root drift (e.g. a hard landing that starts a metre away). Positions are
    for a character placed at the origin. The action is shared by every character: call once per clip.
    """
    act = action(clip)
    arm = _import(clip)
    ad = arm.animation_data
    ad.action = act
    if getattr(act, "slots", None):
        ad.action_slot = act.slots[0]
    bpy.context.scene.frame_set(int(frame))
    pb = arm.pose.bones[kit.MIX + bone]
    head = arm.matrix_world @ pb.head
    delta_w = Vector((target_xy[0] - head.x, target_xy[1] - head.y, 0.0))
    d = (arm.matrix_world.to_3x3() @ pb.bone.matrix_local.to_3x3()).inverted() @ delta_w
    path = f'pose.bones["{kit.MIX + bone}"].location'
    for fc in kit._fcurves(act):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                kp.co.y += d[fc.array_index]
                kp.handle_left.y += d[fc.array_index]
                kp.handle_right.y += d[fc.array_index]
            fc.update()
    own = [a for a in bpy.data.actions if a is not act and a.users == 0]
    data = arm.data
    bpy.data.objects.remove(arm, do_unlink=True)
    bpy.data.armatures.remove(data)
    for a in own:            # the duplicate action that came with this import
        bpy.data.actions.remove(a)
    return d


def ik_arm(arm, side: str, target, pole, influence=0.0, calibrate_frame=None):
    """IK on top of a clip (chain: forearm + upper arm), influence animated by the caller."""
    pb = arm.pose.bones[kit.MIX + f"{side}ForeArm"]
    c = pb.constraints.new("IK")
    c.name = "IK"
    c.target, c.pole_target, c.chain_count, c.use_tail = target, pole, 2, True
    if calibrate_frame is not None:
        sc = bpy.context.scene

        def dist(a):
            c.pole_angle = math.radians(a)
            c.influence = 1.0
            arm.update_tag()
            sc.frame_set(calibrate_frame)
            j = arm.matrix_world @ arm.pose.bones[kit.MIX + f"{side}ForeArm"].head
            return (j - pole.matrix_world.translation).length

        best = min(range(-180, 180, 30), key=dist)
        best = min((best + k for k in range(-15, 16, 3)), key=dist)
        c.pole_angle = math.radians(best)
    c.influence = influence
    return c


def calibrate_pole(arm, side: str, frame: int):
    """Choose the IK pole angle (bone roll dependent) so the elbow really points at the pole at `frame`."""
    c = arm.pose.bones[kit.MIX + f"{side}ForeArm"].constraints["IK"]
    keep = c.influence
    sc = bpy.context.scene
    pole = c.pole_target

    def dist(a):
        c.pole_angle = math.radians(a)
        c.influence = 1.0
        arm.update_tag()
        sc.frame_set(frame)
        j = arm.matrix_world @ arm.pose.bones[kit.MIX + f"{side}ForeArm"].head
        return (j - pole.matrix_world.translation).length

    best = min(range(-180, 180, 30), key=dist)
    best = min((best + k for k in range(-15, 16, 3)), key=dist)
    c.pole_angle = math.radians(best)
    c.influence = keep
    return best
