"""
dimension_plans.py — Auto-dimensions floor plan views for A102 sheets.

Barnhaus dimension standard (3-string system):
  String 1 (outermost): Overall building length/width
  String 2 (middle):    Opening-to-opening (door/window centerlines)  
  String 3 (innermost): Wall-end to wall-end segments

Uses revit.create_dimension bridge tool.
"""

from core import revit_client as rc
from core.project_state import load_state

# Offset from building edge for each dimension string (ft)
OFFSET_S1 = 8.0   # overall
OFFSET_S2 = 5.0   # openings
OFFSET_S3 = 2.5   # wall ends


def run(state: dict = None, level_key: str = "L1"):
    if state is None:
        state = load_state()

    print(f"\n📐 Running dimension plans for {level_key}...")

    view = _get_dimension_view(state, level_key)
    if not view:
        print(f"  ❌ No dimension view found for {level_key}")
        print(f"     Available floor plans: {[v.get('name') for v in state.get('views', {}).get('floor_plans', [])]}")
        return

    view_id = view.get("id")
    print(f"  🎯 View: {view.get('name')} (ID: {view_id})")

    ext_walls = state.get("walls", {}).get("exterior", [])
    walls_with_geo = [w for w in ext_walls if w.get("start_point") and w.get("end_point")]

    if not walls_with_geo:
        print("  ❌ No wall geometry in state — run scan first with latest bridge")
        return

    print(f"  📏 {len(walls_with_geo)} exterior walls with geometry")

    h_walls = [w for w in walls_with_geo if _is_horizontal(w)]  # N/S walls (run E-W)
    v_walls = [w for w in walls_with_geo if _is_vertical(w)]    # E/W walls (run N-S)

    placed = 0

    # ── Overall E-W dimension (across top) ──────────────────────────────────
    if v_walls:
        result = _place_overall_dimension(v_walls, "vertical", view_id)
        if result:
            placed += 1
            print(f"  ✅ Overall E-W: {result}")

    # ── Overall N-S dimension (down the side) ────────────────────────────────
    if h_walls:
        result = _place_overall_dimension(h_walls, "horizontal", view_id)
        if result:
            placed += 1
            print(f"  ✅ Overall N-S: {result}")

    # ── Wall-to-wall segment dimensions ─────────────────────────────────────
    if v_walls:
        placed += _place_segment_dimensions(v_walls, "vertical", view_id)

    if h_walls:
        placed += _place_segment_dimensions(h_walls, "horizontal", view_id)

    if placed == 0:
        print("  ❌ No dimensions placed — bridge returned errors on all attempts")
        print("     Check that the dimension view is open/accessible in Revit")
    else:
        print(f"\n  ✅ {placed} dimension strings placed in {view.get('name')}")


def _place_overall_dimension(walls: list, orientation: str, view_id: int):
    """Place one overall dimension across the full building extent."""
    if orientation == "vertical":
        # Walls run N-S — measure E-W extent
        # Find westmost and eastmost walls by their X midpoints
        sorted_walls = sorted(walls, key=lambda w: (w["start_point"]["x"] + w["end_point"]["x"]) / 2)
    else:
        # Walls run E-W — measure N-S extent
        sorted_walls = sorted(walls, key=lambda w: (w["start_point"]["y"] + w["end_point"]["y"]) / 2)

    if len(sorted_walls) < 2:
        return None

    wall1 = sorted_walls[0]   # min
    wall2 = sorted_walls[-1]  # max

    # Find bounding box of all walls to position the dimension line
    all_x = [w["start_point"]["x"] for w in walls] + [w["end_point"]["x"] for w in walls]
    all_y = [w["start_point"]["y"] for w in walls] + [w["end_point"]["y"] for w in walls]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    if orientation == "vertical":
        # Dimension line runs N-S, placed above (north) of building
        dim_y = max_y + OFFSET_S1
        line_start = {"x": min_x - 2, "y": dim_y, "z": 0}
        line_end   = {"x": max_x + 2, "y": dim_y, "z": 0}
    else:
        # Dimension line runs E-W, placed to the left (west) of building
        dim_x = min_x - OFFSET_S1
        line_start = {"x": dim_x, "y": min_y - 2, "z": 0}
        line_end   = {"x": dim_x, "y": max_y + 2, "z": 0}

    result = rc.call("revit.create_dimension", {
        "element1_id": wall1["id"],
        "element2_id": wall2["id"],
        "start_point": line_start,
        "end_point":   line_end,
        "view_id":     view_id,
    })

    if result.get("success"):
        data = result.get("result", {})
        return data.get("value_string", "placed")
    else:
        print(f"    ⚠️  Overall {orientation} failed: {result.get('error', 'unknown error')}")
        return None


def _place_segment_dimensions(walls: list, orientation: str, view_id: int):
    """Place segment-to-segment dimensions between adjacent parallel walls."""
    placed = 0

    if orientation == "vertical":
        sorted_walls = sorted(walls, key=lambda w: (w["start_point"]["x"] + w["end_point"]["x"]) / 2)
        all_y = [w["start_point"]["y"] for w in walls] + [w["end_point"]["y"] for w in walls]
        dim_y = max(all_y) + OFFSET_S2
    else:
        sorted_walls = sorted(walls, key=lambda w: (w["start_point"]["y"] + w["end_point"]["y"]) / 2)
        all_x = [w["start_point"]["x"] for w in walls] + [w["end_point"]["x"] for w in walls]
        dim_x = min(all_x) - OFFSET_S2

    for i in range(len(sorted_walls) - 1):
        w1 = sorted_walls[i]
        w2 = sorted_walls[i + 1]

        if orientation == "vertical":
            x1 = (w1["start_point"]["x"] + w1["end_point"]["x"]) / 2
            x2 = (w2["start_point"]["x"] + w2["end_point"]["x"]) / 2
            if abs(x2 - x1) < 0.5:
                continue  # Too close, skip
            line_start = {"x": x1, "y": dim_y, "z": 0}
            line_end   = {"x": x2, "y": dim_y, "z": 0}
        else:
            y1 = (w1["start_point"]["y"] + w1["end_point"]["y"]) / 2
            y2 = (w2["start_point"]["y"] + w2["end_point"]["y"]) / 2
            if abs(y2 - y1) < 0.5:
                continue
            line_start = {"x": dim_x, "y": y1, "z": 0}
            line_end   = {"x": dim_x, "y": y2, "z": 0}

        result = rc.call("revit.create_dimension", {
            "element1_id": w1["id"],
            "element2_id": w2["id"],
            "start_point": line_start,
            "end_point":   line_end,
            "view_id":     view_id,
        })

        if result.get("success"):
            placed += 1
        else:
            print(f"    ⚠️  Segment dim failed: {result.get('error', '')[:60]}")

    return placed


def _get_dimension_view(state: dict, level_key: str) -> dict | None:
    keywords = {
        "L1": ["level 1", "l1", "first", "f1"],
        "L2": ["level 2", "l2", "second", "f2"],
    }.get(level_key, [])

    floor_plans = state.get("views", {}).get("floor_plans", [])

    # Prefer views with "dimension" or "dim" in the name
    for v in floor_plans:
        name = v.get("name", "").lower()
        if any(kw in name for kw in keywords):
            if "dim" in name:
                return v

    # Fallback: any matching level view
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
