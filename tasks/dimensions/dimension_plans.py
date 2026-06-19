"""
dimension_plans.py — Auto-dimensions floor plan views for A102 sheets.

Barnhaus standard:
  Exterior: slab edge to slab edge (overall building extents)
  Sub-dims: where building has jogs/wings, show each leg
  Interior: interior wall face to interior wall face (future)

Reference points: outermost wall endpoint coordinates, not midpoints.
"""

from core import revit_client as rc
from core.project_state import load_state

OFFSET_INNER = 4.0   # ft — first string offset from slab edge
OFFSET_OUTER = 8.0   # ft — overall dimension string offset


def run(state: dict = None, level_key: str = "L1"):
    if state is None:
        state = load_state()

    print(f"\n📐 Dimension plans — {level_key}")

    view = _get_dimension_view(state, level_key)
    if not view:
        print(f"  ❌ No dimension view found")
        return

    view_id = view.get("id")
    print(f"  🎯 View: {view.get('name')} (ID: {view_id})")

    ext_walls = [w for w in state.get("walls", {}).get("exterior", [])
                 if w.get("start_point") and w.get("end_point")]

    if not ext_walls:
        print("  ❌ No wall geometry in state")
        return

    # ── Build envelope from actual wall endpoints (not midpoints) ──────────
    # Collect all endpoint X/Y coords to find true building extents
    all_pts = []
    for w in ext_walls:
        all_pts.append(w["start_point"])
        all_pts.append(w["end_point"])

    min_x = min(p["x"] for p in all_pts)
    max_x = max(p["x"] for p in all_pts)
    min_y = min(p["y"] for p in all_pts)
    max_y = max(p["y"] for p in all_pts)

    print(f"  📐 Slab extents: X({min_x:.2f}→{max_x:.2f}) Y({min_y:.2f}→{max_y:.2f})")
    print(f"      Width: {max_x-min_x:.2f}ft  Depth: {max_y-min_y:.2f}ft")

    placed = 0

    # ── Find the defining walls for each face ──────────────────────────────
    # LEFT face:  vertical wall(s) whose X endpoints are nearest to min_x
    # RIGHT face: vertical wall(s) whose X endpoints are nearest to max_x
    # TOP face:   horizontal wall(s) whose Y endpoints are nearest to max_y
    # BOTTOM face: horizontal wall(s) whose Y endpoints are nearest to min_y

    v_walls = [w for w in ext_walls if _is_vertical(w)]
    h_walls = [w for w in ext_walls if _is_horizontal(w)]

    left_wall   = _wall_nearest_coord(v_walls,   "x", min_x)
    right_wall  = _wall_nearest_coord(v_walls,   "x", max_x)
    top_wall    = _wall_nearest_coord(h_walls,   "y", max_y)
    bottom_wall = _wall_nearest_coord(h_walls,   "y", min_y)

    print(f"  LEFT:   wall {left_wall['id'] if left_wall else 'none'}")
    print(f"  RIGHT:  wall {right_wall['id'] if right_wall else 'none'}")
    print(f"  TOP:    wall {top_wall['id'] if top_wall else 'none'}")
    print(f"  BOTTOM: wall {bottom_wall['id'] if bottom_wall else 'none'}")

    # ── Overall dimensions ─────────────────────────────────────────────────
    dim_pad = 3.0  # extend dimension line past building edge

    # TOP — overall width (E-W), placed above building
    if left_wall and right_wall:
        y_outer = max_y + OFFSET_OUTER
        r = _dim(left_wall["id"], right_wall["id"],
                 min_x - dim_pad, y_outer, max_x + dim_pad, y_outer, view_id)
        if r: placed += 1; print(f"  ✅ TOP overall: {max_x-min_x:.2f}ft")

    # BOTTOM — overall width, placed below building
    if left_wall and right_wall:
        y_outer = min_y - OFFSET_OUTER
        r = _dim(left_wall["id"], right_wall["id"],
                 min_x - dim_pad, y_outer, max_x + dim_pad, y_outer, view_id)
        if r: placed += 1; print(f"  ✅ BOTTOM overall")

    # LEFT — overall depth (N-S), placed left of building
    if top_wall and bottom_wall:
        x_outer = min_x - OFFSET_OUTER
        r = _dim(top_wall["id"], bottom_wall["id"],
                 x_outer, min_y - dim_pad, x_outer, max_y + dim_pad, view_id)
        if r: placed += 1; print(f"  ✅ LEFT overall: {max_y-min_y:.2f}ft")

    # RIGHT — overall depth, placed right of building
    if top_wall and bottom_wall:
        x_outer = max_x + OFFSET_OUTER
        r = _dim(top_wall["id"], bottom_wall["id"],
                 x_outer, min_y - dim_pad, x_outer, max_y + dim_pad, view_id)
        if r: placed += 1; print(f"  ✅ RIGHT overall")

    # ── Sub-dimensions: jogs in the footprint ─────────────────────────────
    # Find any vertical walls whose X is significantly inside the left/right edge
    # These represent jogs or wings — add inner string dimensions
    placed += _place_jog_dims(v_walls, "x", min_x, max_x, min_y, max_y,
                               "horizontal", view_id)
    placed += _place_jog_dims(h_walls, "y", min_y, max_y, min_x, max_x,
                               "vertical", view_id)

    # ── Interior room dimensions ─────────────────────────────────────────
    interior_placed = _place_interior_dims(state, view_id)
    placed += interior_placed

    print(f"\n  ✅ {placed} total dimensions placed in {view.get('name')}")


def _place_jog_dims(walls, coord_axis, edge_min, edge_max, span_min, span_max,
                    dim_direction, view_id):
    """Place inner-string dimensions between walls that jog in from the edge."""
    placed = 0
    edge_tolerance = 1.5  # ft — how close to edge counts as "on the edge"

    # Find walls whose near-edge coordinates form a jog
    edge_walls = []
    for w in walls:
        coords = [w["start_point"][coord_axis], w["end_point"][coord_axis]]
        near_min = any(abs(c - edge_min) <= edge_tolerance for c in coords)
        near_max = any(abs(c - edge_max) <= edge_tolerance for c in coords)
        if near_min or near_max:
            val = min(coords) if near_min else max(coords)
            edge_walls.append((val, w))

    edge_walls.sort(key=lambda x: x[0])

    if len(edge_walls) < 2:
        return 0

    # Place inner string dimensions between adjacent edge walls
    offset = OFFSET_INNER
    for i in range(len(edge_walls) - 1):
        v1, w1 = edge_walls[i]
        v2, w2 = edge_walls[i + 1]
        if abs(v2 - v1) < 1.0:
            continue  # too close, skip

        if dim_direction == "horizontal":
            # Dimension line runs E-W (above the building)
            dim_coord = edge_max + offset if coord_axis == "x" else edge_min - offset
            r = _dim(w1["id"], w2["id"],
                     min(v1,v2) - 1, dim_coord,
                     max(v1,v2) + 1, dim_coord, view_id)
        else:
            # Dimension line runs N-S (left of building)
            dim_coord = edge_min - offset if coord_axis == "y" else edge_max + offset
            r = _dim(w1["id"], w2["id"],
                     dim_coord, min(v1,v2) - 1,
                     dim_coord, max(v1,v2) + 1, view_id)

        if r: placed += 1

    return placed


def _wall_nearest_coord(walls, axis, target):
    """Return the wall whose endpoints are closest to target coord."""
    if not walls:
        return None
    def dist(w):
        coords = [w["start_point"][axis], w["end_point"][axis]]
        return min(abs(c - target) for c in coords)
    return min(walls, key=dist)


def _dim(e1, e2, x0, y0, x1, y1, view_id, face_refs=False):
    r = rc.call("revit.create_dimension", {
        "element1_id":  e1,
        "element2_id":  e2,
        "start_point":  {"x": x0, "y": y0, "z": 0},
        "end_point":    {"x": x1, "y": y1, "z": 0},
        "view_id":      view_id,
        "use_face_refs": face_refs,
    })
    if not r.get("success"):
        err = (r.get("error") or "")[:100]
        if err: print(f"    ⚠️  {err}")
    return r.get("success", False)


def _is_horizontal(wall):
    sp, ep = wall["start_point"], wall["end_point"]
    return abs(ep["x"] - sp["x"]) > abs(ep["y"] - sp["y"])


def _is_vertical(wall):
    return not _is_horizontal(wall)


def _place_interior_dims(state, view_id):
    """Place width + depth dimensions inside every room."""
    # Build wall lookup across all categories
    all_walls = {}
    for cat in ['exterior', 'interior', 'other']:
        for w in state.get('walls', {}).get(cat, []):
            if w.get('start_point') and w.get('end_point'):
                all_walls[w['id']] = w

    rooms = [r for r in state.get('rooms', []) if r.get('area_sf', 0) > 30]
    placed = 0

    for room in rooms:
        bb = room.get('bbox', {})
        if not bb.get('has_bbox'):
            continue

        bb_min = bb['min']
        bb_max = bb['max']
        cx = (bb_min['x'] + bb_max['x']) / 2
        cy = (bb_min['y'] + bb_max['y']) / 2

        bwall_ids = room.get('boundary_wall_ids', [])
        bwalls = [all_walls[wid] for wid in bwall_ids if wid in all_walls]

        h_walls = [w for w in bwalls if _is_horizontal(w)]
        v_walls = [w for w in bwalls if _is_vertical(w)]

        name = room.get('name', 'Room')

        # Width (E-W): between westmost and eastmost vertical boundary walls
        if len(v_walls) >= 2:
            v_sorted = sorted(v_walls,
                key=lambda w: (w['start_point']['x'] + w['end_point']['x']) / 2)
            r = _dim(v_sorted[0]['id'], v_sorted[-1]['id'],
                     bb_min['x'] - 0.5, cy, bb_max['x'] + 0.5, cy, view_id,
                     face_refs=True)
            if r:
                placed += 1
            else:
                # Fallback: try with just 1 wall if 2-wall dim failed
                pass

        # Depth (N-S): between southmost and northmost horizontal boundary walls
        if len(h_walls) >= 2:
            h_sorted = sorted(h_walls,
                key=lambda w: (w['start_point']['y'] + w['end_point']['y']) / 2)
            r = _dim(h_sorted[0]['id'], h_sorted[-1]['id'],
                     cx, bb_min['y'] - 0.5, cx, bb_max['y'] + 0.5, view_id,
                     face_refs=True)
            if r:
                placed += 1

    print(f"  ROOMS: {placed} interior dimensions ({len(rooms)} rooms)")
    return placed


def _get_dimension_view(state, level_key):
    kw = {"L1": ["level 1","l1","first","f1"], "L2": ["level 2","l2","second","f2"]}.get(level_key,[])
    views = state.get("views", {}).get("floor_plans", [])
    for v in views:
        n = v.get("name","").lower()
        if any(k in n for k in kw) and "dim" in n:
            return v
    for v in views:
        n = v.get("name","").lower()
        if any(k in n for k in kw):
            return v
    return None
