"""Set pieces for the 3D look: desk, chair, laptop, phone, tear-off calendar, window, progress board,
paper, coffee cups, storm cloud, rain, lightning.

All sizes in metres. Characters face -Y (the camera), so "front" of a desk is its -Y side.
Every builder returns a dict of the objects it made; the first key is the parent empty when there is one.
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from . import kit

GRAY_TOP = (0.42, 0.42, 0.43, 1)
GRAY_BODY = (0.20, 0.20, 0.21, 1)
GRAY_DARK = (0.09, 0.09, 0.10, 1)
PAPER = (0.95, 0.95, 0.93, 1)
RED = (0.86, 0.10, 0.08, 1)


def _mat(name, color, rough=0.65, emit=0.0):
    return bpy.data.materials.get(name) or kit.dark(name, color, rough, emit)


def _parent(objs, parent):
    for o in objs:
        o.parent = parent
    return objs


def desk(name, loc, w=1.10, d=0.60, h=0.75, top=0.05, panel_from=0.30):
    """Office desk seen from the front: light top slab, dark front + side panels (hollow, knees fit), short legs."""
    root = kit.empty(name, loc, 0.3)
    m_top = _mat("desk_top", GRAY_TOP, 0.55)
    m_body = _mat("desk_body", GRAY_BODY, 0.75)
    t = 0.03
    parts = {"root": root}
    parts["top"] = kit.box(f"{name}_top", (w, d, top), (0, 0, h - top / 2), bevel=0.006)
    ph = h - top - panel_from
    parts["front"] = kit.box(f"{name}_front", (w - 0.02, t, ph), (0, -d / 2 + t / 2 + 0.01, panel_from + ph / 2))
    parts["side_l"] = kit.box(f"{name}_side_l", (t, d - 0.04, ph), (-w / 2 + t / 2 + 0.01, 0, panel_from + ph / 2))
    parts["side_r"] = kit.box(f"{name}_side_r", (t, d - 0.04, ph), (w / 2 - t / 2 - 0.01, 0, panel_from + ph / 2))
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        parts[f"leg{i}"] = kit.box(f"{name}_leg{i}", (0.045, 0.045, panel_from),
                                   (sx * (w / 2 - 0.04), sy * (d / 2 - 0.04), panel_from / 2))
    for k, o in parts.items():
        if k == "root":
            continue
        kit.set_mat(o, m_top if k == "top" else m_body)
        o.parent = root
    return parts


def chair(name, loc, seat_h=0.46, w=0.46, d=0.44, back_h=0.62):
    root = kit.empty(name, loc, 0.2)
    m = _mat("chair", GRAY_DARK, 0.7)
    parts = {"root": root,
             "seat": kit.box(f"{name}_seat", (w, d, 0.05), (0, 0, seat_h - 0.025), bevel=0.01),
             "back": kit.box(f"{name}_back", (w, 0.045, back_h), (0, d / 2 - 0.02, seat_h + back_h / 2), bevel=0.012)}
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        parts[f"leg{i}"] = kit.box(f"{name}_leg{i}", (0.035, 0.035, seat_h - 0.05),
                                   (sx * (w / 2 - 0.03), sy * (d / 2 - 0.03), (seat_h - 0.05) / 2))
    for k, o in parts.items():
        if k != "root":
            kit.set_mat(o, m)
            o.parent = root
    return parts


def laptop(name, loc, w=0.36, d=0.25, open_deg=105, screen_color=(0.75, 0.88, 1.0), glow=2.5):
    """Laptop on the desk, screen towards the character (+Y); the camera sees the lid's back."""
    root = kit.empty(name, loc, 0.1)
    m_body = _mat("laptop", (0.16, 0.16, 0.17, 1), 0.35)
    base = kit.box(f"{name}_base", (w, d, 0.018), (0, 0, 0.009), bevel=0.004)
    hinge = kit.empty(f"{name}_hinge", (0, -d / 2, 0.018), 0.05)
    lid = kit.box(f"{name}_lid", (w, 0.012, d * 0.95), (0, 0.006, d * 0.95 / 2), bevel=0.004)
    scr = kit.plane(f"{name}_screen", w * 0.9, d * 0.8, (0, 0.0135, d * 0.95 / 2), (math.radians(90), 0, math.radians(180)))
    kit.set_mat(base, m_body)
    kit.set_mat(lid, m_body)
    kit.set_mat(scr, kit.emission(f"{name}_scr", screen_color, glow))
    base.parent = hinge.parent = root
    lid.parent = scr.parent = hinge
    hinge.rotation_euler.x = math.radians(open_deg - 90)
    # soft light from the screen onto the character's face and chest
    li = bpy.data.lights.new(f"{name}_glow", "AREA")
    li.energy = 18
    li.size = 0.3
    li.color = screen_color
    lo = bpy.data.objects.new(f"{name}_glow", li)
    bpy.context.scene.collection.objects.link(lo)
    lo.parent = hinge
    lo.location = (0, 0.12, d * 0.5)
    lo.rotation_euler = (math.radians(90), 0, 0)    # area light emits along local -Z -> +Y (the character)
    return {"root": root, "base": base, "hinge": hinge, "lid": lid, "screen": scr, "glow": lo}


def phone(name, color=(0.80, 0.90, 1.0), glow=3.0, light=6.0, size=1.0):
    """Phone held in the hands: thin dark slab with a bright screen facing the character, plus its glow."""
    root = kit.empty(name, (0, 0, 0), 0.05)
    body = kit.box(f"{name}_body", (0.075 * size, 0.009, 0.15 * size), (0, 0, 0), bevel=0.003)
    scr = kit.plane(f"{name}_screen", 0.066 * size, 0.135 * size, (0, 0.0047, 0), (math.radians(-90), 0, 0))
    kit.set_mat(body, _mat("phone", (0.05, 0.05, 0.06, 1), 0.3))
    kit.set_mat(scr, kit.emission(f"{name}_scr", color, glow))
    li = bpy.data.lights.new(f"{name}_glow", "POINT")
    li.energy = light
    li.color = color
    li.shadow_soft_size = 0.05
    lo = bpy.data.objects.new(f"{name}_glow", li)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (0, 0.08, 0.02)
    for o in (body, scr, lo):
        o.parent = root
    return {"root": root, "body": body, "screen": scr, "glow": lo}


# ----------------------------------------------------------------------------- wall pieces

def calendar(name, loc, w=0.62, h=0.74):
    """Tear-off calendar: dark board, two binder rings, a page with a big number and a caption.

    Returns the parts plus `page(...)` to make extra pages (for tearing off) and `set(...)` to
    change the front page between frames.
    """
    root = kit.empty(name, loc, 0.2)
    board = kit.box(f"{name}_board", (w, 0.04, h), (0, 0.02, 0), bevel=0.01)
    kit.set_mat(board, _mat("cal_board", (0.13, 0.13, 0.14, 1), 0.6, 0.15))
    board.parent = root
    rings = []
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.028, minor_radius=0.008, location=(sx * w * 0.22, -0.005, h / 2 - 0.035),
                                         rotation=(math.radians(90), 0, 0))
        r = bpy.context.active_object
        r.name = f"{name}_ring{sx}"
        kit.set_mat(r, _mat("cal_ring", (0.85, 0.85, 0.85, 1), 0.3, 0.6))
        r.parent = root
        rings.append(r)
    pw, ph = w * 0.88, h * 0.80

    def page(pname, number="30", caption="DAYS LEFT", red=False, y=-0.004):
        """A page object (with its texts as children) hinged at its top edge."""
        hinge = kit.empty(f"{pname}_hinge", (0, y, h / 2 - 0.07), 0.05)
        hinge.parent = root
        bg = kit.plane(f"{pname}_bg", pw, ph, (0, 0, -ph / 2), (math.radians(90), 0, 0))
        col_bg = RED if red else PAPER
        col_tx = (1, 1, 1) if red else (0.05, 0.05, 0.05)
        kit.set_mat(bg, kit.emission(f"{pname}_bgm", col_bg[:3], 1.0))
        bg.parent = hinge
        num = kit.text(f"{pname}_num", number, size=0.30, loc=(0, -0.003, -ph * 0.40), color=col_tx, strength=1.0,
                       bold=True, spacing=1.05, parent=hinge)
        cap = kit.text(f"{pname}_cap", caption, size=0.082, loc=(0, -0.003, -ph * 0.79), color=col_tx, strength=1.0,
                       spacing=1.15, parent=hinge)
        return {"hinge": hinge, "bg": bg, "num": num, "cap": cap}

    front = page(f"{name}_p0")

    def set_page(p, number=None, caption=None, red=None):
        if number is not None:
            p["num"].data.body = number
            k = 1.0 if len(number) <= 2 else 0.74     # "DUE" must fit the page
            p["num"].scale = (k, k, k)
        if caption is not None:
            p["cap"].data.body = caption
        if red is not None:
            col_bg = RED if red else PAPER
            col_tx = (1, 1, 1) if red else (0.05, 0.05, 0.05)
            _set_emit(p["bg"], col_bg)
            _set_emit(p["num"], col_tx)
            _set_emit(p["cap"], col_tx)

    return {"root": root, "board": board, "rings": rings, "front": front, "page": page, "set": set_page,
            "size": (pw, ph), "hinge_z": h / 2 - 0.07}


def _set_emit(obj, color):
    m = obj.active_material
    em = next(n for n in m.node_tree.nodes if n.type == "EMISSION")
    em.inputs["Color"].default_value = (*color[:3], 1)


def window(name, loc, w=0.62, h=0.78, sky=(0.42, 0.62, 0.95), glow=1.2, moon=False):
    """Window in the dark: frame, cross mullions, glowing panes (day = light blue, night = navy + moon)."""
    root = kit.empty(name, loc, 0.2)
    m_frame = _mat("win_frame", (0.16, 0.16, 0.17, 1), 0.6, 0.1)
    fr = 0.05
    parts = {"root": root}
    parts["panes"] = kit.plane(f"{name}_panes", w - fr, h - fr, (0, 0.01, 0), (math.radians(90), 0, 0))
    kit.set_mat(parts["panes"], kit.emission(f"{name}_sky", sky, glow))
    for k, (sx, sy, px, pz) in {"top": (w, fr, 0, h / 2 - fr / 2), "bot": (w, fr, 0, -h / 2 + fr / 2),
                                "l": (fr, h, -w / 2 + fr / 2, 0), "r": (fr, h, w / 2 - fr / 2, 0),
                                "mv": (fr * 0.6, h, 0, 0), "mh": (w, fr * 0.6, 0, 0)}.items():
        parts[k] = kit.box(f"{name}_{k}", (sx, 0.05, sy), (px, 0, pz))
        kit.set_mat(parts[k], m_frame)
    if moon:
        parts["moon"] = kit.sphere(f"{name}_moon", 0.035)
        parts["moon"].location = (-w * 0.22, -0.005, h * 0.22)
        kit.set_mat(parts["moon"], kit.emission(f"{name}_moonm", (1, 1, 0.95), 2.0))
    for k, o in parts.items():
        if k != "root":
            o.parent = root
    return parts


def progress_board(name, loc, w=0.70, h=0.36, color=(0.35, 0.95, 0.55)):
    """Floating progress widget: dark plate, outline track, glowing fill (scale X 0..1), percent text."""
    root = kit.empty(name, loc, 0.2)
    plate = kit.box(f"{name}_plate", (w, 0.03, h), (0, 0.015, 0), bevel=0.012)
    kit.set_mat(plate, _mat("pb_plate", (0.11, 0.11, 0.12, 1), 0.6, 0.15))
    bw, bh = w * 0.82, h * 0.22
    track = kit.box(f"{name}_track", (bw, 0.012, bh), (0, -0.004, -h * 0.18))
    kit.set_mat(track, _mat("pb_track", (0.03, 0.03, 0.03, 1), 0.8))
    fill_pivot = kit.empty(f"{name}_fill_pivot", (-bw / 2 + 0.01, -0.012, -h * 0.18), 0.03)
    fill = kit.box(f"{name}_fill", (bw - 0.02, 0.01, bh - 0.02), ((bw - 0.02) / 2, 0, 0))
    kit.set_mat(fill, kit.emission(f"{name}_fillm", color, 2.2))
    fill.parent = fill_pivot
    pct = kit.text(f"{name}_pct", "0%", size=0.11, loc=(0, -0.006, h * 0.16), color=(1, 1, 1), strength=1.2, bold=True)
    for o in (plate, track, fill_pivot, pct):
        o.parent = root
    fill_pivot.scale.x = 0.0
    return {"root": root, "plate": plate, "track": track, "fill": fill, "fill_pivot": fill_pivot, "pct": pct}


# ----------------------------------------------------------------------------- clutter

def paper(name, w=0.21, h=0.297, color=PAPER, glow=0.9):
    """A sheet (vertical plane facing -Y), single-sided emission so it reads in the dark."""
    p = kit.plane(name, w, h, (0, 0, 0), (math.radians(90), 0, 0))
    m = bpy.data.materials.get("paper_sheet") or kit.emission("paper_sheet", color, glow)
    kit.set_mat(p, m)
    return p


def paper_stack(name, loc, n=6, w=0.22, d=0.30, step=0.012, jitter=0.02, seed=1):
    rnd = random.Random(seed)
    root = kit.empty(name, loc, 0.1)
    m = bpy.data.materials.get("paper_stack") or kit.dark("paper_stack", PAPER, 0.8, 0.35)
    sheets = []
    for i in range(n):
        s = kit.box(f"{name}_{i}", (w, d, step * 0.9), (rnd.uniform(-jitter, jitter), rnd.uniform(-jitter, jitter),
                                                         step * (i + 0.5)))
        s.rotation_euler.z = rnd.uniform(-0.12, 0.12)
        kit.set_mat(s, m)
        s.parent = root
        sheets.append(s)
    return {"root": root, "sheets": sheets}


def cup(name, loc=(0, 0, 0), r=0.04, h=0.11):
    """Paper coffee cup: white cylinder + brown sleeve (the reference stacks them into a tower)."""
    root = kit.empty(name, loc, 0.05)
    bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=r * 0.82, radius2=r, depth=h, location=(0, 0, h / 2))
    body = bpy.context.active_object
    body.name = f"{name}_body"
    kit.set_mat(body, bpy.data.materials.get("cup_white") or kit.dark("cup_white", (0.92, 0.92, 0.9, 1), 0.6, 0.4))
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=r * 0.95, depth=h * 0.35, location=(0, 0, h * 0.52))
    sleeve = bpy.context.active_object
    sleeve.name = f"{name}_sleeve"
    kit.set_mat(sleeve, bpy.data.materials.get("cup_sleeve") or kit.dark("cup_sleeve", (0.45, 0.28, 0.16, 1), 0.7, 0.25))
    for o in (body, sleeve):
        o.parent = root
    return {"root": root, "body": body, "sleeve": sleeve}


# ----------------------------------------------------------------------------- weather

def cloud(name, loc, w=0.9, puffs=9, seed=3, color=(0.30, 0.30, 0.32, 1)):
    """Storm cloud: overlapping spheres on a flat bottom, a dark outline like the figures."""
    rnd = random.Random(seed)
    root = kit.empty(name, loc, 0.2)
    m = bpy.data.materials.get(f"cloud_{color}") or kit.toon(f"cloud_{color}", color, 0.55)
    balls = []
    for i in range(puffs):
        u = (i + 0.5) / puffs
        x = (u - 0.5) * w
        r = (0.17 + 0.12 * math.sin(math.pi * u)) * (w / 0.9) * rnd.uniform(0.85, 1.1)
        z = r * 0.55 + rnd.uniform(-0.02, 0.05) + 0.05 * math.sin(math.pi * u)
        b = kit.sphere(f"{name}_{i}", r, seg=20, rings=12)
        b.location = (x, rnd.uniform(-0.04, 0.04), z)
        b.scale.z = 0.92
        kit.set_mat(b, m)
        kit.add_outline(b, 0.014)
        b.parent = root
        balls.append(b)
    # flat underside
    base = kit.capsule(f"{name}_base", w * 0.9, 0.14)
    base.rotation_euler.z = math.radians(-90)
    base.location = (-w * 0.45, 0, 0.1)
    base.scale.z = 0.6
    kit.set_mat(base, m)
    kit.add_outline(base, 0.014)
    base.parent = root
    balls.append(base)
    return {"root": root, "balls": balls}


def rain(name, loc, w=0.8, depth=0.3, top=0.0, bottom=-1.2, drops=40, seed=5, speed=4.0, fps=60, frames=(1, 900)):
    """Falling streaks under a cloud, each drop loops (cyclic linear keys)."""
    rnd = random.Random(seed)
    root = kit.empty(name, loc, 0.1)
    m = bpy.data.materials.get("rain") or kit.emission("rain", (0.75, 0.82, 0.95), 1.4)
    fall = top - bottom
    period = max(2, int(round(fall / speed * fps)))
    out = []
    for i in range(drops):
        dr = kit.capsule(f"{name}_{i}", 0.09, 0.0045)
        dr.rotation_euler.x = math.radians(90)  # capsule +Y -> world +Z
        x = rnd.uniform(-w / 2, w / 2)
        y = rnd.uniform(-depth / 2, depth / 2)
        kit.set_mat(dr, m)
        dr.parent = root
        off = rnd.randrange(period)
        f0 = frames[0] - off
        dr.location = (x, y, top)
        dr.keyframe_insert("location", index=2, frame=f0)
        dr.location = (x, y, bottom)
        dr.keyframe_insert("location", index=2, frame=f0 + period)
        fc = next(c for c in kit._fcurves(dr.animation_data.action) if c.data_path == "location" and c.array_index == 2)
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.modifiers.new("CYCLES")
        out.append(dr)
    return {"root": root, "drops": out}


def lightning(name, start, end, seed=7, segs=9, jag=0.12, radius=0.016, color=(0.85, 0.80, 1.0), strength=12.0,
              branches=2):
    """Jagged bolt from `start` to `end` (world), as a bevelled poly curve with a hot emission."""
    rnd = random.Random(seed)
    start, end = Vector(start), Vector(end)
    m = bpy.data.materials.get(f"bolt_{name}") or kit.emission(f"bolt_{name}", color, strength)

    def bolt(bname, a, b, n, j, rad):
        pts = [a]
        d = b - a
        side = d.cross(Vector((0, 1, 0))).normalized()
        for k in range(1, n):
            u = k / n
            pts.append(a + d * u + side * rnd.uniform(-j, j) + Vector((0, rnd.uniform(-j, j) * 0.3, 0)))
        pts.append(b)
        cu = bpy.data.curves.new(bname, "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = rad
        cu.bevel_resolution = 2
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, co in zip(sp.points, pts):
            p.co = (*co, 1)
        ob = bpy.data.objects.new(bname, cu)
        bpy.context.scene.collection.objects.link(ob)
        cu.materials.append(m)
        return ob, pts

    main, pts = bolt(name, start, end, segs, jag, radius)
    objs = [main]
    for i in range(branches):
        k = rnd.randrange(2, max(3, segs - 2))
        a = pts[k]
        b = a + Vector((rnd.choice((-1, 1)) * rnd.uniform(0.15, 0.3), 0, -rnd.uniform(0.2, 0.4)))
        ob, _ = bolt(f"{name}_br{i}", a, b, 4, jag * 0.6, radius * 0.6)
        objs.append(ob)
    li = bpy.data.lights.new(f"{name}_flash", "POINT")
    li.energy = 0
    li.color = color
    li.shadow_soft_size = 0.3
    lo = bpy.data.objects.new(f"{name}_flash", li)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (start + end) / 2
    return {"bolts": objs, "flash": lo}


# ----------------------------------------------------------------------------- gym / stage

def pullup_bar(name, z=2.30, x0=-1.85, x1=1.85, radius=0.024, points=61):
    """Long horizontal bar on two posts. The bar is a poly curve so it can bend per frame (set_bend)."""
    m_bar = bpy.data.materials.get("bar_metal") or kit.dark("bar_metal", (0.62, 0.62, 0.64, 1), 0.28, 0.12)
    m_post = _mat("bar_post", (0.16, 0.16, 0.17, 1), 0.5, 0.05)
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(points - 1)
    xs = [x0 + (x1 - x0) * i / (points - 1) for i in range(points)]
    for p, x in zip(sp.points, xs):
        p.co = (x, 0, z, 1)
    ob = kit._link(bpy.data.objects.new(name, cu))
    cu.materials.append(m_bar)
    posts = []
    for i, x in enumerate((x0 - 0.04, x1 + 0.04)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.035, depth=z + 0.06, location=(x, 0, (z + 0.06) / 2))
        po = bpy.context.active_object
        po.name = f"{name}_post{i}"
        kit.set_mat(po, m_post)
        posts.append(po)

    def set_bend(dips):
        """dips: [(x, depth, width)] -> bar sags around each x (depth in m, gaussian width in m)."""
        for p, x in zip(sp.points, xs):
            dz = sum(d * math.exp(-((x - cx) / w) ** 2) for cx, d, w in dips)
            p.co = (x, 0, z - dz, 1)

    return {"bar": ob, "posts": posts, "set_bend": set_bend, "z": z}


def light_beam(name, top, bottom_z=0.25, r_top=0.06, r_bottom=0.75, strength=0.35, color=(1.0, 0.97, 0.9)):
    """Fake volumetric spotlight shaft: open cone, additive emission fading to the edges and the floor."""
    top = Vector(top)
    depth = top.z - bottom_z
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=r_bottom, radius2=r_top, depth=depth, end_fill_type="NOTHING",
                                    location=(top.x, top.y, bottom_z + depth / 2))
    ob = bpy.context.active_object
    ob.name = name
    m, nt, out = kit._mat(f"beam_{name}")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")          # brighter near the lamp, gone at the floor
    mr.inputs["From Min"].default_value = -depth / 2
    mr.inputs["From Max"].default_value = depth / 2
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = 1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    lw = nt.nodes.new("ShaderNodeLayerWeight")       # soft edges: facing the camera = dense, silhouette = thin
    lw.inputs["Blend"].default_value = 0.5
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(mr.outputs["Result"], mul.inputs[0])
    nt.links.new(inv.outputs[0], mul.inputs[1])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 1.6
    nt.links.new(mul.outputs[0], pw.inputs[0])
    gain = nt.nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = strength
    gain.name = "gain"
    nt.links.new(pw.outputs[0], gain.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    nt.links.new(gain.outputs[0], em.inputs["Strength"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    kit.set_mat(ob, m)
    ob.visible_shadow = False
    return {"obj": ob, "gain": nt.nodes["gain"], "strength": strength}


def bolt_pool(name, n=8, pts=7, core=0.006, sheath=0.018, color=(1.0, 0.12, 0.08), strength=7.0):
    """Reusable 'black lightning with a red rim' strokes: black core + red edge sheath, points set per frame."""
    m_core = bpy.data.materials.get("bolt_core") or kit.emission("bolt_core", (0, 0, 0), 0.0)
    m_sh, nt, out = kit._mat(f"{name}_sheath")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Facing"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    pool = []
    for i in range(n):
        pair = []
        for kind, rad, mat in (("core", core, m_core), ("sheath", sheath, m_sh)):
            cu = bpy.data.curves.new(f"{name}_{i}_{kind}", "CURVE")
            cu.dimensions = "3D"
            cu.bevel_depth = rad
            cu.bevel_resolution = 1
            sp = cu.splines.new("POLY")
            sp.points.add(pts - 1)
            ob = kit._link(bpy.data.objects.new(f"{name}_{i}_{kind}", cu))
            cu.materials.append(mat)
            ob.visible_shadow = False
            ob.hide_render = True
            pair.append((ob, sp))
        pool.append(pair)

    def set_bolt(i, points, visible=True):
        for ob, sp in pool[i]:
            ob.hide_render = not visible
            if visible:
                for p, co in zip(sp.points, points):
                    p.co = (*co, 1)

    return {"pool": pool, "set": set_bolt, "n": n, "pts": pts}
