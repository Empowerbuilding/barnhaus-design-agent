"""
dimension_plans.py — Auto-dimensions floor plan views for A102 sheets.

3-string exterior dimension system (Barnhaus standard):
  String 1 (4ft out):  Individual wall segments / opening locations
  String 2 (7ft out):  Sub-group totals
  String 3 (10ft out): Overall building dimension

Building footprint determined from ROOMS bounding box (not walls),
so outer roof/site boundary rectangles don't throw off placement.
"""

from core import revit_client as rc
from core.project_state import load_state

# Offsets from building edge (ft)
OFFSET_SEGMENTS = 4.0   # string 1 — individual segments
OFFSET_SUBTOTAL = 7.0   # string 2 — sub-totals  
OFFSET_OVERALL  = 10.0  # string 3 — overall


def run(state: dict = None, level_key: str = "L1"):
    if state is None:
        state = load_state()

    print(f"\n📐 Dimension plans — {level_key}")

    view = _get_dimension_view(state, level_key)
    if not view:
        print(f"  ❌ No dimension view found for {level_key}")
        print(f"     Views: {[v.get('name') for v in state.get('views', {}).get('floor_plans', [])]}")
        return

    view_id = view.get("id")
    print(f"  🎯 View: {view.get('name')} (ID: {view_id})")

    # ── Get building footprint from ROOMS (not walls) ───────────────────────
    footprint = _get_building_footprint(state)
    if not footprint:
        print("  ❌ No rooms found — can't determine building footprint")
        return

    min_x, max_x, min_y, max_y = footprint
    print(f"  📐 Footprint: X({min_x:.1f}→{max_x:.1f}) Y({min_y:.1f}→{max_y:.1f})")

    # ── Get walls with geometry ──────────────────────────────────────────────
    ext_walls = state.get("walls", {}).get("exterior", [])
    walls_with_geo = [w for w in ext_walls if w.get("start_point") and w.get("end_point")]

    if not walls_with_geo:
        print("  ❌ No wall geometry — run scan with latest bridge")
        return

    # Filter to walls actually within the building footprint (exclude outer boundary)
    building_walls = _filter_building_walls(walls_with_geo, footprint)
    print(f"  🧱 {len(building_walls)} building walls (of {len(walls_with_geo)} exterior)")

    h_walls = sorted([w for w in building_walls if _is_horizontal(w)],
                     key=lambda w: (w["start_point"]["y"] + w["end_point"]["y"]) / 2)
    v_walls = sorted([w for w in building_walls if _is_vertical(w)],
                     key=lambda w: (w["start_point"]["x"] + w["end_point"]["x"]) / 2)

    placed = 0

    # ── TOP (north side) ────────────────────────────────────────────────────
    placed += _dimension_side("TOP",    v_walls, h_walls, "north", footprint, view_id)

    # ── BOTTOM (south side) ─────────────────────────────────────────────────
    placed += _dimension_side("BOTTOM", v_walls, h_walls, "south", footprint, view_id)

    # ── LEFT (west side) ────────────────────────────────────────────────────
    placed += _dimension_side("LEFT",   h_walls, v_walls, "west",  footprint, view_id)

    # ── RIGHT (east side) ───────────────────────────────────────────────────
    placed += _dimension_side("RIGHT",  h_walls, v_walls, "east",  footprint, view_id)

    print(f"\n  ✅ {placed} dimension strings placed in {view.get('name')}")


def _dimension_side(label, span_walls, depth_walls, side, footprint, view_id):
    """
    Place 3 dimension strings on one side of the building.
    span_walls  = walls that run parallel to this side (vary in depth direction)
    depth_walls = walls that run perpendicular to this side (span across)
    side        = 'north' | 'south' | 'east' | 'west'
    """
    min_x, max_x, min_y, max_y = footprint
    placed = 0

    if not depth_walls or len(depth_walls) < 2:
        return 0

    is_horizontal_side = side in ("north", "south")  # dimension line runs E-W or N-S

    if is_horizontal_side:
        # Dimension line runs E-W, positioned above (north) or below (south)
        sign = 1 if side == "north" else -1
        base = max_y if side == "north" else min_y
        line_x0 = min_x - 3
        line_x1 = max_x + 3

        # String 3 — overall (outermost)
        if len(depth_walls) >= 2:
            w1 = depth_walls[0]
            w2 = depth_walls[-1]
            dim_y = base + sign * OFFSET_OVERALL
            r = _place_dim(w1["id"], w2["id"],
                           {"x": line_x0, "y": dim_y, "z": 0},
                           {"x": line_x1, "y": dim_y, "z": 0}, view_id)
            if r: placed += 1

        # String 1 — segments (innermost, one dim per adjacent wall pair)
        dim_y = base + sign * OFFSET_SEGMENTS
        for i in range(len(depth_walls) - 1):
            w1 = depth_walls[i]
            w2 = depth_walls[i + 1]
            mid1 = (w1["start_point"]["x"] + w1["end_point"]["x"]) / 2
            mid2 = (w2["start_point"]["x"] + w2["end_point"]["x"]) / 2
            if abs(mid2 - mid1) < 0.5: continue
            r = _place_dim(w1["id"], w2["id"],
                           {"x": min(mid1, mid2) - 1, "y": dim_y, "z": 0},
                           {"x": max(mid1, mid2) + 1, "y": dim_y, "z": 0}, view_id)
            if r: placed += 1

    else:
        # Dimension line runs N-S, positioned left (west) or right (east)
        sign = -1 if side == "west" else 1
        base = min_x if side == "west" else max_x
        line_y0 = min_y - 3
        line_y1 = max_y + 3

        # String 3 — overall
        if len(depth_walls) >= 2:
            w1 = depth_walls[0]
            w2 = depth_walls[-1]
            dim_x = base + sign * OFFSET_OVERALL
            r = _place_dim(w1["id"], w2["id"],
                           {"x": dim_x, "y": line_y0, "z": 0},
                           {"x": dim_x, "y": line_y1, "z": 0}, view_id)
            if r: placed += 1

        # String 1 — segments
        dim_x = base + sign * OFFSET_SEGMENTS
        for i in range(len(depth_walls) - 1):
            w1 = depth_walls[i]
            w2 = depth_walls[i + 1]
            mid1 = (w1["start_point"]["y"] + w1["end_point"]["y"]) / 2
            mid2 = (w2["start_point"]["y"] + w2["end_point"]["y"]) / 2
            if abs(mid2 - mid1) < 0.5: continue
            r = _place_dim(w1["id"], w2["id"],
                           {"x": dim_x, "y": min(mid1, mid2) - 1, "z": 0},
                           {"x": dim_x, "y": max(mid1, mid2) + 1, "z": 0}, view_id)
            if r: placed += 1

    print(f"  {label}: {placed} strings")
    return placed


def _place_dim(e1_id, e2_id, start, end, view_id):
    result = rc.call("revit.create_dimension", {
        "element1_id": e1_id,
        "element2_id": e2_id,
        "start_point": start,
        "end_point":   end,
        "view_id":     view_id,
    })
    if not result.get("success"):
        err = (result.get("error") or "")[:80]
        if err:
            print(f"    ⚠️  {err}")
    return result.get("success", False)


def _get_building_footprint(state: dict):
    """Get building XY footprint from rooms bounding box."""
    rooms = state.get("rooms", [])
    valid = [r for r in rooms if r.get("area_sf", 0) > 10]
    if not valid:
        return None

    xs, ys = [], []
    for r in valid:
        bb = r.get("bounding_box") or r.get("bbox")
        if bb:
            xs += [bb.get("min_x", 0), bb.get("max_x", 0)]
            ys += [bb.get("min_y", 0), bb.get("max_y", 0)]
        elif r.get("x") and r.get("y"):
            xs.append(r["x"])
            ys.append(r["y"])

    if not xs:
        # Fallback: use wall midpoints to estimate footprint
        ext_walls = state.get("walls", {}).get("exterior", [])
        for w in ext_walls:
            mp = w.get("midpoint")
            if mp:
                xs.append(mp["x"])
                ys.append(mp["y"])

    if not xs:
        return None

    return min(xs), max(xs), min(ys), max(ys)


def _filter_building_walls(walls, footprint):
    """Remove walls outside the building footprint (outer boundary rectangle)."""
    min_x, max_x, min_y, max_y = footprint
    margin = 5.0  # allow 5ft margin beyond room bbox

    result = []
    for w in walls:
        sp = w["start_point"]
        ep = w["end_point"]
        # Wall midpoint must be within footprint + margin
        mx = (sp["x"] + ep["x"]) / 2
        my = (sp["y"] + ep["y"]) / 2
        if (min_x - margin <= mx <= max_x + margin and
                min_y - margin <= my <= max_y + margin):
            result.append(w)
    return result


def _get_dimension_view(state: dict, level_key: str) -> dict | None:
    keywords = {
        "L1": ["level 1", "l1", "first", "f1", "floor plan f1", "dimension plan f1"],
        "L2": ["level 2", "l2", "second", "f2"],
    }.get(level_key, [])

    floor_plans = state.get("views", {}).get("floor_plans", [])

    # Prefer dimension-specific views
    for v in floor_plans:
        name = v.get("name", "").lower()
        if any(kw in name for kw in keywords) and "dim" in name:
            return v

    # Fallback: any matching level
    for v in floor_plans:
        name = v.get("name", "").lower()
        if any(kw in name for kw in keywords):
            return v

    return None


def _is_horizontal(wall: dict) -> bool:
    s = wall.get("start_point", {})
    e = wall.get("end_point", {})
    return abs(e.get("x", 0) - s.get("x", 0)) > abs(e.get("y", 0) - s.get("y", 0))


def _is_vertical(wall: dict) -> bool:
    return not _is_horizontal(wall)
