"""Vent hole layouts in unwrap (u, v) mm — same geometry as the SVG previews."""
from __future__ import annotations

import math
import random
from typing import Callable

PANEL_W = 60.0 * math.pi - 40.0
PANEL_H = 50.0
EDGE_INSET = 5.0
MIN_GAP = 5.0
MIN_SIDE = 5.0
MAX_SIDE = 15.0

SLOT_LEFT = 32.0
SLOT_WIDTH = 20.0
# Keep vents clear of slot corner flares (sketch X 19–43 mm) on the unwrap.
PADS_GAP_U0 = 30.0
PADS_GAP_U1 = 54.0
PADS_CX = 31.0
PADS_R_OUT = 32.0
PADS_SLOT_X_LEFT = 21.0
PADS_SLOT_X_RIGHT = 41.0
# Extra vents on the pads cup back (+Y), opposite the pad slot on −Y.
PADS_BACK_TARGET = 7
PADS_BACK_MIN_GAP = MIN_GAP
# Pads cup face toward the sticks cup (low u on unwrap, left of the slot band).
PADS_SEAM_U = (6.0, 27.0)
PADS_SEAM_V = (10.0, 42.0)
PADS_SEAM_TARGET = 2
STICKS_SEAM_U = (10.0, 38.0)
STICKS_SEAM_V = (12.0, 40.0)
STICKS_SEAM_SEEDS = ((20.0, 24.0), (27.0, 32.0), (32.0, 18.0))
PADS_SEAM_SEEDS = ((14.0, 26.0), (21.0, 34.0), (11.0, 18.0))


def corner_radius(side: float) -> float:
    return min(2.0, max(0.6, side * 0.12))


def tri_vertices_sharp(side: float, cx: float, cy: float, angle_deg: float) -> list[tuple[float, float]]:
    h = side * math.sqrt(3) / 2
    pts = [(0, -2 * h / 3), (-side / 2, h / 3), (side / 2, h / 3)]
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(x * ca - y * sa + cx, x * sa + y * ca + cy) for x, y in pts]


def svg_arc_points(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    rx: float,
    ry: float | None = None,
    rotation: float = 0.0,
    large_arc: bool = False,
    sweep: bool = True,
    steps: int = 12,
) -> list[tuple[float, float]]:
    """Sample an SVG elliptical arc (W3C endpoint form). Matches svg.path.Arc."""
    if ry is None:
        ry = rx
    if math.hypot(x1 - x2, y1 - y2) < 1e-12 or rx == 0 or ry == 0:
        return [(x1, y1), (x2, y2)]

    cosr = math.cos(math.radians(rotation))
    sinr = math.sin(math.radians(rotation))
    dx = (x1 - x2) / 2.0
    dy = (y1 - y2) / 2.0
    x1p = cosr * dx + sinr * dy
    y1p = -sinr * dx + cosr * dy
    rx_sq, ry_sq = rx * rx, ry * ry
    scale = (x1p * x1p) / rx_sq + (y1p * y1p) / ry_sq
    if scale > 1:
        s = math.sqrt(scale)
        rx *= s
        ry *= s
        rx_sq, ry_sq = rx * rx, ry * ry

    t1 = rx_sq * y1p * y1p
    t2 = ry_sq * x1p * x1p
    c = math.sqrt(abs((rx_sq * ry_sq - t1 - t2) / (t1 + t2)))
    if large_arc == sweep:
        c = -c
    cxp = c * rx * y1p / ry
    cyp = -c * ry * x1p / rx
    cx = cosr * cxp - sinr * cyp + (x1 + x2) / 2.0
    cy = sinr * cxp + cosr * cyp + (y1 + y2) / 2.0

    ux = (x1p - cxp) / rx
    uy = (y1p - cyp) / ry
    vx = (-x1p - cxp) / rx
    vy = (-y1p - cyp) / ry
    n = math.hypot(ux, uy)
    theta = math.degrees(math.acos(max(-1.0, min(1.0, ux / n))))
    if uy < 0:
        theta = -theta
    theta %= 360

    n2 = math.hypot(ux * ux + uy * uy) * math.hypot(vx * vx + vy * vy)
    d = max(-1.0, min(1.0, (ux * vx + uy * vy) / n2))
    delta = math.degrees(math.acos(d))
    if (ux * vy - uy * vx) < 0:
        delta = -delta
    delta %= 360
    if not sweep:
        delta -= 360

    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        pos = i / steps
        angle = math.radians(theta + delta * pos)
        x = cosr * math.cos(angle) * rx - sinr * math.sin(angle) * ry + cx
        y = sinr * math.cos(angle) * rx + cosr * math.sin(angle) * ry + cy
        pts.append((x, y))
    return pts


def rounded_triangle_outline(
    side: float, cx: float, cy: float, angle_deg: float, r: float, arc_steps: int = 12
) -> list[tuple[float, float]]:
    """CCW outline with corner fillets — same M/L/A rules as the SVG preview."""
    verts = tri_vertices_sharp(side, cx, cy, angle_deg)
    area = sum(verts[i][0] * verts[(i + 1) % 3][1] - verts[(i + 1) % 3][0] * verts[i][1] for i in range(3)) / 2
    if area < 0:
        verts = list(reversed(verts))

    outline: list[tuple[float, float]] = []
    n = len(verts)
    for i in range(n):
        a = verts[(i - 1) % n]
        b = verts[i]
        c = verts[(i + 1) % n]
        u = (a[0] - b[0], a[1] - b[1])
        v = (c[0] - b[0], c[1] - b[1])
        lu, lv = math.hypot(*u), math.hypot(*v)
        if lu < 1e-9 or lv < 1e-9:
            continue
        u = (u[0] / lu, u[1] / lu)
        v = (v[0] / lv, v[1] / lv)
        dot = max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1]))
        theta = math.acos(dot)
        if theta < 1e-6:
            continue
        trim = r / math.tan(theta / 2)
        trim = min(trim, lu * 0.45, lv * 0.45)
        p1 = (b[0] + u[0] * trim, b[1] + u[1] * trim)
        p2 = (b[0] + v[0] * trim, b[1] + v[1] * trim)
        outline.append(p1)
        arc = svg_arc_points(p1[0], p1[1], p2[0], p2[1], r, r, 0, False, True, arc_steps)
        outline.extend(arc[1:])
    return outline


def dist_point_seg(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab2 = abx * abx + aby * aby
    if ab2 < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, (apx * abx + apy * aby) / ab2))
    qx, qy = ax + t * abx, ay + t * aby
    return math.hypot(px - qx, py - qy)


def min_distance_polys(v1, v2):
    d = float("inf")
    for x1, y1 in v1:
        for x2, y2 in v2:
            d = min(d, math.hypot(x1 - x2, y1 - y2))
    for poly in (v1, v2):
        other = v2 if poly is v1 else v1
        for x, y in poly:
            for i in range(len(other)):
                ax, ay = other[i]
                bx, by = other[(i + 1) % len(other)]
                d = min(d, dist_point_seg(x, y, ax, ay, bx, by))
    return d


def seg_intersect(a, b, c, d):
    ax, ay = a
    bx, by = b
    cx, cy = c
    dx, dy = d
    den = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
    if abs(den) < 1e-12:
        return False
    t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / den
    u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / den
    return 0 < t < 1 and 0 < u < 1


def point_in_poly(px, py, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-18) + x1):
            inside = not inside
    return inside


def polygons_overlap(v1, v2, gap):
    if min_distance_polys(v1, v2) < gap:
        return True
    n1, n2 = len(v1), len(v2)
    for i in range(n1):
        a, b = v1[i], v1[(i + 1) % n1]
        for j in range(n2):
            c, d = v2[j], v2[(j + 1) % n2]
            if seg_intersect(a, b, c, d):
                return True
    if point_in_poly(v1[0][0], v1[0][1], v2) or point_in_poly(v2[0][0], v2[0][1], v1):
        return True
    return False


def inside_panel(verts, inset):
    for x, y in verts:
        if x < inset or x > PANEL_W - inset or y < inset or y > PANEL_H - inset:
            return False
    return True


def dist_to_rect(verts, x0, y0, x1, y1):
    d = float("inf")
    for x, y in verts:
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        d = min(d, math.hypot(dx, dy))
    rect_edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for i in range(3):
        a, b = verts[i], verts[(i + 1) % 3]
        for c, dpt in rect_edges:
            for px, py in (a, b):
                d = min(d, dist_point_seg(px, py, c[0], c[1], dpt[0], dpt[1]))
            for rcx, rcy in (c, dpt):
                d = min(d, dist_point_seg(rcx, rcy, a[0], a[1], b[0], b[1]))
    return d


def pads_slot_edge_thetas() -> tuple[float, float]:
    r = PADS_R_OUT
    dx_l = PADS_SLOT_X_LEFT - PADS_CX
    dx_r = PADS_SLOT_X_RIGHT - PADS_CX
    y_l = -math.sqrt(max(r * r - dx_l * dx_l, 0.0))
    y_r = -math.sqrt(max(r * r - dx_r * dx_r, 0.0))
    return math.atan2(y_l, dx_l), math.atan2(y_r, dx_r)


def pads_back_u_band() -> tuple[float, float]:
    """Unwrap u range for the +Y back face (opposite pad slot)."""
    th_l, th_r = pads_slot_edge_thetas()
    u_center = SLOT_LEFT + SLOT_WIDTH * (math.pi / 2 - th_l) / (th_r - th_l)
    half_w = 36.0
    u0 = max(EDGE_INSET, u_center - half_w)
    u1 = min(PANEL_W - EDGE_INSET, u_center + half_w)
    return u0, u1


def _try_place(
    sharp_placed: list[dict],
    gap_rect: tuple[float, float, float, float] | None,
    cx: float,
    cy: float,
    side: float,
    angle: float,
    min_gap: float,
) -> bool:
    verts = tri_vertices_sharp(side, cx, cy, angle)
    if not inside_panel(verts, EDGE_INSET):
        return False
    if gap_rect and dist_to_rect(verts, *gap_rect) < min_gap:
        return False
    if any(polygons_overlap(verts, p["verts"], min_gap) for p in sharp_placed):
        return False
    sharp_placed.append({"side": side, "angle": angle, "cx": cx, "cy": cy, "verts": verts})
    return True


def pack_placements(
    seed: int,
    gap_rect: tuple[float, float, float, float] | None,
    *,
    region_u: tuple[float, float] | None = None,
    region_v: tuple[float, float] | None = None,
    exclude_u: tuple[float, float] | None = None,
    max_new: int | None = None,
    existing: list[dict] | None = None,
    min_gap: float = MIN_GAP,
) -> list[dict]:
    random.seed(seed)
    if existing is not None:
        sharp_placed = existing
    else:
        sharp_placed = []
    start_len = len(sharp_placed)
    target_add = max_new if max_new is not None else None
    attempts = 0
    while attempts < 150000:
        if target_add is not None and len(sharp_placed) - start_len >= target_add:
            break
        if target_add is None and attempts >= 150000:
            break
        attempts += 1
        side = random.uniform(MIN_SIDE, MAX_SIDE)
        angle = random.uniform(0, 360)
        h = side * math.sqrt(3) / 2
        half = max(side, h) / 2 + EDGE_INSET
        if half * 2 > min(PANEL_W, PANEL_H):
            continue
        if region_u:
            cx = random.uniform(max(region_u[0] + half, half), min(region_u[1] - half, PANEL_W - half))
        else:
            cx = random.uniform(half, PANEL_W - half)
        if region_v:
            cy = random.uniform(max(region_v[0] + half, half), min(region_v[1] - half, PANEL_H - half))
        else:
            cy = random.uniform(half, PANEL_H - half)
        if region_u and not (region_u[0] <= cx <= region_u[1]):
            continue
        if region_v and not (region_v[0] <= cy <= region_v[1]):
            continue
        if exclude_u and exclude_u[0] <= cx <= exclude_u[1]:
            continue
        _try_place(sharp_placed, gap_rect, cx, cy, side, angle, min_gap)

    return sharp_placed


def _place_at_seeds(
    sharp_placed: list[dict],
    gap_rect: tuple[float, float, float, float] | None,
    seeds: tuple[tuple[float, float], ...],
) -> int:
    added = 0
    for cx, cy in seeds:
        for side in (6.5, 8.0, 9.5, 11.0):
            for angle in range(0, 360, 22):
                if _try_place(sharp_placed, gap_rect, cx, cy, side, angle, MIN_GAP):
                    added += 1
                    break
            else:
                continue
            break
    return added


def _drop_highest_u(sharp_placed: list[dict], count: int) -> None:
    """Make room for seam vents by removing holes on the outer unwrap edge."""
    sharp_placed.sort(key=lambda p: p["cx"], reverse=True)
    del sharp_placed[:count]


def outlines_from_sharp(sharp_placed: list[dict]) -> list[list[tuple[float, float]]]:
    holes = []
    for p in sharp_placed:
        r = corner_radius(p["side"])
        holes.append(rounded_triangle_outline(p["side"], p["cx"], p["cy"], p["angle"], r))
    return holes


def sticks_holes() -> list[list[tuple[float, float]]]:
    sharp = pack_placements(42, None)
    _drop_highest_u(sharp, 2)
    _place_at_seeds(sharp, None, STICKS_SEAM_SEEDS)
    pack_placements(
        103,
        None,
        region_u=STICKS_SEAM_U,
        region_v=STICKS_SEAM_V,
        max_new=1,
        existing=sharp,
    )
    return outlines_from_sharp(sharp)


def pads_holes() -> list[list[tuple[float, float]]]:
    gap = (PADS_GAP_U0, 0.0, PADS_GAP_U1, PANEL_H)
    u0, u1 = pads_back_u_band()
    # Main pattern on sides/front; back (+Y) filled in a second pass.
    sharp = pack_placements(42, gap, exclude_u=(u0, u1))
    pack_placements(
        99,
        gap,
        region_u=(u0, u1),
        max_new=PADS_BACK_TARGET,
        existing=sharp,
        min_gap=PADS_BACK_MIN_GAP,
    )
    _drop_highest_u(sharp, 1)
    _place_at_seeds(sharp, gap, PADS_SEAM_SEEDS)
    pack_placements(
        102,
        gap,
        region_u=PADS_SEAM_U,
        region_v=PADS_SEAM_V,
        max_new=PADS_SEAM_TARGET,
        existing=sharp,
    )
    return outlines_from_sharp(sharp)
