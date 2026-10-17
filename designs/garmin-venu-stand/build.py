# Garmin Venu 3 / 3S charging stand
#
# Regenerates designs/garmin-venu-stand/garmin-venu-stand.FCStd.
# Run:  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd build.py
#
# Assumptions baked into the numbers below:
#   * Bambu Lab A1, stock 0.4 mm nozzle
#   * Arm: PETG. Base and cover: PLA or PETG
#   * Official Garmin 4-pin cable. Plug-body size is an estimate until you measure it.
#   * 2.5 inch drive, SFF-8201, 9.5 mm thick, unless you edit the drive_* cells
#   * Cable plan A: arm split left/right, tunnel on the split, USB exits the rear center
#
# Edit plug_w / plug_h / plug_d / plug_clear in the Params spreadsheet and recompute
# to resize the test slug and the arm pockets. Edit drive_* to resize the bay.
# Reach, rise, and dock angle are built by this script; change them here and rerun.

import math
import os
import sys
import traceback

print("build.py starting", flush=True)

import FreeCAD as App
import Part
import Sketcher

HERE = os.path.dirname(os.path.abspath(__file__))
DOC_PATH = os.path.join(HERE, "garmin-venu-stand.FCStd")
MESH_DIR = os.path.join(HERE, "meshes")

# alias, value, unit, note
INPUTS = [
    ("drive_len", 100.5, "mm", "SFF-8201 length. Measure your drive and edit."),
    ("drive_wid", 69.85, "mm", "SFF-8201 width."),
    ("drive_thk", 9.5, "mm", "Use 7 or 15 if your 2.5 inch drive is not 9.5 mm."),
    ("drive_clear_xy", 1.0, "mm", "Loose fit, each side."),
    ("drive_clear_z", 1.5, "mm", "Loose fit above the drive. The drive sits on the cover."),
    ("wall", 3.0, "mm", "Outer wall."),
    ("cover_thk", 2.8, "mm", "Bottom cover. Screw heads sit below it."),
    ("roof", 3.2, "mm", "Shell top skin."),
    ("base_len", 170.0, "mm", "X is forward, origin at the rear-left corner."),
    ("base_wid", 108.0, "mm", ""),
    ("rear_block", 52.0, "mm", "Solid rear block: arm screws and cable channel."),
    ("flange_len", 44.0, "mm", "Arm foot length."),
    ("flange_wid", 42.0, "mm", "Arm foot width."),
    ("flange_thk", 18.0, "mm", "Arm foot height."),
    ("flange_x0", 6.0, "mm", "Arm foot, rear edge."),
    ("curve_inset", 10.0, "mm", "Curve starts this far inside the front of the foot."),
    ("arm_reach", 88.0, "mm", "Forward from the curve start to the plug face."),
    ("arm_rise", 52.0, "mm", "Up from the curve start to the plug face."),
    ("arm_lead", 36.0, "mm", "Horizontal curve handle. Larger is a gentler bend."),
    ("arm_handle", 26.0, "mm", "Handle along the plug axis."),
    ("dock_angle", 55.0, "deg", "Watch face from horizontal."),
    ("cable_bore", 5.0, "mm", "Tunnel diameter inside the arm."),
    ("groove_w", 14.0, "mm", "Rear channel width. A USB-C plug can pass."),
    ("groove_h", 8.0, "mm", "Rear channel height. The cover is the floor."),
    ("riser_d", 7.0, "mm", "Vertical hole from the channel into the arm."),
    ("plug_w", 14.0, "mm", "ESTIMATE. Width of the Garmin plug body."),
    ("plug_h", 9.0, "mm", "ESTIMATE. Height of the Garmin plug body."),
    ("plug_d", 12.0, "mm", "ESTIMATE. Depth of the plug body in the pocket."),
    ("plug_clear", 0.2, "mm", "Snug fit, each side. Loosen if the test slug grips too hard."),
    ("funnel_d", 2.5, "mm", "Lead-in depth at the plug face."),
    ("funnel_extra", 2.0, "mm", "Lead-in opening, extra each side."),
    ("screw_d", 3.3, "mm", "M3 clearance hole."),
    ("nut_af", 5.8, "mm", "M3 nut trap across flats (nut is 5.5)."),
    ("nut_t", 2.6, "mm", "M3 nut trap depth (nut is 2.4)."),
    ("screw_margin", 8.0, "mm", "Cover-screw inset from the outer edge."),
    ("cbore_d", 6.2, "mm", "M3 socket-head counterbore on the arm."),
    ("cbore_h", 3.2, "mm", ""),
    ("screw_offset", 5.8, "mm", "Arm clamp screws, offset from the cable center."),
    ("mount_x", 18.0, "mm", "Arm-to-base screws, X."),
    ("mount_inset_y", 8.0, "mm", "Arm-to-base screws, inset from the foot side."),
    ("slug_margin", 8.0, "mm", "Plastic around the pocket on the test slug."),
    ("slug_back", 6.0, "mm", "Solid behind the pocket on the test slug."),
]

# (parameter along the curve, full width, full thickness)
SECTIONS = (
    (0.00, 28.0, 14.0),
    (0.28, 22.0, 20.0),
    (0.55, 20.0, 20.0),
    (0.78, 26.0, 24.0),
    (1.00, 34.0, 28.0),
)
CLAMP_U = (0.30, 0.52, 0.70)


def compute(inp):
    p = dict(inp)
    p["cavity_h"] = p["drive_thk"] + p["drive_clear_z"]
    p["shell_h"] = p["roof"] + p["cavity_h"]
    p["slot_l"] = p["drive_len"] + 2 * p["drive_clear_xy"]
    p["slot_w"] = p["drive_wid"] + 2 * p["drive_clear_xy"]
    p["slot_x0"] = p["rear_block"] + 2
    p["slot_y0"] = (p["base_wid"] - p["slot_w"]) / 2
    p["flange_y0"] = (p["base_wid"] - p["flange_wid"]) / 2
    p["curve_x0"] = p["flange_x0"] + p["flange_len"] - p["curve_inset"]
    p["z_shell"] = p["cover_thk"]
    p["z_flange"] = p["cover_thk"] + p["shell_h"]
    p["curve_z"] = p["z_flange"] + p["flange_thk"] / 2
    p["mid_y"] = p["base_wid"] / 2
    p["mount_y1"] = p["flange_y0"] + p["mount_inset_y"]
    p["mount_y2"] = p["flange_y0"] + p["flange_wid"] - p["mount_inset_y"]
    p["cable_x"] = p["curve_x0"]
    p["cable_y"] = p["mid_y"]
    p["corner_x1"] = p["screw_margin"]
    p["corner_x2"] = p["base_len"] - p["screw_margin"]
    p["corner_y1"] = p["screw_margin"]
    p["corner_y2"] = p["base_wid"] - p["screw_margin"]
    p["nut_r"] = p["nut_af"] / math.sqrt(3)
    p["plug_pocket_w"] = p["plug_w"] + 2 * p["plug_clear"]
    p["plug_pocket_h"] = p["plug_h"] + 2 * p["plug_clear"]
    p["funnel_w"] = p["plug_pocket_w"] + 2 * p["funnel_extra"]
    p["funnel_h"] = p["plug_pocket_h"] + 2 * p["funnel_extra"]
    p["pocket_depth"] = p["plug_d"] + p["funnel_d"]
    p["slug_w"] = p["funnel_w"] + 2 * p["slug_margin"]
    p["slug_h"] = p["funnel_h"] + 2 * p["slug_margin"]
    p["slug_d"] = p["pocket_depth"] + p["slug_back"]
    return p


def validate(p):
    slot_end = p["slot_x0"] + p["slot_l"]
    if slot_end > p["base_len"] - 12:
        raise RuntimeError("drive bay hits the front wall; shorten drive_len or lengthen base_len")
    if p["slot_x0"] < p["rear_block"]:
        raise RuntimeError("drive bay hits the rear block")
    flange_front = p["flange_x0"] + p["flange_len"]
    if flange_front > p["rear_block"]:
        raise RuntimeError("arm foot sticks out of the rear block")
    if p["curve_x0"] <= p["flange_x0"] or p["curve_x0"] >= flange_front:
        raise RuntimeError("curve start is not inside the arm foot")
    gap = p["screw_offset"] - p["screw_d"] / 2 - p["cable_bore"] / 2
    if gap < 1.2:
        raise RuntimeError("arm screws are too close to the cable tunnel (%.2f mm)" % gap)
    head_x = p["curve_x0"] + p["arm_reach"]
    if head_x > p["base_len"] - 25:
        raise RuntimeError("plug face hangs too far past the base")
    print("layout ok: bay x %.1f..%.1f, plug face x %.1f, screw-to-cable gap %.2f mm" % (
        p["slot_x0"], slot_end, head_x, gap))


def add_sheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "Params")
    sheet.set("A1", "parameter")
    sheet.set("B1", "value")
    sheet.set("C1", "unit")
    sheet.set("D1", "note")
    row = 2
    for alias, value, unit, note in INPUTS:
        sheet.set("A%d" % row, alias)
        sheet.set("B%d" % row, repr(value) if isinstance(value, float) else str(value))
        sheet.setAlias("B%d" % row, alias)
        sheet.set("C%d" % row, unit)
        sheet.set("D%d" % row, note)
        row += 1
    formulas = [
        ("cavity_h", "=drive_thk + drive_clear_z", "mm", "Drive bay height."),
        ("shell_h", "=roof + cavity_h", "mm", "Shell height above the cover."),
        ("slot_l", "=drive_len + 2 * drive_clear_xy", "mm", ""),
        ("slot_w", "=drive_wid + 2 * drive_clear_xy", "mm", ""),
        ("slot_x0", "=rear_block + 2", "mm", ""),
        ("slot_y0", "=(base_wid - slot_w) / 2", "mm", ""),
        ("flange_y0", "=(base_wid - flange_wid) / 2", "mm", ""),
        ("curve_x0", "=flange_x0 + flange_len - curve_inset", "mm", ""),
        ("z_shell", "=cover_thk", "mm", "Bottom of the shell."),
        ("z_flange", "=cover_thk + shell_h", "mm", "Bottom of the arm foot."),
        ("mid_y", "=base_wid / 2", "mm", ""),
        ("mount_y1", "=flange_y0 + mount_inset_y", "mm", ""),
        ("mount_y2", "=flange_y0 + flange_wid - mount_inset_y", "mm", ""),
        ("cable_x", "=curve_x0", "mm", "Rear-center channel meets the arm here."),
        ("cable_y", "=mid_y", "mm", ""),
        ("corner_x1", "=screw_margin", "mm", ""),
        ("corner_x2", "=base_len - screw_margin", "mm", ""),
        ("corner_y1", "=screw_margin", "mm", ""),
        ("corner_y2", "=base_wid - screw_margin", "mm", ""),
        ("nut_r", "=nut_af / sqrt(3)", "mm", "Hex vertex radius."),
        ("plug_pocket_w", "=plug_w + 2 * plug_clear", "mm", "Snug pocket width."),
        ("plug_pocket_h", "=plug_h + 2 * plug_clear", "mm", "Snug pocket height."),
        ("funnel_w", "=plug_pocket_w + 2 * funnel_extra", "mm", ""),
        ("funnel_h", "=plug_pocket_h + 2 * funnel_extra", "mm", ""),
        ("pocket_depth", "=plug_d + funnel_d", "mm", ""),
        ("slug_w", "=funnel_w + 2 * slug_margin", "mm", ""),
        ("slug_h", "=funnel_h + 2 * slug_margin", "mm", ""),
        ("slug_d", "=pocket_depth + slug_back", "mm", ""),
    ]
    for alias, formula, unit, note in formulas:
        sheet.set("A%d" % row, alias)
        sheet.set("B%d" % row, formula)
        sheet.setAlias("B%d" % row, alias)
        sheet.set("C%d" % row, unit)
        sheet.set("D%d" % row, note)
        row += 1
    sheet.set("A%d" % row, "routing")
    sheet.set("D%d" % row, "Plan A. Arm splits left/right. Cable tunnel on the split. USB leaves through the rear face, centered.")
    row += 1
    sheet.set("A%d" % row, "print")
    sheet.set("D%d" % row, "0.4 mm nozzle. PETG arm, PLA or PETG base. Shell: top face on the bed, bay up. Cover: flat. Each arm half: split face on the bed.")
    row += 1
    sheet.set("A%d" % row, "hardware")
    sheet.set("D%d" % row, "4x M3x10 screws and nuts close the cover. 2x M3x35 screws drop through the arm foot into nuts in the shell. 3x M3x20 screws and nuts clamp the arm halves and the plug.")
    row += 1
    sheet.set("A%d" % row, "rebuild")
    sheet.set("D%d" % row, "Plug size and drive size recompute from this sheet. Reach, rise, and dock angle: edit build.py and run it again.")
    return sheet


def xy_plane(body):
    # The second body cannot reuse the name XY_Plane, so match the plane normal.
    for obj in body.Origin.OriginFeatures:
        if obj.TypeId != "App::Plane":
            continue
        normal = obj.Placement.Rotation.multVec(App.Vector(0, 0, 1))
        if abs(normal.z) > 0.99 and abs(normal.x) < 0.01 and abs(normal.y) < 0.01:
            return obj
    raise RuntimeError("no XY plane on %s" % body.Name)


def attach_xy(sk, body, z_expr, z_seed):
    sk.AttachmentSupport = [(xy_plane(body), "")]
    sk.MapMode = "FlatFace"
    sk.AttachmentOffset = App.Placement(App.Vector(0, 0, z_seed), App.Rotation())
    sk.setExpression("AttachmentOffset.Base.z", z_expr)


def require_constrained(sk):
    sk.solve()
    if not sk.FullyConstrained:
        raise RuntimeError("sketch %s is not fully constrained" % sk.Name)


def add_rect(sk, x0, y0, w, h, x0_expr, y0_expr, w_expr, h_expr):
    sk.addGeometry(Part.LineSegment(App.Vector(x0, y0, 0), App.Vector(x0 + w, y0, 0)), False)
    sk.addGeometry(Part.LineSegment(App.Vector(x0 + w, y0, 0), App.Vector(x0 + w, y0 + h, 0)), False)
    sk.addGeometry(Part.LineSegment(App.Vector(x0 + w, y0 + h, 0), App.Vector(x0, y0 + h, 0)), False)
    sk.addGeometry(Part.LineSegment(App.Vector(x0, y0 + h, 0), App.Vector(x0, y0, 0)), False)
    n = sk.GeometryCount
    base = n - 4
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", base + i, 2, base + (i + 1) % 4, 1))
    sk.addConstraint(Sketcher.Constraint("Horizontal", base))
    sk.addConstraint(Sketcher.Constraint("Horizontal", base + 2))
    sk.addConstraint(Sketcher.Constraint("Vertical", base + 1))
    sk.addConstraint(Sketcher.Constraint("Vertical", base + 3))
    c = sk.addConstraint(Sketcher.Constraint("DistanceX", base, 1, x0))
    sk.renameConstraint(c, "x0_%d" % base)
    sk.setExpression("Constraints.x0_%d" % base, x0_expr)
    c = sk.addConstraint(Sketcher.Constraint("DistanceY", base, 1, y0))
    sk.renameConstraint(c, "y0_%d" % base)
    sk.setExpression("Constraints.y0_%d" % base, y0_expr)
    c = sk.addConstraint(Sketcher.Constraint("DistanceX", base, 1, base, 2, w))
    sk.renameConstraint(c, "w_%d" % base)
    sk.setExpression("Constraints.w_%d" % base, w_expr)
    c = sk.addConstraint(Sketcher.Constraint("DistanceY", base + 1, 1, base + 1, 2, h))
    sk.renameConstraint(c, "h_%d" % base)
    sk.setExpression("Constraints.h_%d" % base, h_expr)


def add_circle(sk, cx, cy, r, cx_expr, cy_expr, r_expr):
    geo = sk.addGeometry(Part.Circle(App.Vector(cx, cy, 0), App.Vector(0, 0, 1), r), False)
    c = sk.addConstraint(Sketcher.Constraint("DistanceX", geo, 3, cx))
    sk.renameConstraint(c, "cx_%d" % geo)
    sk.setExpression("Constraints.cx_%d" % geo, cx_expr)
    c = sk.addConstraint(Sketcher.Constraint("DistanceY", geo, 3, cy))
    sk.renameConstraint(c, "cy_%d" % geo)
    sk.setExpression("Constraints.cy_%d" % geo, cy_expr)
    c = sk.addConstraint(Sketcher.Constraint("Radius", geo, r))
    sk.renameConstraint(c, "r_%d" % geo)
    sk.setExpression("Constraints.r_%d" % geo, r_expr)


def add_hex(sk, cx, cy, radius, cx_expr, cy_expr):
    angles = [30, 90, 150, 210, 270, 330]
    pts = []
    for deg in angles:
        a = math.radians(deg)
        pts.append(App.Vector(cx + radius * math.cos(a), cy + radius * math.sin(a), 0))
    first = sk.GeometryCount
    for i in range(6):
        sk.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 6]), False)
    for i in range(6):
        sk.addConstraint(Sketcher.Constraint(
            "Coincident", first + i, 2, first + (i + 1) % 6, 1))
    for i, deg in enumerate(angles):
        a = math.radians(deg)
        c = sk.addConstraint(Sketcher.Constraint("DistanceX", first + i, 1, pts[i].x))
        sk.renameConstraint(c, "hx_%d_%d" % (first, i))
        sk.setExpression(
            "Constraints.hx_%d_%d" % (first, i),
            "%s + Params.nut_r * %.8f" % (cx_expr, math.cos(a)),
        )
        c = sk.addConstraint(Sketcher.Constraint("DistanceY", first + i, 1, pts[i].y))
        sk.renameConstraint(c, "hy_%d_%d" % (first, i))
        sk.setExpression(
            "Constraints.hy_%d_%d" % (first, i),
            "%s + Params.nut_r * %.8f" % (cy_expr, math.sin(a)),
        )


def new_sketch(body, name):
    return body.newObject("Sketcher::SketchObject", name)


def pocket(body, sketch, name, length_expr, length_seed, reversed_):
    poc = body.newObject("PartDesign::Pocket", name)
    poc.Profile = sketch
    poc.Length = length_seed
    poc.setExpression("Length", length_expr)
    poc.Reversed = reversed_
    return poc


def make_shell(doc, p):
    body = doc.addObject("PartDesign::Body", "BaseShell")
    doc.recompute()
    sk = new_sketch(body, "ShellOutline")
    attach_xy(sk, body, "Params.z_shell", p["z_shell"])
    add_rect(sk, 0, 0, p["base_len"], p["base_wid"], "0", "0", "Params.base_len", "Params.base_wid")
    require_constrained(sk)
    pad = body.newObject("PartDesign::Pad", "ShellPad")
    pad.Profile = sk
    pad.Length = p["shell_h"]
    pad.setExpression("Length", "Params.shell_h")

    bay = new_sketch(body, "DriveBay")
    attach_xy(bay, body, "Params.z_shell", p["z_shell"])
    add_rect(
        bay, p["slot_x0"], p["slot_y0"], p["slot_l"], p["slot_w"],
        "Params.slot_x0", "Params.slot_y0", "Params.slot_l", "Params.slot_w",
    )
    require_constrained(bay)
    pocket(body, bay, "DriveBayPocket", "Params.cavity_h", p["cavity_h"], True)

    groove = new_sketch(body, "CableGroove")
    attach_xy(groove, body, "Params.z_shell", p["z_shell"])
    add_rect(
        groove, -1, p["cable_y"] - p["groove_w"] / 2, p["cable_x"] + 1, p["groove_w"],
        "-1",
        "Params.cable_y - Params.groove_w / 2",
        "Params.cable_x + 1",
        "Params.groove_w",
    )
    require_constrained(groove)
    pocket(body, groove, "CableGroovePocket", "Params.groove_h", p["groove_h"], True)

    nuts = new_sketch(body, "NutTraps")
    attach_xy(nuts, body, "Params.z_shell", p["z_shell"])
    nut_centers = [
        ("Params.corner_x1", "Params.corner_y1", p["corner_x1"], p["corner_y1"]),
        ("Params.corner_x1", "Params.corner_y2", p["corner_x1"], p["corner_y2"]),
        ("Params.corner_x2", "Params.corner_y1", p["corner_x2"], p["corner_y1"]),
        ("Params.corner_x2", "Params.corner_y2", p["corner_x2"], p["corner_y2"]),
        ("Params.mount_x", "Params.mount_y1", p["mount_x"], p["mount_y1"]),
        ("Params.mount_x", "Params.mount_y2", p["mount_x"], p["mount_y2"]),
    ]
    for cx_e, cy_e, cx, cy in nut_centers:
        add_hex(nuts, cx, cy, p["nut_r"], cx_e, cy_e)
    require_constrained(nuts)
    pocket(body, nuts, "NutTrapPocket", "Params.nut_t", p["nut_t"], True)

    holes = new_sketch(body, "ScrewHoles")
    attach_xy(holes, body, "Params.z_shell", p["z_shell"])
    screw_r = p["screw_d"] / 2
    for cx_e, cy_e, cx, cy in nut_centers:
        add_circle(holes, cx, cy, screw_r, cx_e, cy_e, "Params.screw_d / 2")
    add_circle(
        holes, p["cable_x"], p["cable_y"], p["riser_d"] / 2,
        "Params.cable_x", "Params.cable_y", "Params.riser_d / 2",
    )
    require_constrained(holes)
    pocket(body, holes, "ScrewHolePocket", "Params.shell_h + 1", p["shell_h"] + 1, True)
    return body


def make_cover(doc, p):
    body = doc.addObject("PartDesign::Body", "BaseCover")
    doc.recompute()
    sk = new_sketch(body, "CoverOutline")
    attach_xy(sk, body, "0", 0)
    add_rect(sk, 0, 0, p["base_len"], p["base_wid"], "0", "0", "Params.base_len", "Params.base_wid")
    require_constrained(sk)
    pad = body.newObject("PartDesign::Pad", "CoverPad")
    pad.Profile = sk
    pad.Length = p["cover_thk"]
    pad.setExpression("Length", "Params.cover_thk")

    holes = new_sketch(body, "CoverHoles")
    attach_xy(holes, body, "0", 0)
    # Cover screws only. The arm screws come down through the foot into nuts
    # trapped in the shell, so the cover just keeps those nuts from falling out.
    centers = [
        ("Params.corner_x1", "Params.corner_y1", p["corner_x1"], p["corner_y1"]),
        ("Params.corner_x1", "Params.corner_y2", p["corner_x1"], p["corner_y2"]),
        ("Params.corner_x2", "Params.corner_y1", p["corner_x2"], p["corner_y1"]),
        ("Params.corner_x2", "Params.corner_y2", p["corner_x2"], p["corner_y2"]),
    ]
    for cx_e, cy_e, cx, cy in centers:
        add_circle(holes, cx, cy, p["screw_d"] / 2, cx_e, cy_e, "Params.screw_d / 2")
    require_constrained(holes)
    pocket(body, holes, "CoverHolePocket", "Params.cover_thk + 1", p["cover_thk"] + 1, True)
    return body


def section_size(u):
    if u <= SECTIONS[0][0]:
        return SECTIONS[0][1], SECTIONS[0][2]
    if u >= SECTIONS[-1][0]:
        return SECTIONS[-1][1], SECTIONS[-1][2]
    for i in range(len(SECTIONS) - 1):
        u0, w0, t0 = SECTIONS[i]
        u1, w1, t1 = SECTIONS[i + 1]
        if u0 <= u <= u1:
            f = (u - u0) / (u1 - u0)
            return w0 + f * (w1 - w0), t0 + f * (t1 - t0)
    return SECTIONS[-1][1], SECTIONS[-1][2]


def frame_at(curve, u):
    pt = curve.value(u)
    tangent = App.Vector(curve.tangent(u)[0])
    tangent.normalize()
    ydir = App.Vector(0, 1, 0)
    nd = ydir.cross(tangent)
    nd.normalize()
    if nd.z < 0:
        nd = nd * -1
    return pt, tangent, ydir, nd


def half_ellipse_wire(curve, u, wy, th):
    # Closed half-section. The straight edge lies on the arm's center plane so the
    # two printed halves meet without a boolean split through the spline.
    pt, tangent, ydir, nd = frame_at(curve, u)
    el = Part.Ellipse()
    el.MajorRadius = wy / 2
    el.MinorRadius = th / 2
    rot = App.Rotation(ydir, nd, tangent)
    # Local +X is global +Y. This arc is the negative-Y half.
    arc = el.toShape(math.pi / 2, 3 * math.pi / 2)
    arc = arc.transformGeometry(App.Placement(pt, rot).toMatrix())
    edge = arc.Edges[0]
    close = Part.makeLine(edge.valueAt(edge.LastParameter), edge.valueAt(edge.FirstParameter))
    return Part.Wire([edge, close])


def ellipse_half_y(wy, th, offset):
    a = wy / 2
    b = th / 2
    val = 1 - (offset / b) ** 2
    if val <= 0.02:
        raise RuntimeError("clamp screw misses the arm section")
    return a * math.sqrt(val)


def make_curve(p):
    ang = math.radians(p["dock_angle"])
    plug_dir = App.Vector(math.sin(ang), 0, math.cos(ang))
    p0 = App.Vector(p["curve_x0"], p["mid_y"], p["curve_z"])
    p1 = p0 + App.Vector(p["arm_lead"], 0, 0)
    p3 = p0 + App.Vector(p["arm_reach"], 0, p["arm_rise"])
    p2 = p3 - plug_dir * p["arm_handle"]
    curve = Part.BezierCurve()
    curve.setPoles([p0, p1, p2, p3])
    return curve, plug_dir, p0, p3


def min_bend_radius(curve):
    best = 1e9
    for i in range(1, 80):
        curv = abs(curve.curvature(i / 80.0))
        if curv > 1e-9:
            best = min(best, 1.0 / curv)
    return best


def u_before_end(curve, remain):
    n = 500
    pts = [curve.value(i / (n - 1)) for i in range(n)]
    seg = [(pts[i] - pts[i - 1]).Length for i in range(1, n)]
    total = sum(seg)
    target = total - remain
    if target <= 0:
        raise RuntimeError("cable tunnel is longer than the arm")
    acc = 0.0
    ts = [i / (n - 1) for i in range(n)]
    for i, length in enumerate(seg):
        if acc + length >= target:
            frac = (target - acc) / length
            return ts[i] + frac * (ts[i + 1] - ts[i])
        acc += length
    return 1.0


def circle_wire(center, normal, radius):
    return Part.Wire(Part.makeCircle(radius, center, normal))


def hex_prism(center, af, depth, along_y):
    radius = af / math.sqrt(3)
    pts = []
    for i in range(6):
        a = math.radians(30 + i * 60)
        pts.append(App.Vector(
            center.x + radius * math.cos(a),
            center.y,
            center.z + radius * math.sin(a),
        ))
    face = Part.Face(Part.makePolygon(pts + [pts[0]]))
    solid = face.extrude(App.Vector(0, along_y * depth, 0))
    return solid


def clamp_centers(p, curve):
    centers = []
    for index, u in enumerate(CLAMP_U):
        wy, th = section_size(u)
        half_y = ellipse_half_y(wy, th, p["screw_offset"])
        pt, _, _, nd = frame_at(curve, u)
        sign = 1 if index % 2 == 0 else -1
        centers.append((pt + nd * (sign * p["screw_offset"]), half_y))
    return centers


def make_arm_halves(p, curve):
    # Left half only. The right half is a mirror, then each side gets its own
    # screw head or nut so the plug is clamped when the halves are screwed together.
    flange = Part.makeBox(
        p["flange_len"], p["flange_wid"] / 2, p["flange_thk"],
        App.Vector(p["flange_x0"], p["mid_y"] - p["flange_wid"] / 2, p["z_flange"]),
    )
    spine = Part.Wire(curve.toShape())
    profiles = [half_ellipse_wire(curve, u, wy, th) for u, wy, th in SECTIONS]
    pipe = spine.makePipeShell(profiles, True, False, 0)
    left = flange.fuse(pipe).removeSplitter()
    if len(left.Solids) != 1:
        raise RuntimeError("arm half did not fuse into one solid (%d)" % len(left.Solids))

    remain = max(p["plug_d"] - 1.0, 2.0)
    u_end = u_before_end(curve, remain)
    bore_wire = Part.Wire(curve.toShape(curve.FirstParameter, u_end))
    r_bore = p["cable_bore"] / 2
    c0, t0, _, _ = frame_at(curve, 0)
    c1, t1, _, _ = frame_at(curve, u_end)
    bore = bore_wire.makePipeShell(
        [circle_wire(c0, t0, r_bore), circle_wire(c1, t1, r_bore)],
        True, False, 0,
    )
    riser = Part.makeCylinder(
        p["riser_d"] / 2,
        p["flange_thk"] + 8,
        App.Vector(p["cable_x"], p["cable_y"], p["z_flange"] - 1),
        App.Vector(0, 0, 1),
    )
    tools = [bore, riser]
    # Foot screws. The two holes are symmetric, so the mirror copies the left one across.
    for mount_y in (p["mount_y1"], p["mount_y2"]):
        tools.append(Part.makeCylinder(
            p["screw_d"] / 2,
            p["flange_thk"] + 4,
            App.Vector(p["mount_x"], mount_y, p["z_flange"] - 2),
            App.Vector(0, 0, 1),
        ))
    centers = clamp_centers(p, curve)
    for center, half_y in centers:
        tools.append(Part.makeCylinder(
            p["screw_d"] / 2,
            half_y * 2 + 6,
            center - App.Vector(0, half_y + 3, 0),
            App.Vector(0, 1, 0),
        ))
    tool = tools[0]
    for extra in tools[1:]:
        tool = tool.fuse(extra)
    left = left.cut(tool).removeSplitter()
    if len(left.Solids) != 1:
        raise RuntimeError("arm half cut left %d solids" % len(left.Solids))

    right = left.mirror(App.Vector(0, p["mid_y"], 0), App.Vector(0, 1, 0))
    nuts = None
    cbores = None
    for center, half_y in centers:
        nut_start = App.Vector(center.x, p["mid_y"] + half_y + 0.4, center.z)
        nut = hex_prism(nut_start, p["nut_af"], p["nut_t"] + 0.6, -1)
        nuts = nut if nuts is None else nuts.fuse(nut)
        cb_start = App.Vector(center.x, p["mid_y"] - half_y - 0.4, center.z)
        cbore = Part.makeCylinder(
            p["cbore_d"] / 2, p["cbore_h"] + 0.6, cb_start, App.Vector(0, 1, 0),
        )
        cbores = cbore if cbores is None else cbores.fuse(cbore)
    right = right.cut(nuts).removeSplitter()
    left = left.cut(cbores).removeSplitter()
    if len(left.Solids) != 1 or len(right.Solids) != 1:
        raise RuntimeError("arm screw seats did not stay single solids")
    return left, right


def rot_plug(plug_dir):
    z = App.Vector(plug_dir)
    z.normalize()
    x = App.Vector(0, 1, 0)
    x = x - z * x.dot(z)
    x.normalize()
    y = z.cross(x)
    y.normalize()
    return App.Rotation(x, y, z)


def add_plug_pockets(doc, body, p, p3, plug_dir):
    doc.recompute()
    plane = body.newObject("PartDesign::Plane", "PlugFace")
    plane.AttachmentSupport = [(xy_plane(body), "")]
    plane.MapMode = "FlatFace"
    plane.AttachmentOffset = App.Placement(p3, rot_plug(plug_dir))

    funnel = new_sketch(body, "FunnelSketch")
    funnel.AttachmentSupport = [(plane, "")]
    funnel.MapMode = "FlatFace"
    add_rect(
        funnel,
        -p["funnel_w"] / 2, -p["funnel_h"] / 2, p["funnel_w"], p["funnel_h"],
        "-(Params.funnel_w / 2)", "-(Params.funnel_h / 2)",
        "Params.funnel_w", "Params.funnel_h",
    )
    require_constrained(funnel)
    pocket(body, funnel, "FunnelPocket", "Params.funnel_d", p["funnel_d"], False)

    snug = new_sketch(body, "PlugSketch")
    snug.AttachmentSupport = [(plane, "")]
    snug.MapMode = "FlatFace"
    add_rect(
        snug,
        -p["plug_pocket_w"] / 2, -p["plug_pocket_h"] / 2,
        p["plug_pocket_w"], p["plug_pocket_h"],
        "-(Params.plug_pocket_w / 2)", "-(Params.plug_pocket_h / 2)",
        "Params.plug_pocket_w", "Params.plug_pocket_h",
    )
    require_constrained(snug)
    pocket(body, snug, "PlugPocket", "Params.pocket_depth", p["pocket_depth"], False)


def adopt_half(doc, name, shape):
    body = doc.addObject("PartDesign::Body", name)
    doc.recompute()
    feat = doc.addObject("Part::Feature", name + "Base")
    feat.Shape = shape
    body.BaseFeature = feat
    doc.recompute()
    return body


def make_slug(doc, p):
    body = doc.addObject("PartDesign::Body", "PlugTestSlug")
    doc.recompute()
    sk = new_sketch(body, "SlugOutline")
    attach_xy(sk, body, "0", 0)
    add_rect(sk, 0, 0, p["slug_w"], p["slug_h"], "0", "0", "Params.slug_w", "Params.slug_h")
    require_constrained(sk)
    pad = body.newObject("PartDesign::Pad", "SlugPad")
    pad.Profile = sk
    pad.Length = p["slug_d"]
    pad.setExpression("Length", "Params.slug_d")
    doc.recompute()

    top = p["slug_d"]
    funnel = new_sketch(body, "SlugFunnel")
    attach_xy(funnel, body, "Params.slug_d", top)
    add_rect(
        funnel,
        (p["slug_w"] - p["funnel_w"]) / 2, (p["slug_h"] - p["funnel_h"]) / 2,
        p["funnel_w"], p["funnel_h"],
        "(Params.slug_w - Params.funnel_w) / 2",
        "(Params.slug_h - Params.funnel_h) / 2",
        "Params.funnel_w", "Params.funnel_h",
    )
    require_constrained(funnel)
    pocket(body, funnel, "SlugFunnelPocket", "Params.funnel_d", p["funnel_d"], False)

    snug = new_sketch(body, "SlugPlug")
    attach_xy(snug, body, "Params.slug_d", top)
    add_rect(
        snug,
        (p["slug_w"] - p["plug_pocket_w"]) / 2, (p["slug_h"] - p["plug_pocket_h"]) / 2,
        p["plug_pocket_w"], p["plug_pocket_h"],
        "(Params.slug_w - Params.plug_pocket_w) / 2",
        "(Params.slug_h - Params.plug_pocket_h) / 2",
        "Params.plug_pocket_w", "Params.plug_pocket_h",
    )
    require_constrained(snug)
    pocket(body, snug, "SlugPlugPocket", "Params.pocket_depth", p["pocket_depth"], False)
    body.Placement = App.Placement(App.Vector(-80, 30, 0), App.Rotation())
    return body


def check_solid(obj, name):
    shape = obj.Shape
    if not shape.isValid() or len(shape.Solids) != 1 or shape.Volume < 1:
        raise RuntimeError("bad solid %s valid=%s solids=%s vol=%s state=%s" % (
            name, shape.isValid(), len(shape.Solids), shape.Volume, obj.State))
    bb = shape.BoundBox
    print("%s  vol=%8.0f mm3   %5.1f x %5.1f x %5.1f mm" % (
        name.ljust(14), shape.Volume, bb.XLength, bb.YLength, bb.ZLength))
    return shape


def inside(shape, point, tol=1e-6):
    return shape.isInside(point, tol, True)


def export_mesh(shape, path):
    import MeshPart
    mesh = MeshPart.meshFromShape(shape, LinearDeflection=0.08, AngularDeflection=0.35)
    mesh.write(path)
    print("wrote", path, mesh.CountPoints, "verts")


def orient_shell(shape):
    # Top face onto the bed: 180 deg about X, then sit on z=0.
    rot = App.Rotation(App.Vector(1, 0, 0), 180)
    moved = shape.transformGeometry(App.Placement(App.Vector(0, 0, 0), rot).toMatrix())
    moved.translate(App.Vector(0, 0, -moved.BoundBox.ZMin))
    return moved


def orient_half(shape, mid_y, right):
    # Split face flat on the bed. Left outward normal is +Y; right is -Y.
    angle = 90 if not right else -90
    rot = App.Rotation(App.Vector(1, 0, 0), angle)
    moved = shape.transformGeometry(App.Placement(App.Vector(0, 0, 0), rot).toMatrix())
    moved.translate(App.Vector(0, 0, -moved.BoundBox.ZMin))
    return moved


def main():
    inp = {alias: value for alias, value, _unit, _note in INPUTS}
    p = compute(inp)
    validate(p)

    doc = App.newDocument("garmin-venu-stand")
    doc.Label = "Garmin Venu stand"
    add_sheet(doc)
    doc.recompute()

    shell = make_shell(doc, p)
    cover = make_cover(doc, p)
    slug = make_slug(doc, p)
    doc.recompute()
    for obj in (shell, cover, slug):
        if "Invalid" in obj.State or "Error" in obj.State:
            raise RuntimeError("%s %s" % (obj.Name, obj.State))

    curve, plug_dir, _p0, p3 = make_curve(p)
    bend = min_bend_radius(curve)
    print("min cable bend radius %.1f mm" % bend)
    if bend < 10:
        raise RuntimeError("bend radius below 10 mm")

    left_shape, right_shape = make_arm_halves(p, curve)
    overlap = left_shape.common(right_shape).Volume
    print("arm halves L %.0f R %.0f overlap %.2f" % (
        left_shape.Volume, right_shape.Volume, overlap), flush=True)
    if overlap > 5:
        raise RuntimeError("arm halves overlap")

    left = adopt_half(doc, "ArmLeft", left_shape)
    right = adopt_half(doc, "ArmRight", right_shape)
    add_plug_pockets(doc, left, p, p3, plug_dir)
    add_plug_pockets(doc, right, p, p3, plug_dir)
    doc.recompute()

    for obj in doc.Objects:
        if "Invalid" in obj.State or "Error" in obj.State or "Touched" in obj.State:
            print("STATE", obj.Name, obj.State)

    shell_s = check_solid(shell, "BaseShell")
    cover_s = check_solid(cover, "BaseCover")
    left_s = check_solid(left, "ArmLeft")
    right_s = check_solid(right, "ArmRight")
    slug_s = check_solid(slug, "PlugTestSlug")

    # Cable center inside the rear channel is open.
    channel_pt = App.Vector(10, p["cable_y"], p["z_shell"] + p["groove_h"] / 2)
    if inside(shell_s, channel_pt):
        raise RuntimeError("rear cable channel is solid")
    # Bay center is open.
    bay_pt = App.Vector(
        p["slot_x0"] + p["slot_l"] / 2,
        p["mid_y"],
        p["z_shell"] + p["cavity_h"] / 2,
    )
    if inside(shell_s, bay_pt):
        raise RuntimeError("drive bay is solid")
    # The pocket is shared by the two halves. A side wall of the head must remain.
    removed = left_shape.Volume - left_s.Volume
    print("left pocket removed %.0f mm3" % removed, flush=True)
    mouth = p3 - plug_dir * (p["funnel_d"] * 0.5) + App.Vector(0, -0.4, 0)
    if inside(left_s, mouth):
        raise RuntimeError("plug lead-in did not cut the left arm")
    deep = p3 - plug_dir * (p["funnel_d"] + min(4.0, p["plug_d"] * 0.5)) + App.Vector(0, -0.4, 0)
    if inside(left_s, deep):
        raise RuntimeError("plug pocket did not cut the left arm")
    side_wall = p3 - plug_dir * (p["funnel_d"] + 2) + App.Vector(0, -p["plug_pocket_w"] / 2 - 1.5, 0)
    if not inside(left_s, side_wall):
        raise RuntimeError("plug pocket ate the side of the head")
    if removed < 50 or removed > 2500:
        raise RuntimeError("plug pocket volume %.0f mm3 is not plausible" % removed)
    # Slug pocket is open.
    slug_mouth = App.Vector(
        -80 + p["slug_w"] / 2,
        30 + p["slug_h"] / 2,
        p["slug_d"] - 1,
    )
    if inside(slug_s, slug_mouth):
        raise RuntimeError("test slug pocket did not cut")

    bb = shell_s.BoundBox
    arm_bb = left_s.fuse(right_s).BoundBox
    height = max(bb.ZMax, cover_s.BoundBox.ZMax, arm_bb.ZMax)
    print("assembly envelope %.1f x %.1f x %.1f mm" % (bb.XLength, bb.YLength, height))
    if bb.XLength > 256 or bb.YLength > 256 or height > 256:
        raise RuntimeError("part exceeds the A1 build volume")

    cutter = Part.makeBox(500, 200, 300, App.Vector(-100, p["mid_y"] + 0.15, -30))
    section = Part.Compound([
        shell_s.cut(cutter),
        cover_s.cut(cutter),
        left_s,
        right_s.cut(cutter),
    ])
    sec_obj = doc.addObject("Part::Feature", "CableSection")
    sec_obj.Shape = section
    sec_obj.Label = "Cable section (right half removed)"

    os.makedirs(MESH_DIR, exist_ok=True)
    export_mesh(orient_shell(shell_s), os.path.join(MESH_DIR, "base-shell.3mf"))
    cover_print = cover_s.copy()
    cover_print.translate(App.Vector(0, 0, -cover_print.BoundBox.ZMin))
    export_mesh(cover_print, os.path.join(MESH_DIR, "base-cover.3mf"))
    export_mesh(orient_half(left_s, p["mid_y"], False), os.path.join(MESH_DIR, "arm-left.3mf"))
    export_mesh(orient_half(right_s, p["mid_y"], True), os.path.join(MESH_DIR, "arm-right.3mf"))
    slug_print = slug_s.copy()
    slug_print.translate(App.Vector(-slug_print.BoundBox.XMin, -slug_print.BoundBox.YMin, 0))
    export_mesh(slug_print, os.path.join(MESH_DIR, "plug-test-slug.3mf"))

    doc.saveAs(DOC_PATH)
    print("saved", DOC_PATH, flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
