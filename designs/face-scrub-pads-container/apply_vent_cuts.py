"""Apply SVG vent patterns to EarAndPads FreeCAD model. Run inside FreeCAD."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import FreeCAD as App
import Part

_VENT_HOLES_PATH = Path("/Users/darh/Work/3dPrinting/designs/face-scrub-pads-container/vent_holes.py")
_spec = importlib.util.spec_from_file_location("vent_holes", _VENT_HOLES_PATH)
vent_holes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vent_holes)

# --- pattern layout (mm) ---
PANEL_W = 60.0 * math.pi - 40.0
PANEL_H = 50.0
Z_BAND_BOTTOM = 6.0  # 5 mm above interior floor (bottom at 1 mm)
SLOT_LEFT = 32.0
SLOT_WIDTH = 20.0
SLOT_CENTER_U = SLOT_LEFT + SLOT_WIDTH / 2.0  # 42 mm on unwrap

STICKS_CX = -30.0
STICKS_R_IN = 29.0
STICKS_R_OUT = 31.0

PADS_CX = 31.0
PADS_R_IN = 30.0
PADS_R_OUT = 32.0
# Pad slot sketch: X 21–41 mm on the pads cup (−Y outer face), matches vent gap u = 32–52 mm.
PADS_SLOT_X_LEFT = 21.0
PADS_SLOT_X_RIGHT = 41.0

WALL = 2.0
CUT_DEPTH = WALL + 2.0
OUTWARD_PAD = 0.5  # start cutters slightly outside the wall so edge vents fully pierce


def cup_point(cx: float, r: float, theta: float, z: float) -> App.Vector:
    return App.Vector(cx + r * math.cos(theta), r * math.sin(theta), z)


def hole_solid(
    hole_uv: list[tuple[float, float]],
    cx: float,
    r_out: float,
    theta_at_u,
) -> Part.Shape:
    """Planar rounded triangle in tangent plane, extruded through wall."""
    u_c = sum(p[0] for p in hole_uv) / len(hole_uv)
    v_c = sum(p[1] for p in hole_uv) / len(hole_uv)
    theta_c = theta_at_u(u_c)
    z_c = Z_BAND_BOTTOM + v_c
    p0 = cup_point(cx, r_out, theta_c, z_c)
    tangent = App.Vector(-math.sin(theta_c), math.cos(theta_c), 0)
    z_axis = App.Vector(0, 0, 1)
    outward = App.Vector(math.cos(theta_c), math.sin(theta_c), 0)

    pts3d = []
    for u, v in hole_uv:
        du = u - u_c
        dv = v - v_c
        pts3d.append(p0 + tangent * du + z_axis * dv)

    wire = Part.makePolygon(pts3d + [pts3d[0]])
    face = Part.Face(wire)
    # Pad outside + cut through (same tangent outline as SVG; no cylindrical fan warp).
    outer = face.extrude(outward * OUTWARD_PAD)
    through = face.extrude(outward * (-(CUT_DEPTH + OUTWARD_PAD)))
    return outer.fuse(through)


def all_hole_solids(
    sticks_holes, pads_holes
) -> list[Part.Shape]:
    shapes = [hole_solid(h, STICKS_CX, STICKS_R_OUT, sticks_theta) for h in sticks_holes]
    shapes += [hole_solid(h, PADS_CX, PADS_R_OUT, pads_theta) for h in pads_holes]
    if not shapes:
        raise RuntimeError("no holes parsed")
    return shapes


def sticks_theta(u: float) -> float:
    # outward -X at panel center
    return math.pi + (u - PANEL_W / 2.0) / STICKS_R_OUT


def pads_slot_edge_thetas() -> tuple[float, float]:
    """Outer-wall angles (rad) at the left/right slot edges in the model."""
    r = PADS_R_OUT
    dx_l = PADS_SLOT_X_LEFT - PADS_CX
    dx_r = PADS_SLOT_X_RIGHT - PADS_CX
    y_l = -math.sqrt(max(r * r - dx_l * dx_l, 0.0))
    y_r = -math.sqrt(max(r * r - dx_r * dx_r, 0.0))
    return math.atan2(y_l, dx_l), math.atan2(y_r, dx_r)


def pads_theta(u: float) -> float:
    # Unwrap u = SLOT_LEFT..SLOT_LEFT+SLOT_WIDTH spans the physical pad slot on −Y.
    th_l, th_r = pads_slot_edge_thetas()
    return th_l + (u - SLOT_LEFT) * (th_r - th_l) / SLOT_WIDTH


def apply(doc: App.Document) -> None:
    sticks_holes = vent_holes.sticks_holes()
    pads_holes = vent_holes.pads_holes()

    hole_shapes = all_hole_solids(sticks_holes, pads_holes)

    body = doc.getObject("Body")
    # remove previous vent features
    for obj in list(doc.Objects):
        if (
            obj.Name in ("VentCutters", "VentSubtractive")
            or obj.Name.startswith("VentHole")
            or obj.Label.startswith("Vent")
        ):
            if obj in body.Group:
                body.removeObject(obj)
            doc.removeObject(obj.Name)

    # One cutter per hole — fusing many tools can make the boolean drop isolated vents.
    cutter_objs = []
    for i, shape in enumerate(hole_shapes):
        feat = doc.addObject("Part::Feature", f"VentHole{i:03d}")
        feat.Shape = shape
        feat.ViewObject.Visibility = False
        cutter_objs.append(feat)

    vent_bool = body.newObject("PartDesign::Boolean", "VentSubtractive")
    vent_bool.Type = "Cut"
    vent_bool.Group = cutter_objs
    vent_bool.Refine = True
    doc.recompute()
    if vent_bool.Shape.isNull() or vent_bool.Shape.Volume < 1:
        raise RuntimeError("Vent boolean cut failed to produce valid shape")


if __name__ == "__main__":
    doc = App.getDocument("EarAndPads")
    apply(doc)
    save_paths = [
        "/Users/darh/Work/3dPrinting/FreeCAD/EarAndPads.FCStd",
        "/Users/darh/Work/3dPrinting/designs/face-scrub-pads-container/EarAndPads.FCStd",
    ]
    for p in save_paths:
        doc.saveAs(p)
