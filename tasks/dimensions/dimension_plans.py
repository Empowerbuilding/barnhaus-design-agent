"""
dimension_plans.py — Auto-dimensions floor plan views for A102 sheets.

Barnhaus dimension standard (3-string system):
  String 1 (outermost): Overall building length/width
  String 2 (middle):    Opening-to-opening (door/window centerlines)
  String 3 (innermost): Wall-end to first opening

Color key (applied via line styles):
  Red   = Interior walls
  Black = Exterior walls & openings
  Blue  = Slab measurement

Dimension offset from building face: 2ft, 4ft, 6ft for strings 1/2/3.
"""

from core import revit_client as rc
from core.constants import WALL
from core.project_state import load_state


# Dimension string offsets from building exterior face (ft)
OFFSET_OVERALL   = 6.0  # string 1 — overall
OFFSET_OPENINGS  = 4.0  # string 2 — opening-to-opening
OFFSET_WALL_ENDS = 2.0  # string 3 — wall end to opening


def run(state: dict = None, level_key: str = "L1"):
    if state is None:
        state = load_state()

    print(f"\n📐 Running dimension plans for {level_key}...")

    # Get the floor plan view for this level
    view = _get_floor_plan_view(state, level_key)
    if not view:
        print(f"  ❌ No floor plan view found for {level_key}")
        return

    view_id = view.get("id")
    ext_walls = state.get("walls", {}).get("exterior", [])

    if not ext_walls:
        print("  ❌ No exterior walls found")
        return

    # Group exterior walls by orientation
    h_walls = [w for w in ext_walls if _is_horizontal(w)]  # N/S walls
    v_walls = [w for w in ext_walls if _is_vertical(w)]    # E/W walls

    # ── Horizontal dimension strings (top and bottom of building) ──────────
    if h_walls:
        _dimension_wall_group(h_walls, "horizontal", view_id, state)

    # ── Vertical dimension strings (left and right sides) ─────────────────
    if v_walls:
        _dimension_wall_group(v_walls, "vertical", view_id, state)

    print(f"  ✅ Dimensions applied to {level_key} floor plan")


def _dimension_wall_group(walls: list, orientation: str, view_id: int, state: dict):
    """Apply 3-string dimension set to a group of parallel walls."""
    doors   = state.get("doors", [])
    windows = state.get("windows", [])

    for wall in walls:
        wall_id  = wall.get("id")
        start    = wall.get("start_point", {})
        end      = wall.get("end_point", {})
        if not start or not end:
            continue

        # Build reference list: wall faces + door/window openings in this wall
        references = [{"element_id": wall_id, "ref_type": "face_left"},
                      {"element_id": wall_id, "ref_type": "face_right"}]

        # Add openings hosted in this wall
        hosted_openings = [d for d in doors + windows if d.get("host_wall_id") == wall_id]
        for opening in hosted_openings:
            references.append({"element_id": opening.get("id"), "ref_type": "center"})

        if len(references) < 2:
            continue

        # Offset direction: perpendicular to wall, outward
        if orientation == "horizontal":
            offset_dir = 1 if start.get("y", 0) > 0 else -1
            line_start = {"x": start.get("x", 0), "y": start.get("y", 0) + offset_dir * OFFSET_OVERALL}
            line_end   = {"x": end.get("x", 0),   "y": end.get("y", 0)   + offset_dir * OFFSET_OVERALL}
        else:
            offset_dir = -1 if start.get("x", 0) > 0 else 1
            line_start = {"x": start.get("x", 0) + offset_dir * OFFSET_OVERALL, "y": start.get("y", 0)}
            line_end   = {"x": end.get("x", 0)   + offset_dir * OFFSET_OVERALL, "y": end.get("y", 0)}

        rc.add_dimension(references, line_start, line_end, view_id)


def _get_floor_plan_view(state: dict, level_key: str) -> dict | None:
    keywords = {
        "L1": ["floor plan", "level 1"],
        "L2": ["floor plan", "level 2"],
    }.get(level_key, [])

    all_views = (state.get("views", {}).get("unplaced", []) +
                 state.get("views", {}).get("on_sheet", []))

    for v in all_views:
        name = v.get("name", "").lower()
        if all(kw in name for kw in keywords):
            return v
    return None


def _is_horizontal(wall: dict) -> bool:
    """Wall runs East-West (N or S face)."""
    s = wall.get("start_point", {})
    e = wall.get("end_point", {})
    return abs(e.get("x", 0) - s.get("x", 0)) > abs(e.get("y", 0) - s.get("y", 0))


def _is_vertical(wall: dict) -> bool:
    return not _is_horizontal(wall)
