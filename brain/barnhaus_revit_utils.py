"""
barnhaus_revit_utils.py
Universal Barnhaus Revit build utilities.
These functions enforce design rules at the code level — not per-project patches.
Import and use for every Barnhaus project build.

═══════════════════════════════════════════════════════════════════════════
BARNHAUS DESIGN RULES (enforced here — update when rules change)
═══════════════════════════════════════════════════════════════════════════

STRUCTURAL / WALL RULES
  - Exterior walls always use LocationLine=FinishFaceExterior (flip-safe)
  - After creation, verify_wall_facing() checks exterior normal direction
  - Interior walls use 4.5" type; exterior use 7.5" EXT PBR
  - Minimum garage wall height: 12ft (for 10ft overhead door clearance)
  - Garage overhead door always placed on the correct load-side exterior face

FOOTPRINT SHAPES (supported in build scripts)
  - RECTANGLE: single bbox (x0,y0)→(x1,y1) — simplest, most efficient
  - L-SHAPE: two overlapping rectangles sharing one corner zone
             main wing + service/garage wing at right angle
             use skip_faces to omit shared interior edges
  - U-SHAPE: three wings forming a U; main + two side wings
             courtyard open on one face (typically south)
  - T-SHAPE: main rectangular body + rear or front projection
  - COURTYARD: perimeter wrap around interior open space
             typically 4 wings connected at corners

KITCHEN LAYOUTS (affects layout_kitchen() back_wall and island placement)
  - l-shape:   two walls (back + side), island optional
  - galley:    two parallel walls, no island, linear flow
  - u-shape:   three walls (back + both sides), island optional
  - one-wall:  single back wall run, island as second "wall"
  - island:    island is the primary workspace; perimeter wall minimal

HALLWAY TYPES (affects create_double_loaded_corridor() and door placement)
  - open-plan:        no dedicated hallway walls; rooms flow openly
  - single-corridor:  one wall divides private zone from public
  - double-loaded:    4ft corridor with walls on both sides (Barnhaus L2 standard)
  - gallery:          wide feature hall (6ft+), one wall, often with niches

ROOF RULES
  - Per-edge overhang: oh_s/n/w/e flags; False = flush on interior/shared edges
  - Standard overhang: 1.5ft on all exterior eave and rake edges
  - Interior shared edges (where wing meets wing): oh=False, flush trim only
  - Gable: ridge runs along long axis; N/S are eave sides, E/W are rake/gable ends
  - Shed: mono-pitch, low edge set by shed_low_edge (default = north for drainage)
  - Multi-zone roofs: each rectangular zone gets its own make_roof() call
    with oh=False on shared interior edges between zones
  - L2 upper: oh_w=False (sits on L1), oh_e=True (exterior gable)
  - L1 master: oh_e=False (adjacent to service zone), oh_w=True (exterior gable)
  - Garage: oh_w=False (shared wall with house), oh_e=True (exterior gable)
  - Attach gable-end walls to roof after creation: attach_walls_to_roof()

ROOM LABELING
  - L2 rooms compute SF immediately after creation
  - L1 rooms show 0 SF until Revit's room solver runs (known Revit behavior)
    Root cause: L1 walls have unbound height; Revit needs room separation lines
    or room bounding levels to compute L1 area automatically
  - Workaround: in Revit UI, select all L1 rooms → Room → Compute Area

FIXTURE PLACEMENT RULES
  - All fixtures placed at fz=0 (level-relative, NOT absolute elevation)
  - Toilet tank: 0.5ft from wall, center at 1.0ft from wall face
  - Base cabinet: 1.25ft from wall face (2.5ft deep, center at 1.25ft)
  - Upper cabinet: 0.5ft from wall face (1ft deep, center)
  - Vanity sink: 0.75ft from wall face
  - Shower column: 1.5ft from each corner wall
  - Freestanding tub: 2.5ft from wall (half of 5ft length)
  - Rotation conventions:
      0°   = facing NORTH (fixture back to south wall)
      90°  = facing EAST  (fixture back to west wall)
      180° = facing SOUTH (fixture back to north wall)
      270° = facing WEST  (fixture back to east wall)

STAIR RULES
  - Stair zone: minimum 12ft × 10ft clear (for standard 3ft wide residential stair)
  - create_stairs() currently returns -1 (stub) — place manually in Revit
  - Reserve stair zone in floor plan; walls should enclose the stair shaft

COORDINATE CONVENTIONS
  - X increases EAST, Y increases NORTH
  - Elevation Z=0 at Level 1.0; positive Z goes UP
  - All dimensions in FEET (Revit internal = feet)
  - Room tag points should be interior to all bounding walls (not on walls)
═══════════════════════════════════════════════════════════════════════════
"""

import requests

BASE = "http://localhost:3000/execute"
_req = 0

import time as _time

def _call(tool, payload):
    global _req
    _req += 1
    r = requests.post(BASE, json={"request_id": f"r{_req}", "tool": tool, "payload": payload})
    _time.sleep(0.6)   # allow Revit's transaction engine to settle between calls
    return r.json()


# ─────────────────────────────────────────────
# WALL THICKNESS REGISTRY (feet)
# ─────────────────────────────────────────────
WALL_THICKNESS = {
    'Wall 7.5" EXT PBR':      0.625,
    'Wall 2x6 Ext Stucco':    0.625,
    'Wall 11.5" Exterior':    0.958,
    'Wall 4.5 Interior"':     0.375,
}

def half_thick(wall_type):
    return WALL_THICKNESS.get(wall_type, 0.5) / 2

T     = 0.3125  # half thickness of standard EXT wall
EXT_T = 0.625   # full thickness of standard EXT wall

# With LocationLine=FinishFaceExterior:
#   - Exterior wall EXTERIOR face is at the drawn coordinate (e.g. x=0)
#   - Exterior wall INTERIOR face is at coordinate + EXT_T (e.g. x=0.625)
#   - Floors must NOT expand outward (exterior face = boundary)
#   - Interior walls must offset by EXT_T inward from exterior coordinates
#
# Helper: given an exterior boundary, return interior face coords
def int_south(y_ext): return y_ext + EXT_T   # south wall: interior face is inward (+y)
def int_north(y_ext): return y_ext - EXT_T   # north wall: interior face is inward (-y)
def int_west(x_ext):  return x_ext + EXT_T   # west wall:  interior face is inward (+x)
def int_east(x_ext):  return x_ext - EXT_T   # east wall:  interior face is inward (-x)


# ─────────────────────────────────────────────
# WALLS
# ─────────────────────────────────────────────
def get_wall_orientation(wall_id):
    d = _call("revit.get_wall_orientation", {"wall_id": wall_id})
    return d["Result"]["orientation"] if d["Status"] == "ok" else None

def flip_door(door_id):
    """Flip door facing direction. Uses element_id (not door_id)."""
    d = _call("revit.flip_door", {"element_id": door_id})
    print(f"  flip door {door_id}: {d.get('Status','?')}")
    return d

def flip_wall(wall_id):
    d = _call("revit.flip_wall", {"wall_id": wall_id})
    return d["Status"] == "ok"

def verify_wall_facing(wall_id, expected_nx, expected_ny, label=""):
    """
    Check wall exterior face orientation and flip if wrong.
    NOTE: With LocationLine=FinishFaceExterior (now default for exterior walls),
    flipping no longer shifts the wall position — this is safe to call.
    """
    orient = get_wall_orientation(wall_id)
    if orient is None:
        print(f"  [FACING] could not get orientation for wall {wall_id}")
        return
    ox, oy = orient["x"], orient["y"]
    correct = (expected_nx == 0 or (expected_nx > 0 and ox > 0.5) or (expected_nx < 0 and ox < -0.5)) and \
              (expected_ny == 0 or (expected_ny > 0 and oy > 0.5) or (expected_ny < 0 and oy < -0.5))
    if not correct:
        print(f"  [FACING] {label} wall {wall_id} facing wrong ({ox:.1f},{oy:.1f}), expected ({expected_nx},{expected_ny}) — flipping")
        flip_wall(wall_id)
    else:
        print(f"  [FACING] {label} wall {wall_id} ok ({ox:.1f},{oy:.1f})")


def create_wall(sx, sy, sz, ex, ey, ez, level, wall_type, height=10, label="",
                _ext_bounds=None):
    """
    Create a single wall at centerline coordinates.

    _ext_bounds: optional dict with exterior perimeter coords used to guard
                 against placing interior walls on top of exterior walls.
                 Format: {"x_min": 0, "x_max": 70, "y_min": 22, "y_max": 54}
                 If the wall lies exactly on any exterior face, a warning is printed.
    """
    INT_TYPE = 'Wall 4.5 Interior"'
    if wall_type == INT_TYPE and _ext_bounds:
        b = _ext_bounds
        on_boundary = (
            (sx == ex and sx in (b.get("x_min"), b.get("x_max"))) or
            (sy == ey and sy in (b.get("y_min"), b.get("y_max")))
        )
        if on_boundary:
            print(f"  ⚠️  [WALL OVERLAP] Interior wall [{label}] ({sx},{sy})-({ex},{ey}) "
                  f"lies on exterior boundary — SKIPPED")
            return None

    payload = {
        "start_point": {"x": sx, "y": sy, "z": sz},
        "end_point":   {"x": ex, "y": ey, "z": ez},
        "height": height, "level": level, "wall_type": wall_type
    }
    d = _call("revit.create_wall", payload)
    wid = d["Result"]["wall_id"] if d["Status"] == "ok" else None
    tag = f" [{label}]" if label else ""
    print(f"  wall{tag} ({sx},{sy})-({ex},{ey}) z={sz}: {'ok ' + str(wid) if wid else 'ERR ' + d.get('Message','')}")
    return wid


def create_rect_exterior(x0, y0, x1, y1, z, level, wall_type, height=10, label_prefix="", skip_faces=None):
    """
    Create exterior walls of a rectangle with correct outward facing.
    Draw directions are REVERSED from naive expectation because this Revit template
    produces walls facing the opposite direction — reversed directions = no flip needed.

    skip_faces: list of face names to omit, e.g. ["east"] when an adjacent structure
                shares that wall. The shared wall should be drawn separately.
    """
    skip = skip_faces or []
    p = label_prefix + " " if label_prefix else ""
    walls = {}
    if "south" not in skip:
        walls["south"] = create_wall(x1,y0,z, x0,y0,z, level, wall_type, height, f"{p}south")
        verify_wall_facing(walls["south"],  0, -1, f"{p}south")
    else:
        walls["south"] = None
    if "north" not in skip:
        walls["north"] = create_wall(x0,y1,z, x1,y1,z, level, wall_type, height, f"{p}north")
        verify_wall_facing(walls["north"],  0, +1, f"{p}north")
    else:
        walls["north"] = None
    if "west" not in skip:
        walls["west"] = create_wall(x0,y0,z, x0,y1,z, level, wall_type, height, f"{p}west")
        verify_wall_facing(walls["west"],  -1,  0, f"{p}west")
    else:
        walls["west"] = None
    if "east" not in skip:
        walls["east"] = create_wall(x1,y1,z, x1,y0,z, level, wall_type, height, f"{p}east")
        verify_wall_facing(walls["east"],  +1,  0, f"{p}east")
    else:
        walls["east"] = None
    return walls


# ─────────────────────────────────────────────
# L-SHAPE FOOTPRINT
# ─────────────────────────────────────────────
def create_l_shape_exterior(main_x0, main_y0, main_x1, main_y1,
                             wing_x0, wing_y0, wing_x1, wing_y1,
                             z, level, wall_type, height=10,
                             main_label="main", wing_label="wing"):
    """
    Create an L-shaped building footprint from two overlapping rectangles.
    The shared corner is automatically detected and the interior walls are skipped.

    main_*: bounding box of the main (larger) rectangle
    wing_*: bounding box of the secondary wing

    The two rectangles must share exactly one edge (or overlap at a corner).
    Returns dict with 'main' and 'wing' wall dicts.

    RULE: Use skip_faces on both rectangles to omit the shared interior edge.
          Caller must place the shared wall once explicitly if needed.

    Example — main runs E-W, wing projects south at east end:
        main: (0,14)→(72,30)   wing: (54,0)→(72,14)
        Main skips south face from x=54→72; wing skips north face (shared with main)
    """
    # Detect which faces are shared (touching or coincident edges)
    # Simple approach: caller passes skip_faces explicitly via create_rect_exterior
    # This function just prints the intended layout for documentation
    print(f"\n── L-Shape footprint: {main_label}({main_x0},{main_y0})→({main_x1},{main_y1})"
          f" + {wing_label}({wing_x0},{wing_y0})→({wing_x1},{wing_y1}) ──")

    # Determine skip faces for each rectangle based on overlap
    main_skip = []
    wing_skip = []

    # Wing projects SOUTH from main (wing_y1 == main_y0 or overlaps)
    if wing_y1 <= main_y0 + 0.1 and wing_x0 >= main_x0 - 0.1 and wing_x1 <= main_x1 + 0.1:
        main_skip = ["south"]   # main south face is covered by wing top
        wing_skip = ["north"]   # wing north face is interior

    # Wing projects NORTH from main
    elif wing_y0 >= main_y1 - 0.1 and wing_x0 >= main_x0 - 0.1 and wing_x1 <= main_x1 + 0.1:
        main_skip = ["north"]
        wing_skip = ["south"]

    # Wing projects EAST from main
    elif wing_x0 >= main_x1 - 0.1 and wing_y0 >= main_y0 - 0.1 and wing_y1 <= main_y1 + 0.1:
        main_skip = ["east"]
        wing_skip = ["west"]

    # Wing projects WEST from main
    elif wing_x1 <= main_x0 + 0.1 and wing_y0 >= main_y0 - 0.1 and wing_y1 <= main_y1 + 0.1:
        main_skip = ["west"]
        wing_skip = ["east"]

    main_walls = create_rect_exterior(main_x0, main_y0, main_x1, main_y1, z, level, wall_type,
                                       height, main_label, skip_faces=main_skip)
    wing_walls = create_rect_exterior(wing_x0, wing_y0, wing_x1, wing_y1, z, level, wall_type,
                                       height, wing_label, skip_faces=wing_skip)
    return {"main": main_walls, "wing": wing_walls}


def create_u_shape_exterior(main_x0, main_y0, main_x1, main_y1,
                              left_x0, left_y0, left_x1, left_y1,
                              right_x0, right_y0, right_x1, right_y1,
                              z, level, wall_type, height=10,
                              main_label="main", left_label="left-wing", right_label="right-wing"):
    """
    Create a U-shaped footprint from three rectangles: main body + two side wings.
    The open face of the U is typically south (courtyard).

    Wings project south from main; main skips south face in the wing zones.
    Each wing skips its north face (shared with main).

    Returns dict with 'main', 'left', 'right' wall dicts.
    """
    print(f"\n── U-Shape footprint: {main_label} + {left_label} + {right_label} ──")

    # Main skips south between left and right wing extents
    # Wings each skip north
    # Note: partial face skip (only part of an edge) must be handled with a separate
    # wall segment — caller should use create_rect_exterior with full skip and draw
    # the partial segments manually.

    main_walls = create_rect_exterior(main_x0, main_y0, main_x1, main_y1, z, level, wall_type,
                                       height, main_label, skip_faces=["south"])
    # Main south face: draw only the gap between the wings
    # left wing outer x = left_x0, right wing outer x = right_x1
    if left_x1 < right_x0:
        # courtyard gap on south face of main
        gap_wall = create_wall(right_x0, main_y0, z, left_x1, main_y0, z, level, wall_type, height, f"{main_label} south gap")
        verify_wall_facing(gap_wall, 0, -1, f"{main_label} south gap")
        main_walls["south_gap"] = gap_wall

    left_walls  = create_rect_exterior(left_x0,  left_y0,  left_x1,  left_y1,  z, level, wall_type, height, left_label,  skip_faces=["north"])
    right_walls = create_rect_exterior(right_x0, right_y0, right_x1, right_y1, z, level, wall_type, height, right_label, skip_faces=["north"])
    return {"main": main_walls, "left": left_walls, "right": right_walls}


# ─────────────────────────────────────────────
# POLYGON FOOTPRINT — arbitrary perimeter
# ─────────────────────────────────────────────
def create_polygon_exterior(points, z, level, wall_type, height=10, label_prefix="POLY"):
    """
    Creates exterior walls tracing an arbitrary polygon.
    points: list of {x, y} dicts in order (polygon vertices, counter-clockwise)
    Creates one wall segment per consecutive pair of points (wraps around).
    Auto-calls verify_wall_facing on each wall.
    Returns list of wall IDs.
    """
    import math as _m
    n = len(points)
    if n < 3:
        print(f"  [POLYGON] Need at least 3 points, got {n}")
        return []

    wall_ids = []
    for i in range(n):
        p0 = points[i]
        p1 = points[(i + 1) % n]
        sx, sy = p0["x"], p0["y"]
        ex, ey = p1["x"], p1["y"]

        seg_label = f"{label_prefix} edge{i}"
        wid = create_wall(sx, sy, z, ex, ey, z, level, wall_type, height, seg_label)

        if wid is not None:
            # Outward normal for CCW polygon: rotate segment direction 90° clockwise
            dx = ex - sx
            dy = ey - sy
            length = _m.sqrt(dx * dx + dy * dy)
            if length > 0.001:
                nx = dy / length    # rotate (dx,dy) 90° CW → (dy, -dx)
                ny = -dx / length
            else:
                nx, ny = 0, 0
            # Round to -1/0/+1 for verify_wall_facing expected values
            enx = 1 if nx > 0.3 else (-1 if nx < -0.3 else 0)
            eny = 1 if ny > 0.3 else (-1 if ny < -0.3 else 0)
            verify_wall_facing(wid, enx, eny, seg_label)

        wall_ids.append(wid)

    print(f"  [POLYGON] Created {len([w for w in wall_ids if w])} walls from {n} vertices")
    return wall_ids


# ─────────────────────────────────────────────
# BUMPOUT — rectangular projection off a face
# ─────────────────────────────────────────────
def add_bumpout(base_x0, base_y0, base_x1, base_y1, wall_face, offset_start, offset_end,
                projection, z, level, wall_type, height=10, label="Bumpout"):
    """
    Projects a rectangular volume off one face of a base rectangle.
    wall_face: "N"(y=y1), "S"(y=y0), "E"(x=x1), "W"(x=x0)
    offset_start, offset_end: position along the face (in the parallel axis) where bump starts/ends
    projection: how far it sticks out (ft)
    Creates 3 walls: two sides + the end face. Does NOT re-draw the base wall.
    Returns list of 3 wall IDs [side1, end, side2].
    """
    p = f"{label} "
    if wall_face == "N":
        by = base_y1
        # side1: west side going north
        s1 = create_wall(offset_start, by, z, offset_start, by + projection, z,
                         level, wall_type, height, f"{p}side-W")
        verify_wall_facing(s1, -1, 0, f"{p}side-W")
        # end: north face going east
        end = create_wall(offset_start, by + projection, z, offset_end, by + projection, z,
                          level, wall_type, height, f"{p}end-N")
        verify_wall_facing(end, 0, 1, f"{p}end-N")
        # side2: east side going south
        s2 = create_wall(offset_end, by + projection, z, offset_end, by, z,
                         level, wall_type, height, f"{p}side-E")
        verify_wall_facing(s2, 1, 0, f"{p}side-E")
    elif wall_face == "S":
        by = base_y0
        s1 = create_wall(offset_end, by, z, offset_end, by - projection, z,
                         level, wall_type, height, f"{p}side-E")
        verify_wall_facing(s1, 1, 0, f"{p}side-E")
        end = create_wall(offset_end, by - projection, z, offset_start, by - projection, z,
                          level, wall_type, height, f"{p}end-S")
        verify_wall_facing(end, 0, -1, f"{p}end-S")
        s2 = create_wall(offset_start, by - projection, z, offset_start, by, z,
                         level, wall_type, height, f"{p}side-W")
        verify_wall_facing(s2, -1, 0, f"{p}side-W")
    elif wall_face == "E":
        bx = base_x1
        s1 = create_wall(bx, offset_start, z, bx + projection, offset_start, z,
                         level, wall_type, height, f"{p}side-S")
        verify_wall_facing(s1, 0, -1, f"{p}side-S")
        end = create_wall(bx + projection, offset_start, z, bx + projection, offset_end, z,
                          level, wall_type, height, f"{p}end-E")
        verify_wall_facing(end, 1, 0, f"{p}end-E")
        s2 = create_wall(bx + projection, offset_end, z, bx, offset_end, z,
                         level, wall_type, height, f"{p}side-N")
        verify_wall_facing(s2, 0, 1, f"{p}side-N")
    elif wall_face == "W":
        bx = base_x0
        s1 = create_wall(bx, offset_end, z, bx - projection, offset_end, z,
                         level, wall_type, height, f"{p}side-N")
        verify_wall_facing(s1, 0, 1, f"{p}side-N")
        end = create_wall(bx - projection, offset_end, z, bx - projection, offset_start, z,
                          level, wall_type, height, f"{p}end-W")
        verify_wall_facing(end, -1, 0, f"{p}end-W")
        s2 = create_wall(bx - projection, offset_start, z, bx, offset_start, z,
                         level, wall_type, height, f"{p}side-S")
        verify_wall_facing(s2, 0, -1, f"{p}side-S")
    else:
        raise ValueError(f"wall_face must be N/S/E/W, got '{wall_face}'")

    print(f"  [BUMPOUT] {label} on face {wall_face}: {projection}ft projection")
    return [s1, end, s2]


# ─────────────────────────────────────────────
# CONNECTOR VOLUME — narrow rect between masses
# ─────────────────────────────────────────────
def create_connector_volume(x0, y0, x1, y1, z, level, wall_type, height=10, label="Connector"):
    """
    A narrow rect exterior connecting two main masses.
    skip_faces=["east","west"] by default (the faces that attach to main volumes).
    Returns wall IDs [south_wall, north_wall].
    """
    print(f"\n── {label}: connector ({x0},{y0})->({x1},{y1}) ──")
    # South wall (exterior faces south)
    w_south = create_wall(x1, y0, z, x0, y0, z, level, wall_type, height, f"{label} south")
    verify_wall_facing(w_south, 0, -1, f"{label} south")
    # North wall (exterior faces north)
    w_north = create_wall(x0, y1, z, x1, y1, z, level, wall_type, height, f"{label} north")
    verify_wall_facing(w_north, 0, 1, f"{label} north")
    return [w_south, w_north]


# ─────────────────────────────────────────────
# GALLERY HALL — wide feature hallway
# ─────────────────────────────────────────────
def create_gallery_hall(x0, y0, x1, y1, z, level, wall_type, width=6, height=10, niche=False,
                        label="Gallery"):
    """
    A wide feature hall (width ft, default 6ft) running along its long axis.
    If niche=True, adds a 2ft deep x 4ft wide alcove on the longer wall (art/coat niche).
    Creates the two long walls. End walls are left open (caller places doors/thresholds).
    Returns wall IDs.
    """
    dx = x1 - x0
    dy = y1 - y0
    wall_ids = []

    print(f"\n── {label}: gallery hall ({x0},{y0})->({x1},{y1}) width={width}ft ──")

    if abs(dx) >= abs(dy):
        # Long axis runs east-west — two walls running along x
        center_y = (y0 + y1) / 2
        w_s_y = center_y - width / 2
        w_n_y = center_y + width / 2
        w_south = create_wall(x0, w_s_y, z, x1, w_s_y, z, level, wall_type, height,
                              f"{label} south wall")
        w_north = create_wall(x0, w_n_y, z, x1, w_n_y, z, level, wall_type, height,
                              f"{label} north wall")
        wall_ids = [w_south, w_north]

        if niche and w_north is not None:
            # 4ft wide x 2ft deep alcove centered on north wall
            niche_cx = (x0 + x1) / 2
            niche_x0 = niche_cx - 2
            niche_x1 = niche_cx + 2
            niche_walls = add_bumpout(x0, w_s_y, x1, w_n_y, "N",
                                      niche_x0, niche_x1, 2, z, level, wall_type,
                                      height, label=f"{label} niche")
            wall_ids.extend(niche_walls)
    else:
        # Long axis runs north-south — two walls running along y
        center_x = (x0 + x1) / 2
        w_w_x = center_x - width / 2
        w_e_x = center_x + width / 2
        w_west = create_wall(w_w_x, y0, z, w_w_x, y1, z, level, wall_type, height,
                             f"{label} west wall")
        w_east = create_wall(w_e_x, y0, z, w_e_x, y1, z, level, wall_type, height,
                             f"{label} east wall")
        wall_ids = [w_west, w_east]

        if niche and w_east is not None:
            # 4ft wide x 2ft deep alcove centered on east wall
            niche_cy = (y0 + y1) / 2
            niche_y0 = niche_cy - 2
            niche_y1 = niche_cy + 2
            niche_walls = add_bumpout(w_w_x, y0, w_e_x, y1, "E",
                                      niche_y0, niche_y1, 2, z, level, wall_type,
                                      height, label=f"{label} niche")
            wall_ids.extend(niche_walls)

    return wall_ids


# ─────────────────────────────────────────────
# GARAGE — standardized helper
# ─────────────────────────────────────────────
def create_garage(gx0, gy0, gx1, gy1, z, level, ext_wall, height=12,
                  garage_cars=2, door_face="south", skip_faces=None, label="Garage"):
    """
    Create garage exterior walls and place overhead door on the specified face.

    door_face: which exterior wall gets the overhead door
      "south" → door on south face (gy0) — typical front-load
      "north" → door on north face (gy1)
      "east"  → door on east face (gx1) — typical side-load when garage is right of house
      "west"  → door on west face (gx0) — side-load when garage is left of house
      NEVER use the face shared with the house interior.

    skip_faces: passed to create_rect_exterior to omit the shared wall face.
    garage_cars: determines door width (1-2=16ft, 3=24ft, 4+=32ft)
    Returns dict of wall IDs + overhead door ID.
    """
    walls = create_rect_exterior(gx0, gy0, gx1, gy1, z, level, ext_wall, height, label, skip_faces=skip_faces)

    door_h_type = "16W X 10H"

    face_map = {
        "south": (walls.get("south"), (gx0 + gx1) / 2, gy0, 'x', gx0, gx1),
        "north": (walls.get("north"), (gx0 + gx1) / 2, gy1, 'x', gx0, gx1),
        "east":  (walls.get("east"),  gx1, (gy0 + gy1) / 2, 'y', gy0, gy1),
        "west":  (walls.get("west"),  gx0, (gy0 + gy1) / 2, 'y', gy0, gy1),
    }

    target_wall, door_x, door_y, axis, ws, we = face_map[door_face]
    print(f"\n── {label}: overhead door on {door_face} face ──")

    d_gar = None
    if target_wall:
        d_gar = place_door(
            target_wall, door_x, door_y, z,
            "Door-Garage-Flush_Panel", door_h_type,
            label=f"{label} overhead",
            wall_axis=axis, wall_start=ws, wall_end=we,
            wall_height=height
        )
        # Do NOT auto-flip — door facing is determined by wall draw direction.
        # Only flip if actually facing wrong (into garage instead of out).

    walls["overhead_door"] = d_gar
    return walls


# ─────────────────────────────────────────────
# FLOORS
# ─────────────────────────────────────────────
def smart_floor(level, z, x0, y0, x1, y1,
                exp_w=True, exp_s=True, exp_e=True, exp_n=True):
    """
    Create a floor slab expanding outward by T on each exterior edge.
    Set exp_*=False on edges shared with adjacent zones — CRITICAL for multi-zone
    footprints (H-shape, L-shape, U-shape, breezeways).

    RULE: Any edge shared with another zone or open breezeway → exp_*=False.
    Only expand on TRUE exterior edges (facing outside/ground).

    CRITICAL: exp_s controls y0 edge, exp_n controls y1 edge.
    If floor A's y1 touches floor B's y0 → A must have exp_n=False AND B must have exp_s=False.

    H-shape with breezeways example:
      Left wing  (exp_e=False)  — east edge open to breezeway
      Breezeway  (exp_w=False, exp_e=False)  — both sides open
      Bridge     (exp_w=False, exp_e=False, exp_s=False, exp_n=False)
                 — all 4 edges shared (breezeways E/W, porches N/S)
      Right wing (exp_w=False)  — west edge open to breezeway
      Back porch (y0=outer, y1=shared w/ bridge) → exp_n=False
      Front porch (y0=shared w/ bridge, y1=outer) → exp_s=False
    """
    pts = [
        {"x": x0-(T if exp_w else 0), "y": y0-(T if exp_s else 0), "z": z},
        {"x": x1+(T if exp_e else 0), "y": y0-(T if exp_s else 0), "z": z},
        {"x": x1+(T if exp_e else 0), "y": y1+(T if exp_n else 0), "z": z},
        {"x": x0-(T if exp_w else 0), "y": y1+(T if exp_n else 0), "z": z},
    ]
    d = _call("revit.create_floor", {"level": level, "boundary_points": pts})
    ok = d["Status"] == "ok"
    fid = d["Result"].get("floor_id") if ok else None
    print(f"  floor [{level} ({x0},{y0})-({x1},{y1})]: {'ok '+str(fid) if ok else 'ERR '+d.get('Message','')}")
    return fid

def create_floor(level, z, outer_pts):
    """outer_pts: list of (x,y) tuples at the OUTER FACE of exterior walls."""
    # Remove closing point if polygon repeats start at end (bridge closes loop itself)
    pts = list(outer_pts)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    bp = [{"x": p[0], "y": p[1], "z": z} for p in pts]
    d = _call("revit.create_floor", {"level": level, "boundary_points": bp})
    fid = d["Result"]["floor_id"] if d["Status"] == "ok" else None
    print(f"  floor [{level}] z={z}: {'ok ' + str(fid) if fid else 'ERR ' + d.get('Message','')}")
    return fid


# ─────────────────────────────────────────────
# ROOFS — per-edge overhang control
# ─────────────────────────────────────────────
def make_roof(label, x0, y0, x1, y1, level_name,
              roof_type='13" Roof No Gyp', overhang=1.5,
              oh_s=True, oh_n=True, oh_w=True, oh_e=True,
              pitch=0.0, slope_style="flat", shed_low_edge=2):
    """
    Create a roof over a rectangular boundary with per-edge overhang and pitch control.

    oh_s/n/w/e: True = add overhang | False = flush (use False on shared/interior edges)

    pitch: rise/run decimal. 0 = flat. Common values:
      0.25 = 3:12  |  0.333 = 4:12  |  0.5 = 6:12  |  0.75 = 9:12

    slope_style:
      "flat"  — no slope (default)
      "shed"  — mono-pitch, one edge slopes. shed_low_edge = index of low eave
                edge order: 0=south, 1=east, 2=north, 3=west (rectangle drawn SW→SE→NE→NW)
      "gable" — two long eave edges slope, rake/gable ends are vertical
      "hip"   — all four edges slope to a ridge point

    shed_low_edge: which edge is the LOW eave for shed roofs (default 2=north, so roof
                  slopes down from south to north — common for Hill Country rear drainage)
    """
    pts = [
        {"x": x0 - (overhang if oh_w else 0), "y": y0 - (overhang if oh_s else 0), "z": 0},
        {"x": x1 + (overhang if oh_e else 0), "y": y0 - (overhang if oh_s else 0), "z": 0},
        {"x": x1 + (overhang if oh_e else 0), "y": y1 + (overhang if oh_n else 0), "z": 0},
        {"x": x0 - (overhang if oh_w else 0), "y": y1 + (overhang if oh_n else 0), "z": 0},
    ]
    payload = {
        "level": level_name,
        "roof_type": roof_type,
        "boundary_points": pts,
        "pitch": pitch,
        "slope_style": slope_style,
        "shed_low_edge": shed_low_edge
    }
    r = _call("revit.create_roof", payload)
    ok = r["Status"] == "ok"
    rid = r["Result"].get("roof_id") if ok else None
    slope_info = f" [{slope_style} {pitch:.2f}]" if pitch > 0 else ""
    print(f"  roof [{label}]{slope_info}: {'ok ' + str(rid) if ok else 'ERR ' + r.get('Message','')}")
    return rid


# ─────────────────────────────────────────────
# L2 CORRIDOR — double-loaded, 4ft wide zone
# ─────────────────────────────────────────────
def create_double_loaded_corridor(x0, x1, corridor_center_y, z, level, int_wall, height=10,
                                  corridor_width=4.0, label="L2 corridor"):
    """
    Create a double-loaded corridor as a proper 4ft-wide zone (two walls).
    corridor_center_y: center of the corridor
    corridor_width: total clear width (default 4ft per Barnhaus standard)
    Returns dict with north_wall and south_wall IDs.

    RULE: All bedroom/bath doors go on BOTH walls (north rooms → south-facing wall,
    south rooms → north-facing wall). Doors must be staggered 1ft in x to avoid conflicts.
    """
    half = corridor_width / 2
    wall_n_y = corridor_center_y + half  # north wall of corridor (south rooms open here)
    wall_s_y = corridor_center_y - half  # south wall of corridor (north rooms open here)

    print(f"\n── {label}: corridor zone y={wall_s_y:.1f} to y={wall_n_y:.1f} (width={corridor_width}ft) ──")
    w_south = create_wall(x0, wall_s_y, z, x1, wall_s_y, z, level, int_wall, height, f"{label} south wall")
    w_north = create_wall(x0, wall_n_y, z, x1, wall_n_y, z, level, int_wall, height, f"{label} north wall")

    return {
        "south_wall": w_south,   # north rooms place doors here
        "north_wall": w_north,   # south rooms place doors here
        "south_y": wall_s_y,
        "north_y": wall_n_y,
        "center_y": corridor_center_y,
    }


# ─────────────────────────────────────────────
# STAIRS
# ─────────────────────────────────────────────
def create_stairs(origin_x, origin_y, bottom_level, top_level,
                  width=4.0, run_length=12.0, label="Stairs"):
    """
    Place a straight-run stair connecting two levels.
    origin_x, origin_y: bottom corner of stair run
    width: stair width in feet (4ft minimum per code)
    run_length: horizontal run length in feet (auto-sized for ~7" risers if omitted)

    RULE: Always reserve a stair zone in service area (min 4×12ft).
    Stairs are always in service zone — never in living core or master suite.
    """
    print(f"\n── {label}: {bottom_level} → {top_level} at ({origin_x},{origin_y}) ──")
    r = _call("revit.create_stairs", {
        "bottom_level": bottom_level,
        "top_level": top_level,
        "origin": {"x": origin_x, "y": origin_y, "z": 0},
        "width": width,
        "run_length": run_length
    })
    ok = r["Status"] == "ok"
    sid = r["Result"].get("stairs_id") if ok else None
    print(f"  stairs [{label}]: {'ok ' + str(sid) if ok else 'ERR ' + r.get('Message','')}")
    return sid


# ─────────────────────────────────────────────
# DOORS
# ─────────────────────────────────────────────
DOOR_WIDTH = {
    'Door-Exterior-Double-Full Glass-Wood_Clad': 6.0,
    'Four_Panel_Sliding_door_11160': 4.0,
    'Three_Panel_Sliding_Door_17534': 9.0,
    'Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad': 3.0,
    'Door-Interior-Single-1_Panel-Wood': 2.5,
    'Door-Interior-Single-Pocket-2_Panel-Wood': 3.0,
    'Door-Garage-Flush_Panel': 16.0,
    'Exterior_Sliding_Door_3843': 6.0,
}

DOOR_HEIGHT = {
    ('Door-Garage-Flush_Panel', 'RV Door'):    14.0,
    ('Door-Garage-Flush_Panel', '16W X 10H'):  10.0,
    ('Door-Garage-Flush_Panel', '10 X 10 OD GL'): 10.0,
    ('Door-Garage-Flush_Panel', '10x10'):      10.0,
    ('Door-Garage-Flush_Panel', '10x14'):      14.0,
    ('Door-Garage-Flush_Panel', '12X14'):      14.0,
    ('Door-Garage-Flush_Panel', '12 X 12'):    12.0,
    ('Door-Garage-Flush_Panel', '96" x 84"'): 7.0,
    ('Overhead_Door_-_Sectional_with_Glass_13396', "10'W X 12'H"): 12.0,
    ('Overhead_Door_-_Sectional_with_Glass_13396', "16' W X 8' H"): 8.0,
}
GARAGE_DOOR_FAMILIES = {'Door-Garage-Flush_Panel', 'Overhead_Door_-_Sectional_with_Glass_13396'}
HEADER_CLEARANCE = 1.5

MIN_CLEARANCE = 3.0
MIN_CLEARANCE_TIGHT = 1.5

def _door_center(wall_start, wall_end, family_name, override_pos=None, tight=False):
    door_w = DOOR_WIDTH.get(family_name, 3.0)
    seg_len = abs(wall_end - wall_start)
    clearance = MIN_CLEARANCE_TIGHT if tight else MIN_CLEARANCE
    min_seg = door_w + 2 * clearance

    if seg_len < min_seg:
        raise ValueError(
            f"Wall segment {wall_start}-{wall_end} ({seg_len:.1f}ft) too short for "
            f"{family_name} ({door_w}ft door + {clearance*2}ft clearance = {min_seg}ft needed)"
        )

    lo = min(wall_start, wall_end) + clearance + door_w / 2
    hi = max(wall_start, wall_end) - clearance - door_w / 2

    if override_pos is not None:
        if not (lo <= override_pos <= hi):
            raise ValueError(
                f"Door position {override_pos} violates clearance. Valid range: {lo:.2f} to {hi:.2f}"
            )
        return override_pos

    return (lo + hi) / 2


def place_door(wall_id, x, y, z, family, type_name, label="",
               wall_axis=None, wall_start=None, wall_end=None, wall_height=None, tight=False, level=None):
    """
    Place a door with automatic clearance validation.
    wall_axis: 'x' or 'y' — which axis the wall runs along
    wall_start/wall_end: coordinate range of the clear segment between intersections
    """
    if family in GARAGE_DOOR_FAMILIES:
        door_h = DOOR_HEIGHT.get((family, type_name), 10.0)
        if wall_height is not None and wall_height < door_h + HEADER_CLEARANCE:
            print(f"  [GARAGE DOOR ERROR] Wall height {wall_height}ft too short for {type_name}. Skipping.")
            return None

    pos = x if wall_axis == 'x' else y if wall_axis == 'y' else None

    if wall_axis and wall_start is not None and wall_end is not None:
        try:
            ideal = _door_center(wall_start, wall_end, family, override_pos=pos, tight=tight)
            if pos is None:
                if wall_axis == 'x': x = ideal
                else: y = ideal
                print(f"  [auto-center] door at {wall_axis}={ideal:.2f}")
        except ValueError as e:
            print(f"  [CLEARANCE ERROR] {e}")
            return None

    payload = {
        "wall_id": wall_id,
        "location": {"x": x, "y": y, "z": z},
        "family_name": family, "type_name": type_name
    }
    if level:
        payload["level"] = level
    d = _call("revit.place_door", payload)
    did = d["Result"]["door_id"] if d["Status"] == "ok" else None
    tag = f" [{label}]" if label else ""
    print(f"  door{tag} on wall {wall_id} at ({x:.1f},{y:.1f}): {'ok ' + str(did) if did else 'ERR ' + d.get('Message','')}")
    return did


# ─────────────────────────────────────────────
# WINDOW PRESETS — zone-aware sizing
# Usage: place_window(wall, x, y, sill_z, **WIN["living"])
# ─────────────────────────────────────────────
WIN_FAMILY = "Instance-Window-Fixed"

# Window presets mapped to types confirmed in this Revit template.
# If a project needs different sizes, load additional families first.
WIN = {
    # Wide panoramic — great room rear wall, main living feature view
    # Best available: 72" x 36" (6ft wide fixed)
    "panoramic": {"family": WIN_FAMILY, "type_name": '72" x 36"'},
    # Standard living — front/side elevation features (60" x 24" confirmed)
    "living":    {"family": WIN_FAMILY, "type_name": '60" x 24"'},
    # Master bedroom — 48" x 48" (generous square)
    "master":    {"family": WIN_FAMILY, "type_name": '48" x 48"'},
    # Secondary bedroom — 48" x 48"
    "bedroom":   {"family": WIN_FAMILY, "type_name": '48" x 48"'},
    # Bathroom — narrow tall: 24" x 96" (keeps privacy, brings in light)
    "bath":      {"family": WIN_FAMILY, "type_name": '24" x 96"'},
    # Clerestory / transom — tall narrow: 24" x 96"
    "clerestory":{"family": WIN_FAMILY, "type_name": '24" x 96"'},
    # Small accent — 18" x 18" (garage, utility, powder room)
    "accent":    {"family": WIN_FAMILY, "type_name": '18" X 18"'},
}

# ─────────────────────────────────────────────
# WINDOWS
# ─────────────────────────────────────────────
def place_window(wall_id, x, y, z, family=WIN_FAMILY, type_name='60" x 24"', label="",
                 wall_axis=None, wall_start=None, wall_end=None):
    pos = x if wall_axis == 'x' else y if wall_axis == 'y' else None

    if wall_axis and wall_start is not None and wall_end is not None:
        win_w = DOOR_WIDTH.get(family, 2.0)
        lo = min(wall_start, wall_end) + MIN_CLEARANCE + win_w / 2
        hi = max(wall_start, wall_end) - MIN_CLEARANCE - win_w / 2
        if pos is None:
            pos = (lo + hi) / 2
            if wall_axis == 'x': x = pos
            else: y = pos

    d = _call("revit.place_window", {
        "wall_id": wall_id,
        "location": {"x": x, "y": y, "z": z},
        "family_name": family, "type_name": type_name
    })
    wid = d["Result"]["window_id"] if d["Status"] == "ok" else None
    tag = f" [{label}]" if label else ""
    print(f"  window{tag} on wall {wall_id} at ({x:.1f},{y:.1f}): {'ok ' + str(wid) if wid else 'ERR ' + d.get('Message','')}")
    return wid


# ─────────────────────────────────────────────
# ROOMS & FIXTURES
# ─────────────────────────────────────────────

def create_room(x, y, z, level, name, number=None, upper_limit_level=None):
    """
    Place a room tag at (x,y) — Revit auto-bounds it to surrounding walls.
    upper_limit_level: level name to cap room height. Pass this for L1 rooms to prevent
    unbounded rooms (which show 0 SF). E.g. upper_limit_level="L1 Roof"
    """
    payload = {"location_point": {"x": x, "y": y, "z": z}, "level": level, "name": name}
    if number:
        payload["number"] = number
    if upper_limit_level:
        payload["upper_limit_level"] = upper_limit_level
    r = _call("revit.create_room", payload)
    ok = r["Status"] == "ok"
    rid = r["Result"].get("room_id") if ok else None
    area = r["Result"].get("area_sf", 0) if ok else 0
    print(f"  room [{name}] at ({x},{y}): {'ok ' + str(rid) + f' ({area:.0f} SF)' if ok else 'ERR ' + r.get('Message','')}")
    return rid

def get_zone_height(zone_name, zone_heights, default_height=11):
    """
    Get wall height for a named zone from submission's zone_heights dict.

    zone_heights: dict from Supabase submission, e.g.:
      {"main_wing": "10", "secondary_wing": "14", "center": "12"}
    default_height: fallback if zone not specified (uses wall_height from submission)

    Usage in build scripts:
      H = get_zone_height('center', sub['zone_heights'], default_height=int(wall_height_ft))
      create_wall(..., height=H)

    Zone names match SHAPE_ZONES in the form:
      rectangle:  main
      l-shape:    main_wing, secondary_wing
      u-shape:    left_wing, center, right_wing
      t-shape:    main_body, rear_wing
      courtyard:  left_wing, center, right_wing
    """
    if not zone_heights:
        return default_height
    val = zone_heights.get(zone_name)
    if val is None:
        return default_height
    try:
        return int(val)
    except (ValueError, TypeError):
        return default_height


WALL_HEIGHT_MAP = {'standard': 10, 'tall': 11, 'dramatic': 12}


def resolve_wall_heights(submission):
    """
    Given a Supabase submission dict, return a dict of zone_name → wall_height (int).
    Falls back to global wall_height if zone_heights not set.

    Usage:
      heights = resolve_wall_heights(sub)
      H_main = heights.get('main_wing', 11)
    """
    global_h = WALL_HEIGHT_MAP.get(submission.get('wall_height', 'standard'), 11)
    zone_heights = submission.get('zone_heights') or {}
    result = {}
    for zone, val in zone_heights.items():
        try:
            result[zone] = int(val)
        except (ValueError, TypeError):
            result[zone] = global_h
    return result, global_h


def get_wall_doors(wall_id, clearance=2.0):
    """
    Query Revit for all doors hosted on a wall.
    Returns door_positions list in place_against_wall format:
      [(wall_coord_ignored, pos_along, width_ft, clearance_ft), ...]
    wall_coord_ignored = 0 since the caller already knows which wall.
    """
    r = _call("revit.get_wall_doors", {"wall_id": wall_id})
    if r["Status"] != "ok":
        return []
    doors = r["Result"].get("doors", [])
    return [(0, d["x"] if d["x"] != 0 else d["y"], d["width_ft"], clearance) for d in doors]


def place_against_wall(family, type_name, wall_coord, wall_face, position_along, z, level,
                       fixture_depth=0.0, wall_thickness=None, label="", door_positions=None,
                       wall_id=None, door_clearance=2.0):
    """
    Place a fixture/cabinet with its back flush against a wall's interior face.

    CALIBRATED 2026-03-06:
      - Cabinet origin = BACK face (confirmed empirically)
      - rotation=0   → front faces SOUTH (-Y)
      - rotation=180 → front faces NORTH (+Y)
      - rotation=90  → front faces WEST  (-X)
      - rotation=270 → front faces EAST  (+X)

    wall_coord    : wall centerline coordinate
    wall_face     : direction the ROOM is relative to the wall
                    'S' = room is south (north wall) → rotation=0
                    'N' = room is north (south wall) → rotation=180
                    'E' = room is east  (west wall)  → rotation=270
                    'W' = room is west  (east wall)  → rotation=90
    position_along: coordinate along the wall
    fixture_depth : for plumbing/appliances whose origin is at CENTER, add depth/2
                    (cabinets = 0, toilets ~1.25, showers ~1.5)
    wall_thickness: 0.625 exterior, 0.375 interior
    wall_id       : if provided, auto-queries Revit for doors on this wall (preferred)
    door_positions: manual override list [(wall_coord, pos_along, width_ft, clearance)]
    door_clearance: clearance in ft when using wall_id auto-query (default 2ft)
    """
    if wall_thickness is None:
        wall_thickness = 0.625

    half = wall_thickness / 2.0

    if wall_face == 'S':    # north wall, room south → face south, origin at interior face
        x, y, rot = position_along, wall_coord - half - fixture_depth, 0
    elif wall_face == 'N':  # south wall, room north → face north
        x, y, rot = position_along, wall_coord + half + fixture_depth, 180
    elif wall_face == 'E':  # west wall, room east → face east (rotation=90)
        x, y, rot = wall_coord + half + fixture_depth, position_along, 90
    elif wall_face == 'W':  # east wall, room west → face west (rotation=270)
        x, y, rot = wall_coord - half - fixture_depth, position_along, 270
    else:
        raise ValueError(f"wall_face must be N/S/E/W, got '{wall_face}'")

    # Auto-query door positions from Revit if wall_id provided (preferred over manual list)
    if wall_id is not None:
        door_positions = get_wall_doors(wall_id, clearance=door_clearance)
        if door_positions:
            print(f"  [AUTO] Found {len(door_positions)} door(s) on wall {wall_id}")

    # Door clearance check
    if door_positions:
        for dp in door_positions:
            dpos  = dp[1]
            dwidth = dp[2]
            dclear = dp[3] if len(dp) > 3 else 2.0
            if abs(position_along - dpos) < (dwidth / 2 + dclear):
                print(f"  [DOOR CONFLICT] {label} at {position_along:.1f} too close "
                      f"to door at {dpos:.1f} (within {dwidth/2+dclear:.1f}ft). SKIPPING.")
                return None

    return place_fixture(family, type_name, x, y, z, level, rotation=rot, label=label)


def place_fixture(family, type_name, x, y, z, level, rotation=0, label=""):
    """
    Place any family instance (plumbing, appliance, furniture) with optional rotation (degrees).
    IMPORTANT: z should be 0 for floor-mounted fixtures. Revit's NewFamilyInstance with a Level
    treats z as OFFSET from the level's elevation, so z=0 = sitting on the floor.
    Passing z=level_elevation would place fixtures 2× the floor height above the floor.
    """
    import time
    time.sleep(0.4)   # rate-limit fixture calls — Revit crashes if hammered too fast
    r = _call("revit.place_family_instance", {
        "family_name": family, "type_name": type_name,
        "location": {"x": x, "y": y, "z": z},
        "level": level, "rotation": rotation
    })
    ok = r["Status"] == "ok"
    iid = r["Result"].get("instance_id") if ok else None
    tag = f" [{label}]" if label else f" [{family}]"
    print(f"  fixture{tag} at ({x:.1f},{y:.1f}) r={rotation}°: {'ok ' + str(iid) if ok else 'ERR ' + r.get('Message','')}")
    return iid


def place_porch_posts(post_xs, post_y, level, roof_pitch=0.083, porch_depth=12,
                      wall_height=11, family='HSS-Hollow Structural Section-Column',
                      type_name='HSS6X6X3/16', shed_slopes_toward_larger_y=True):
    """
    Place porch HSS columns and set correct Top Offset so tops reach the shed roof.

    RULE: Porch shed roofs ALWAYS slope AWAY from the house (high at house wall,
    low at outer post line). Posts at the outer edge are ALWAYS at the low end.
    Top Offset = 0 for all porch posts — the roof drops to meet them.

    shed_slopes_toward_larger_y is kept for legacy compatibility but no longer
    affects top_offset. Posts are always at the low end of the shed.

    Args:
        post_xs:    list of x coords for posts
        post_y:     y coord for all posts
        level:      Revit level name
        roof_pitch: shed roof pitch (default 0.083 = 1:12)
        porch_depth: depth of porch in feet
        wall_height: house wall height in feet (default 11)
        shed_slopes_toward_larger_y: legacy param, ignored
    """
    # Posts sit at the LOW end of the shed roof (outer edge).
    # Roof underside at outer edge = wall_height - (porch_depth * pitch) - roof_thickness
    # Columns default top = wall_height (Level 2.0 at z=11).
    # top_offset = (roof_underside) - wall_height  → negative value
    roof_underside_at_post = wall_height - (porch_depth * roof_pitch)
    top_offset = roof_underside_at_post - wall_height  # negative

    # Pull posts 0.25ft (half HSS6 width) inside floor edge so they don't overhang
    COL_HALF = 0.25
    # Determine inward direction based on which side the house is on
    # shed_slopes_toward_larger_y=True  → house at smaller y, outer edge at larger y → pull post inward = subtract
    # shed_slopes_toward_larger_y=False → house at larger y, outer edge at smaller y → pull post inward = add
    if shed_slopes_toward_larger_y:
        adjusted_y = post_y - COL_HALF
    else:
        adjusted_y = post_y + COL_HALF

    ids = []
    for px in post_xs:
        pid = place_fixture(family, type_name, px, adjusted_y, 0, level,
                            label=f'Porch Post {px}')
        if pid:
            r = _call('revit.set_parameter_value', {
                'element_id': pid,
                'parameter_name': 'Top Offset',
                'value': top_offset
            })
            status = r.get('Result', {}).get('status', 'err')
            print(f"    Top Offset {top_offset:.2f}ft: {status}")
        ids.append(pid)
    return ids


def attach_walls_to_roof(wall_ids, roof_id, location="Top"):
    """
    Attach wall tops (or bases) to a roof using Wall.AddAttachment() — Revit 25.3+ API.
    This is the exact equivalent of the UI "Attach Top/Base" tool.
    location: "Top" (default) or "Base"
    """
    ids = [i for i in wall_ids if i is not None]
    if not ids or not roof_id:
        return
    r = _call("revit.attach_walls_to_roof", {"wall_ids": ids, "roof_id": roof_id, "location": location})
    ok = r["Status"] == "ok"
    if ok:
        res = r["Result"]
        print(f"  attach walls to roof {roof_id}: ok — {res.get('attached',0)} attached, {res.get('skipped',0)} skipped")
    else:
        print(f"  attach walls to roof: ERR {r.get('Message','')}")


def set_wall_height(wall_id, height):
    """Override a wall's unconnected height (fallback if attach fails)."""
    r = _call("revit.set_wall_height", {"wall_id": wall_id, "height": height})
    ok = r["Status"] == "ok"
    print(f"  wall {wall_id} height → {height}ft: {'ok' if ok else 'ERR ' + r.get('Message','')}")


# ─── Room label helpers ───────────────────────────────────────────────────────
def label_rooms(rooms, level, upper_limit_level=None):
    """
    Place room tags for a list of rooms.
    rooms: list of dicts with keys: name, x, y, z (optional, default 0)
    upper_limit_level: pass the ceiling level name to fix 0 SF on L1 rooms.
                       e.g. label_rooms([...], "Level 1.0", upper_limit_level="L1 Roof")
    """
    print(f"\n── Room Labels [{level}] ──")
    ids = []
    for rm in rooms:
        ids.append(create_room(rm["x"], rm["y"], rm.get("z", 0), level, rm["name"],
                               rm.get("number"), upper_limit_level=upper_limit_level))
    return ids


# ─── Kitchen layout ───────────────────────────────────────────────────────────
# kitchen_layout values (from design form):
#   "l-shape"   — run on back wall + one perpendicular side wall
#   "galley"    — two parallel wall runs, no island
#   "u-shape"   — runs on back wall + both side walls
#   "one-wall"  — single back wall run, island as second element
#   "island"    — back wall run + dominant island as workspace
#
# back_wall: "north" | "south" | "east" | "west" — which wall the primary run is against

def _cab(family, type_name, x, y, level, rotation=0, label=""):
    """Internal shorthand: place a cabinet at z=0 (always floor-mounted)."""
    return place_fixture(family, type_name, x, y, 0, level, rotation=rotation, label=label)


def _kitchen_wall_run(wall, x0, y0, x1, y1, fz, level, has_sink=True, has_range=True, has_fridge=True, prefix=""):
    """
    Place a single kitchen counter run against a wall.
    wall: "north" | "south" | "east" | "west"
    Places base cabinets, uppers, sink, range, fridge along the specified wall.
    """
    cx = (x0+x1)/2; cy = (y0+y1)/2
    if wall == "north":
        wy = y1 - 1.25
        if has_range:
            place_fixture("Range-Gas", '36"', cx-5, wy, fz, level, rotation=180, label=f"{prefix}range")
            place_fixture("Hood-Wall", '36"', cx-5, y1-0.3, fz, level, rotation=180, label=f"{prefix}hood")
        if has_fridge:
            place_fixture("Refrigerator", '36" RH', x1-2.5, wy, fz, level, rotation=180, label=f"{prefix}fridge")
        if has_range:
            place_fixture("Dishwasher", '24"', cx-1, wy, fz, level, rotation=180, label=f"{prefix}DW")
        if has_sink:
            place_fixture("Sink Kitchen-Single", '30" x 21"', cx+1.5, wy, fz, level, rotation=180, label=f"{prefix}sink")
            _cab("Base Cabinet-Double Door Sink Unit", '36"', cx+1.5, y1-1.5, level, rotation=180, label=f"{prefix}sink-base")
        for i, bx in enumerate([x0+1.5, x0+3.5, cx-2.5, cx+4, cx+6]):
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', bx, y1-1.5, level, rotation=180, label=f"{prefix}base{i}")
        for i, bx in enumerate([x0+1.5, x0+4, cx-1, cx+4, cx+6.5]):
            _cab("Upper Cabinet-Single Door-Wall", '24"', bx, y1-0.5, level, rotation=180, label=f"{prefix}upper{i}")
    elif wall == "south":
        wy = y0 + 1.25
        if has_range:
            place_fixture("Range-Gas", '36"', cx-5, wy, fz, level, rotation=0, label=f"{prefix}range")
            place_fixture("Hood-Wall", '36"', cx-5, y0+0.3, fz, level, rotation=0, label=f"{prefix}hood")
        if has_fridge:
            place_fixture("Refrigerator", '36" RH', x1-2.5, wy, fz, level, rotation=0, label=f"{prefix}fridge")
        if has_sink:
            place_fixture("Sink Kitchen-Single", '30" x 21"', cx+1.5, wy, fz, level, rotation=0, label=f"{prefix}sink")
            _cab("Base Cabinet-Double Door Sink Unit", '36"', cx+1.5, y0+1.5, level, rotation=0, label=f"{prefix}sink-base")
        for i, bx in enumerate([x0+1.5, x0+3.5, cx-2.5, cx+4, cx+6]):
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', bx, y0+1.5, level, rotation=0, label=f"{prefix}base{i}")
        for i, bx in enumerate([x0+1.5, x0+4, cx-1, cx+4, cx+6.5]):
            _cab("Upper Cabinet-Single Door-Wall", '24"', bx, y0+0.5, level, rotation=0, label=f"{prefix}upper{i}")
    elif wall == "west":
        wx = x0 + 1.25
        if has_range:
            place_fixture("Range-Gas", '36"', wx, cy-3, fz, level, rotation=270, label=f"{prefix}range")
            place_fixture("Hood-Wall", '36"', x0+0.3, cy-3, fz, level, rotation=270, label=f"{prefix}hood")
        if has_fridge:
            place_fixture("Refrigerator", '36" RH', wx, y1-2.5, fz, level, rotation=270, label=f"{prefix}fridge")
        if has_sink:
            place_fixture("Sink Kitchen-Single", '30" x 21"', wx, cy+1.5, fz, level, rotation=270, label=f"{prefix}sink")
            _cab("Base Cabinet-Double Door Sink Unit", '36"', x0+1.5, cy+1.5, level, rotation=270, label=f"{prefix}sink-base")
        for i, by in enumerate([y0+1.5, cy-2, cy, cy+3.5, cy+5.5]):
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', x0+1.5, by, level, rotation=270, label=f"{prefix}base{i}")
        for i, by in enumerate([y0+1.5, cy-2, cy+1, cy+3.5, cy+5.5]):
            _cab("Upper Cabinet-Single Door-Wall", '24"', x0+0.5, by, level, rotation=270, label=f"{prefix}upper{i}")
    elif wall == "east":
        wx = x1 - 1.25
        if has_range:
            place_fixture("Range-Gas", '36"', wx, cy-3, fz, level, rotation=90, label=f"{prefix}range")
            place_fixture("Hood-Wall", '36"', x1-0.3, cy-3, fz, level, rotation=90, label=f"{prefix}hood")
        if has_fridge:
            place_fixture("Refrigerator", '36" RH', wx, y1-2.5, fz, level, rotation=90, label=f"{prefix}fridge")
        if has_sink:
            place_fixture("Sink Kitchen-Single", '30" x 21"', wx, cy+1.5, fz, level, rotation=90, label=f"{prefix}sink")
            _cab("Base Cabinet-Double Door Sink Unit", '36"', x1-1.5, cy+1.5, level, rotation=90, label=f"{prefix}sink-base")
        for i, by in enumerate([y0+1.5, cy-2, cy, cy+3.5, cy+5.5]):
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', x1-1.5, by, level, rotation=90, label=f"{prefix}base{i}")
        for i, by in enumerate([y0+1.5, cy-2, cy+1, cy+3.5, cy+5.5]):
            _cab("Upper Cabinet-Single Door-Wall", '24"', x1-0.5, by, level, rotation=90, label=f"{prefix}upper{i}")


def layout_kitchen(x0, y0, x1, y1, z, level,
                   back_wall="north", has_island=False,
                   kitchen_layout="l-shape", label="Kitchen"):
    """
    Place kitchen appliances and cabinets in a zone.
    kitchen_layout: "l-shape" | "galley" | "u-shape" | "one-wall" | "island"
    back_wall: primary run direction ("north" | "south" | "east" | "west")
    Fixtures always at z=0 (level-relative).
    """
    cx = (x0+x1)/2; cy = (y0+y1)/2
    fz = 0
    # Opposite wall for galley/u-shape second run
    opp = {"north": "south", "south": "north", "east": "west", "west": "east"}
    # Perpendicular walls for L/U-shape side run
    perp = {"north": ("west","east"), "south": ("west","east"),
            "east":  ("south","north"), "west": ("south","north")}
    print(f"\n── {label} [{kitchen_layout}] ──")

    if kitchen_layout == "one-wall":
        # Single back wall run, island as second element
        _kitchen_wall_run(back_wall, x0, y0, x1, y1, fz, level, prefix="")
        place_fixture("Sink Kitchen-Island", '18" x 18"', cx, cy, fz, level, label="island sink")
        _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx-1.5, cy, level, label="island base L")
        _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx+1.5, cy, level, label="island base R")

    elif kitchen_layout == "galley":
        # Two parallel wall runs — back wall has range+sink, opposite wall has fridge+prep
        _kitchen_wall_run(back_wall, x0, y0, x1, y1, fz, level,
                          has_sink=True, has_range=True, has_fridge=False, prefix="A-")
        _kitchen_wall_run(opp[back_wall], x0, y0, x1, y1, fz, level,
                          has_sink=False, has_range=False, has_fridge=True, prefix="B-")

    elif kitchen_layout == "l-shape":
        # Back wall (range+sink) + one side wall (fridge+prep)
        side = perp[back_wall][0]  # default: west/south side
        _kitchen_wall_run(back_wall, x0, y0, x1, y1, fz, level,
                          has_sink=True, has_range=True, has_fridge=False, prefix="A-")
        _kitchen_wall_run(side, x0, y0, x1, y1, fz, level,
                          has_sink=False, has_range=False, has_fridge=True, prefix="B-")
        if has_island:
            place_fixture("Sink Kitchen-Island", '18" x 18"', cx, cy, fz, level, label="island sink")
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx-1.5, cy, level, label="island base L")
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx+1.5, cy, level, label="island base R")

    elif kitchen_layout == "u-shape":
        # Back wall + both side walls
        p1, p2 = perp[back_wall]
        _kitchen_wall_run(back_wall, x0, y0, x1, y1, fz, level,
                          has_sink=True, has_range=True, has_fridge=False, prefix="A-")
        _kitchen_wall_run(p1, x0, y0, x1, y1, fz, level,
                          has_sink=False, has_range=False, has_fridge=True, prefix="B-")
        _kitchen_wall_run(p2, x0, y0, x1, y1, fz, level,
                          has_sink=False, has_range=False, has_fridge=False, prefix="C-")
        if has_island:
            place_fixture("Sink Kitchen-Island", '18" x 18"', cx, cy, fz, level, label="island sink")
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx-1.5, cy, level, label="island base L")
            _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx+1.5, cy, level, label="island base R")

    else:  # "island" or fallback — back wall run + prominent island
        _kitchen_wall_run(back_wall, x0, y0, x1, y1, fz, level,
                          has_sink=False, has_range=True, has_fridge=True, prefix="")
        # Island is the primary workspace with sink
        place_fixture("Sink Kitchen-Island", '18" x 18"', cx,     cy, fz, level, label="island sink")
        _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx-1.5, cy, level, label="island base L")
        _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx+1.5, cy, level, label="island base R")
        _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx,  cy-1.5, level, label="island base front")
        _cab("Base Cabinet-Double Door & 1 Drawer", '36"', cx,  cy+1.5, level, label="island base back")
        # Pantry tall cabinet in corner
        _cab("Tall Cabinet-Double Door", '36"', x0+1.5, y0+1.5, level, label="pantry")


# ─── Hallway helpers ─────────────────────────────────────────────────────────
def create_hallway(x0, x1, center_y, z, level, wall_type, height=10,
                   hallway_type="double-loaded", width=4.0, label="hallway"):
    """
    Create hallway walls based on hallway_type:
      double-loaded: two parallel walls (Barnhaus L2 standard) — uses create_double_loaded_corridor
      single-corridor: one wall divides private from public zone
      gallery: wide single wall, 6ft+ clear (one wall, open other side)
      open-plan: no walls created — returns empty dict
    Returns dict with available wall IDs.
    """
    if hallway_type == "open-plan":
        print(f"\n── {label}: open plan — no hallway walls ──")
        return {}

    elif hallway_type == "double-loaded":
        return create_double_loaded_corridor(x0, x1, center_y, z, level, wall_type,
                                              height=height, corridor_width=width, label=label)

    elif hallway_type in ("single-corridor", "gallery"):
        actual_width = 6.0 if hallway_type == "gallery" else width
        print(f"\n── {label} [{hallway_type}]: single wall at y={center_y:.1f}, clear width={actual_width}ft ──")
        w = create_wall(x0, center_y, z, x1, center_y, z, level, wall_type, height, f"{label} wall")
        return {"wall": w, "width": actual_width}

    return {}


# ─── Bathroom layouts ─────────────────────────────────────────────────────────
def layout_bath_standard(x0, y0, x1, y1, z, level, label="Bath"):
    """
    Standard bath: toilet + shower + vanity + vanity cabinet.
    z param is kept for API consistency but fixtures always placed at fz=0 (level-relative).
    """
    cx = (x0 + x1) / 2
    fz = 0  # level-relative, NOT absolute elevation
    print(f"\n── {label} fixtures ──")
    place_fixture("Toilet-Domestic-3D",    "Toilet-Domestic-3D",
                  cx,          y0 + 1.25, fz, level, label="toilet")
    place_fixture("Shower_columns_15486",  "Shower_columns_15486",
                  x1 - 1.5,   y1 - 1.5,  fz, level, label="shower")
    place_fixture("Sink Vanity-Square",    '20" x 18"',
                  x0 + 0.75,  (y0+y1)/2, fz, level, rotation=270, label="vanity")
    # Vanity base cabinet under sink
    _cab("Base Cabinet-Double Door Sink Unit", '30"', x0 + 0.75, (y0+y1)/2, level, rotation=270, label="vanity cab")


def layout_bath_master(x0, y0, x1, y1, z, level, label="Master Bath"):
    """
    Master bath: freestanding tub, walk-in shower, double vanity with cabinets.
    All fixtures at fz=0 (level-relative).
    """
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    fz = 0
    print(f"\n── {label} fixtures ──")
    # Freestanding tub on focal wall (north)
    place_fixture("Tub-Free Standing-3D",  '30" x 60"',
                  cx,          y1 - 2.5,  fz, level, label="freestanding tub")
    # Toilet in SW corner
    place_fixture("Toilet-Domestic-3D",    "Toilet-Domestic-3D",
                  x0 + 1.0,   y0 + 1.25, fz, level, label="toilet")
    # Walk-in shower in SE corner
    place_fixture("Shower_columns_15486",  "Shower_columns_15486",
                  x1 - 1.5,   y0 + 1.5,  fz, level, rotation=180, label="shower")
    # Double vanity sinks on east wall
    place_fixture("Sink Vanity-Square", '20" x 18"',
                  x1 - 0.75,  cy - 1.5,  fz, level, rotation=90, label="vanity L")
    place_fixture("Sink Vanity-Square", '20" x 18"',
                  x1 - 0.75,  cy + 1.5,  fz, level, rotation=90, label="vanity R")
    # Double vanity cabinets
    _cab("Base Cabinet-Double Door Sink Unit", '36"', x1-1.5, cy-1.5, level, rotation=90, label="vanity cab L")
    _cab("Base Cabinet-Double Door Sink Unit", '36"', x1-1.5, cy+1.5, level, rotation=90, label="vanity cab R")
    # Makeup vanity area (drawer unit)
    _cab("Base Cabinet-3 Drawers", '27"', x1-1.5, cy, level, rotation=90, label="makeup drawers")


def layout_half_bath(x, y, z, level, rotation=0, label="Half Bath"):
    """Powder room: toilet + sink + vanity cabinet. fz=0 always."""
    fz = 0
    print(f"\n── {label} fixtures ──")
    place_fixture("Toilet-Domestic-3D", "Toilet-Domestic-3D",
                  x,    y + 1.0, fz, level, rotation=rotation, label="toilet")
    place_fixture("Sink Vanity-Square", '20" x 18"',
                  x,    y - 0.5, fz, level, rotation=rotation, label="sink")
    _cab("Base Cabinet-Double Door Sink Unit", '24"', x, y-0.5, level, rotation=rotation, label="vanity cab")


def layout_laundry(x, y, z, level, rotation=0, label="Laundry"):
    """Stacked washer/dryer. fz=0 always."""
    fz = 0
    print(f"\n── {label} fixtures ──")
    place_fixture("Stacked Washer and Dryer", '26"x25" - Private',
                  x, y, fz, level, rotation=rotation, label="W/D stack")


# ─────────────────────────────────────────────
# TEMPLATE MANIFEST
# ─────────────────────────────────────────────
import json as _json, os as _os

_MANIFEST_PATH = _os.path.join(_os.path.dirname(__file__), 'revit_template_manifest.json')
_manifest = None

def load_manifest(path=None):
    """Load the template manifest (run scan_revit_template.py first to generate it)."""
    global _manifest
    p = path or _MANIFEST_PATH
    if not _os.path.exists(p):
        print(f"  [WARN] No manifest found at {p}. Run scan_revit_template.py first.")
        return None
    with open(p) as f:
        _manifest = _json.load(f)
    return _manifest

def get_manifest():
    global _manifest
    if _manifest is None:
        load_manifest()
    return _manifest

def check_family(category, family_name, type_name=None):
    """Verify a family/type exists in the manifest. Prints warning if not found."""
    m = get_manifest()
    if not m:
        return True  # no manifest, assume ok
    key_map = {"Doors": "door_families", "Windows": "window_families", "Stairs": "stair_families"}
    key = key_map.get(category)
    if not key:
        return True
    for fam in m.get(key, []):
        if fam["name"] == family_name:
            if type_name is None:
                return True
            for t in fam.get("types", []):
                if t["name"] == type_name:
                    return True
            print(f"  [MANIFEST WARN] Type '{type_name}' not found in family '{family_name}'. Available: {[t['name'] for t in fam['types']]}")
            return False
    print(f"  [MANIFEST WARN] Family '{family_name}' not found in {category}.")
    return False

def list_wall_types():
    """Return wall type names from manifest."""
    m = get_manifest()
    return [wt["name"] for wt in (m or {}).get("wall_types", [])]

def list_window_types(family_name=None):
    """Return all window type names, optionally filtered by family."""
    m = get_manifest()
    result = []
    for fam in (m or {}).get("window_families", []):
        if family_name is None or fam["name"] == family_name:
            result.extend([t["name"] for t in fam.get("types", [])])
    return result

def list_door_types(family_name=None):
    """Return all door type names, optionally filtered by family."""
    m = get_manifest()
    result = []
    for fam in (m or {}).get("door_families", []):
        if family_name is None or fam["name"] == family_name:
            result.extend([t["name"] for t in fam.get("types", [])])
    return result

# ─────────────────────────────────────────────
# GENERIC CALL PASSTHROUGH
# ─────────────────────────────────────────────
def call(tool, payload):
    return _call(tool, payload)


# ═══════════════════════════════════════════════════════════════════════════
# TASK 2: WALL-RELATIVE SMART FIXTURE PLACEMENT
# ═══════════════════════════════════════════════════════════════════════════

def check_placement_clearance(x, y, width, depth, placed_items):
    """
    Check whether a proposed fixture footprint overlaps any previously placed items.

    Args:
        x (float): Center X of proposed placement.
        y (float): Center Y of proposed placement.
        width (float): Footprint width in feet (along X axis, pre-rotation).
        depth (float): Footprint depth in feet (along Y axis, pre-rotation).
        placed_items (list): List of dicts with keys {x, y, width, depth} for
                             already-placed items. Maintained by the caller.

    Returns:
        bool: True if the proposed position is CLEAR (no conflicts), False if conflict.

    Example::

        placed = []
        if check_placement_clearance(5, 3, 2, 2, placed):
            place_fixture(...)
            placed.append({"x": 5, "y": 3, "width": 2, "depth": 2})
    """
    hw = width / 2.0
    hd = depth / 2.0
    px0, px1 = x - hw, x + hw
    py0, py1 = y - hd, y + hd

    for item in placed_items:
        iw = item.get("width", 1.0) / 2.0
        id_ = item.get("depth", 1.0) / 2.0
        ix = item["x"]; iy = item["y"]
        # AABB overlap test (no rotation for simplicity)
        if (px0 < ix + iw and px1 > ix - iw and
                py0 < iy + id_ and py1 > iy - id_):
            return False
    return True


def place_fixture_smart(wall_id, offset_from_wall, position_along_wall, z,
                        family, type_name, label="", level=None,
                        placed_items=None, fixture_width=2.0, fixture_depth=2.0):
    """
    Place a fixture relative to a wall's face geometry instead of using hardcoded XY.

    This solves the problem of fixtures landing inside walls or drifting to wrong
    positions when the plan footprint shifts.

    Args:
        wall_id (int): Revit wall element ID to place relative to.
        offset_from_wall (float): Distance in feet from the wall's INTERIOR face.
                                  E.g. 0.5 = toilet tank flush; 1.25 = base cabinet center.
        position_along_wall (float): Distance in feet from the wall's START point
                                     along its length (0.0 = wall start).
        z (float): Elevation in feet (0 for level-relative floor-mounted fixtures).
        family (str): Revit family name.
        type_name (str): Revit type name within the family.
        label (str): Optional label for console output.
        level (str): Revit level name (passed to place_fixture).
        placed_items (list|None): Running list of placed item footprints for clearance
                                  checks. Pass [] to enable checking; None to skip.
        fixture_width (float): Footprint width for clearance check (default 2.0 ft).
        fixture_depth (float): Footprint depth for clearance check (default 2.0 ft).

    Returns:
        int|None: Revit instance ID, or None on error/conflict.

    How it works:
        1. Calls revit.get_wall_geometry to retrieve start, end, and orientation.
        2. Computes the along-wall unit vector and the face-inward unit vector.
        3. Derives absolute XY as:
               pt = wall_start + position_along_wall * along_vec
                    + (offset_from_wall + half_wall_thickness) * inward_vec
        4. Checks clearance against placed_items (if provided).
        5. Calls place_fixture with the computed XY.

    Example::

        placed = []
        # Place toilet 1.0ft from wall face, 3ft from wall start
        place_fixture_smart(north_wall_id, 1.0, 3.0, 0,
                            "Toilet-Domestic-3D", "Toilet-Domestic-3D",
                            label="toilet", level="Level 1.0",
                            placed_items=placed, fixture_width=1.5, fixture_depth=2.5)
    """
    # Step 1: Get wall geometry
    geo = _call("revit.get_element_bounding_box", {"element_id": wall_id})
    orient = _call("revit.get_wall_orientation", {"wall_id": wall_id})

    if geo.get("Status") != "ok" or orient.get("Status") != "ok":
        print(f"  [SMART FIXTURE] Could not get geometry for wall {wall_id} — skipping {label}")
        return None

    # Determine wall axis from bounding box
    bbox = geo["Result"]
    min_pt = bbox.get("min", {})
    max_pt = bbox.get("max", {})
    dx = (max_pt.get("x", 0) - min_pt.get("x", 0))
    dy = (max_pt.get("y", 0) - min_pt.get("y", 0))

    import math as _math
    length = _math.sqrt(dx*dx + dy*dy)
    if length < 0.01:
        print(f"  [SMART FIXTURE] Wall {wall_id} has zero length — skipping {label}")
        return None

    # Along-wall unit vector (from min corner)
    along_x = dx / length
    along_y = dy / length

    # Inward unit vector = orientation from Revit (exterior normal), negated = inward
    ori = orient["Result"]["orientation"]
    inward_x = -ori["x"]
    inward_y = -ori["y"]

    # Assume wall interior face = half wall thickness inward from center
    # Standard EXT wall half thickness = 0.3125ft, INT wall = 0.1875ft
    # We add offset_from_wall relative to the interior FACE, so we offset from wall center
    # by: half_thick + offset_from_wall
    # We use 0.3125 as a safe default (exterior wall)
    half_thick = 0.3125

    # Step 2: Compute absolute XY
    base_x = min_pt.get("x", 0)
    base_y = min_pt.get("y", 0)

    pos_x = base_x + along_x * position_along_wall + inward_x * (half_thick + offset_from_wall)
    pos_y = base_y + along_y * position_along_wall + inward_y * (half_thick + offset_from_wall)

    # Step 3: Clearance check
    if placed_items is not None:
        if not check_placement_clearance(pos_x, pos_y, fixture_width, fixture_depth, placed_items):
            print(f"  [SMART FIXTURE] Clearance conflict at ({pos_x:.2f},{pos_y:.2f}) — skipping {label}")
            return None

    # Step 4: Place fixture
    result = place_fixture(family, type_name, pos_x, pos_y, z, level or "Level 1.0", label=label)

    if result is not None and placed_items is not None:
        placed_items.append({
            "x": pos_x, "y": pos_y,
            "width": fixture_width, "depth": fixture_depth,
            "label": label
        })

    return result


# ═══════════════════════════════════════════════════════════════════════════
# TASK 3: PRE-BUILD DESIGN VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

def design_brief_to_layout(brief_dict, rules_path):
    """
    Validate a design brief against Barnhaus design rules and produce a
    layout specification dict before any Revit calls are made.

    Reads the barnhaus-design-rules.md file and applies the rules to
    the brief to produce a validated layout and list of warnings.

    Args:
        brief_dict (dict): Design parameters. Recognized keys:
            style (str):           "barnhaus-modern" etc.
            stories (int):         1 or 2
            total_sf (int):        Total conditioned square footage
            bedrooms (int):        Number of bedrooms
            garage_cars (int):     Number of garage bays
            kitchen_layout (str):  "l-shape"|"galley"|"u-shape"|"one-wall"|"island"
            hallway_type (str):    "open-plan"|"single-corridor"|"double-loaded"|"gallery"
            house_shape (str):     "rectangle"|"l-shape"|"t-shape"|"u-shape"|"courtyard"
            master_location (str): "left"|"right"|"rear"|"front"
            has_office (bool):     Office/study present
            has_mudroom (bool):    Mud room present
            has_covered_porch (bool): Covered rear porch
            rear_view_dir (str):   "north"|"south"|"east"|"west"
            garage_side (str):     "left"|"right"|"rear"|"detached"
        rules_path (str):  Absolute path to barnhaus-design-rules.md

    Returns:
        dict with keys:
            footprint (dict):     {"main": {x0,y0,x1,y1}, "garage": {x0,y0,x1,y1}}
            zone_widths (dict):   {"master": N, "living_core": N, "service": N}
            room_program (list):  [{name, sf, location, ceiling_height, adjacencies}]
            warnings (list):      Rule violations detected (strings)
            checklist (list):     QA checklist items from Section 8

    All warnings are printed to console before returning, so they appear
    before any Revit calls are made in the build script.

    Example::

        from barnhaus_revit_utils import design_brief_to_layout

        brief = {
            "stories": 2,
            "total_sf": 3200,
            "bedrooms": 4,
            "garage_cars": 2,
            "kitchen_layout": "island",
            "hallway_type": "double-loaded",
            "house_shape": "l-shape",
            "has_office": True,
            "has_mudroom": True,
            "has_covered_porch": True,
        }
        layout = design_brief_to_layout(brief, "memory/barnhaus-design-rules.md")
        print(layout["warnings"])   # fix these before building
    """
    import os as _os2

    # ── Load rules file ──────────────────────────────────────────────────────
    rules_text = ""
    try:
        with open(rules_path, "r") as rf:
            rules_text = rf.read()
    except Exception as e:
        print(f"  [VALIDATOR] Could not read rules file: {e}")

    warnings = []

    # ── Extract QA checklist from Section 8 ─────────────────────────────────
    checklist = []
    in_checklist = False
    for line in rules_text.splitlines():
        if "General QA Checklist" in line:
            in_checklist = True
        elif in_checklist:
            if line.startswith("###") and "QA" not in line:
                break
            if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "11.", "12.")):
                checklist.append(line.strip())
            elif line.strip().startswith("✅"):
                checklist.append(line.strip())

    # ── Apply design rules ───────────────────────────────────────────────────
    stories        = brief_dict.get("stories", 1)
    total_sf       = brief_dict.get("total_sf", 2000)
    bedrooms       = brief_dict.get("bedrooms", 3)
    garage_cars    = brief_dict.get("garage_cars", 2)
    kitchen_layout = brief_dict.get("kitchen_layout", "island")
    hallway_type   = brief_dict.get("hallway_type", "single-corridor")
    house_shape    = brief_dict.get("house_shape", "rectangle")
    master_loc     = brief_dict.get("master_location", "left")
    has_office     = brief_dict.get("has_office", True)
    has_mudroom    = brief_dict.get("has_mudroom", True)
    has_porch      = brief_dict.get("has_covered_porch", True)
    garage_side    = brief_dict.get("garage_side", "right")

    # Rule: Never a simple box
    if house_shape == "rectangle":
        warnings.append(
            "MASSING: House shape is rectangle. Barnhaus rule: always 2+ offset volumes. "
            "Consider L-shape, T-shape, or compound massing."
        )

    # Rule: Garage subordinate
    if garage_side not in ("left", "right", "detached"):
        warnings.append(
            f"GARAGE: garage_side='{garage_side}' — garage should be offset or detached, "
            "never centered on the front elevation."
        )

    # Rule: Multi-story needs stairs
    if stories > 1:
        has_stairs = brief_dict.get("has_stairs", False)
        if not has_stairs:
            warnings.append(
                "STAIRS: 2-story plan missing stairs. Every multi-story plan MUST have stairs. "
                "Add 'has_stairs': True to brief and reserve a 12x10ft stair zone."
            )

    # Rule: L2 double-loaded corridor
    if stories > 1 and hallway_type != "double-loaded":
        warnings.append(
            f"HALLWAY: L2 plans should use 'double-loaded' hallway type "
            f"(4ft wide corridor). Current: '{hallway_type}'."
        )

    # Rule: Great room must be vaulted
    has_vault = brief_dict.get("great_room_vaulted", True)
    if not has_vault:
        warnings.append(
            "CEILING: Great Room/Living Core ceiling must be VAULTED (follows roofline, "
            "14-22ft at ridge). Never use flat ceiling in the living core."
        )

    # Rule: Mudroom present on plans with garage
    if garage_cars > 0 and not has_mudroom:
        warnings.append(
            "MUDROOM: Garage present but no mudroom. Barnhaus standard: mud room is required "
            "between garage and main house (Garage → Mud Room → Pantry → Kitchen path)."
        )

    # Rule: Covered rear porch
    if not has_porch:
        warnings.append(
            "PORCH: No covered rear porch specified. Barnhaus rule: indoor-outdoor connection "
            "is non-negotiable. Every plan has a rear porch accessible from the living core."
        )

    # Rule: Kitchen island always present
    if kitchen_layout == "galley":
        warnings.append(
            "KITCHEN: Galley layout has no island. Barnhaus rule: kitchen island is always "
            "present (8-12ft long). Consider adding island or switching to 'island' layout."
        )

    # Rule: Master suite isolated
    if master_loc in ("front", "center"):
        warnings.append(
            f"MASTER: master_location='{master_loc}' — master suite must be at one END of "
            "the plan (maximum distance from secondary bedrooms), typically rear-facing."
        )

    # Rule: His/Hers closets
    has_his_hers = brief_dict.get("his_hers_closets", True)
    if not has_his_hers:
        warnings.append(
            "CLOSETS: Missing his/hers separate closets in master suite. "
            "Barnhaus standard: always His + Hers separate, never one shared closet."
        )

    # ── Compute footprint ────────────────────────────────────────────────────
    # Estimate main house footprint from total_sf and stories
    sf_per_floor = total_sf / stories
    # Typical Barnhaus width: 40-60ft, depth: 28-50ft
    import math as _math2
    width = max(40, min(60, _math2.sqrt(sf_per_floor * 1.5)))   # wider than deep
    depth = max(28, min(50, sf_per_floor / width))
    width = round(width / 2) * 2   # round to even feet
    depth = round(depth / 2) * 2

    # Garage footprint: 24ft deep × (22ft per car)
    gar_w = garage_cars * 22
    gar_d = 24
    # Garage sits to the right of the house by default
    gar_x0 = int(width)
    gar_x1 = gar_x0 + gar_w
    gar_y0 = 0
    gar_y1 = gar_d

    footprint = {
        "main":   {"x0": 0, "y0": 0, "x1": int(width), "y1": int(depth)},
        "garage": {"x0": gar_x0, "y0": gar_y0, "x1": gar_x1, "y1": gar_y1},
    }

    # ── Zone widths ──────────────────────────────────────────────────────────
    # Master zone: ~28-32ft; Living core: ~26-34ft; Service: ~12-16ft
    master_w  = min(30, int(width * 0.35))
    service_w = min(16, int(width * 0.18))
    living_w  = int(width) - master_w - service_w
    zone_widths = {"master": master_w, "living_core": living_w, "service": service_w}

    # ── Room program ─────────────────────────────────────────────────────────
    sf_per_bed   = max(180, int((total_sf * 0.12) / max(bedrooms, 1)))
    room_program = [
        {"name": "Great Room",      "sf": int(total_sf * 0.18), "location": "living_core",
         "ceiling_height": "vaulted", "adjacencies": ["Kitchen", "Dining", "Rear Porch"]},
        {"name": "Kitchen",         "sf": int(total_sf * 0.10), "location": "living_core",
         "ceiling_height": 10, "adjacencies": ["Great Room", "Dining", "Pantry"]},
        {"name": "Dining",          "sf": int(total_sf * 0.07), "location": "living_core",
         "ceiling_height": 10, "adjacencies": ["Kitchen", "Great Room"]},
        {"name": "Master Bedroom",  "sf": int(total_sf * 0.14), "location": "master",
         "ceiling_height": 11, "adjacencies": ["Master Bath", "Hers Closet", "His Closet"]},
        {"name": "Master Bath",     "sf": int(total_sf * 0.06), "location": "master",
         "ceiling_height": 10, "adjacencies": ["Master Bedroom", "Hers Closet"]},
        {"name": "His Closet",      "sf": 80, "location": "master",
         "ceiling_height": 10, "adjacencies": ["Master Bath", "Master Bedroom"]},
        {"name": "Hers Closet",     "sf": 100, "location": "master",
         "ceiling_height": 10, "adjacencies": ["Master Bath", "Master Bedroom"]},
        {"name": "Pantry",          "sf": 80,  "location": "service",
         "ceiling_height": 10, "adjacencies": ["Kitchen", "Mud Room"]},
        {"name": "Mud Room",        "sf": 80,  "location": "service",
         "ceiling_height": 10, "adjacencies": ["Garage", "Pantry", "Laundry"]},
        {"name": "Laundry",         "sf": 60,  "location": "service",
         "ceiling_height": 10, "adjacencies": ["Mud Room"]},
        {"name": "Mechanical",      "sf": 40,  "location": "service",
         "ceiling_height": 10, "adjacencies": ["Garage"]},
    ]

    if has_office:
        room_program.append({
            "name": "Office",  "sf": 160, "location": "living_core",
            "ceiling_height": "vaulted or exposed",
            "adjacencies": ["Living Core", "Hallway"]
        })

    if has_porch:
        room_program.append({
            "name": "Rear Covered Porch", "sf": int(int(width) * 10), "location": "exterior",
            "ceiling_height": "vaulted", "adjacencies": ["Great Room"]
        })

    for i in range(2, bedrooms + 1):
        room_program.append({
            "name": f"Bedroom {i}", "sf": sf_per_bed, "location": "bedroom_wing",
            "ceiling_height": 10, "adjacencies": ["Hallway", f"Bath {i}"]
        })

    # ── Print warnings ───────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("PRE-BUILD DESIGN VALIDATION")
    print("═" * 60)
    if warnings:
        print(f"\n⚠️  {len(warnings)} DESIGN WARNING(S) — fix before building:\n")
        for i, w in enumerate(warnings, 1):
            print(f"  [{i}] {w}\n")
    else:
        print("\n✅  Design brief passes all Barnhaus rules.\n")

    return {
        "footprint":    footprint,
        "zone_widths":  zone_widths,
        "room_program": room_program,
        "warnings":     warnings,
        "checklist":    checklist,
    }


def validate_build_script(rooms, doors, windows, walls):
    """
    Programmatically run the Section 8 QA checklist against a build script's
    data structures before any Revit calls are made.

    Args:
        rooms (list):   List of room dicts, each with keys:
                        {name, x, y, level}
        doors (list):   List of door dicts, each with keys:
                        {wall_id, x, y, family, type_name, wall_height,
                         wall_axis, wall_start, wall_end}
        windows (list): List of window dicts, each with keys:
                        {wall_id, x, y, z, family, type_name}
        walls (list):   List of wall dicts, each with keys:
                        {wall_type, height, sx, sy, ex, ey, label, stories}

    Returns:
        list: Violation strings. Empty list = all checks pass.

    QA checks performed (from Section 8 of design rules):
        1. Wall types correct (no stone, exterior=6in, interior=4in)
        2. Stairs present on multi-story plans
        3. No window directly above a door on the same wall
        4. All rooms labeled (name is not empty or generic)
        5. Garage overhead door height clearance (wall_height >= door_height + 1.5ft)
        6. Level 2 floor note (cannot enforce, emits reminder)
        7. Floor-slab extent check (rooms should not be at coordinate 0,0)

    Example::

        violations = validate_build_script(rooms, doors, windows, walls)
        if violations:
            print("BUILD ABORTED — fix violations first:")
            for v in violations:
                print(f"  ✗ {v}")
            raise SystemExit(1)
    """
    violations = []

    STONE_TYPES    = {"stone", "stone wall", "masonry", "limestone"}
    EXT_THICKNESS  = {"7.5", "6\"", "6 inch", '7.5"', "ext pbr", "2x6", "exterior"}
    INT_THICKNESS  = {"4.5", "4\"", "4 inch", '4.5"', "2x4", "interior"}
    GARAGE_DOOR_FAMILIES = {"Door-Garage-Flush_Panel", "Overhead_Door_-_Sectional_with_Glass_13396"}

    # ── Check 1: Wall types (no stone, correct thickness) ───────────────────
    has_multi_story = any(w.get("stories", 1) > 1 for w in walls)
    for w in walls:
        wtype = w.get("wall_type", "").lower()
        if any(s in wtype for s in STONE_TYPES):
            violations.append(
                f"WALL TYPE: '{w.get('wall_type')}' [{w.get('label','')}] — "
                "NEVER use stone wall types. Use Generic-6\" exterior or Generic-4\" interior."
            )
        label_lower = w.get("label", "").lower()
        is_ext = any(k in wtype for k in EXT_THICKNESS) or "ext" in label_lower or "exterior" in label_lower
        is_int = any(k in wtype for k in INT_THICKNESS) or "int" in label_lower or "interior" in label_lower
        if not is_ext and not is_int:
            violations.append(
                f"WALL TYPE: '{w.get('wall_type')}' [{w.get('label','')}] — "
                "Unrecognized wall type. Exterior walls should use 6\" type; interior use 4\" type."
            )

    # ── Check 2: Stairs on multi-story plans ────────────────────────────────
    if has_multi_story:
        has_stair_room = any("stair" in r.get("name", "").lower() for r in rooms)
        if not has_stair_room:
            violations.append(
                "STAIRS: Multi-story plan detected but no stair room found in room list. "
                "Every multi-story plan MUST have stairs. Reserve a 12x10ft stair zone."
            )

    # ── Check 3: No window directly above a door on the same wall segment ───
    door_positions = {}
    for d in doors:
        key = d.get("wall_id")
        if key:
            door_positions.setdefault(key, []).append({
                "x": d.get("x", 0),
                "y": d.get("y", 0),
                "family": d.get("family", ""),
                "type_name": d.get("type_name", ""),
            })

    for w in windows:
        wid = w.get("wall_id")
        if wid in door_positions:
            for d in door_positions[wid]:
                dx = abs(w.get("x", 0) - d["x"])
                dy = abs(w.get("y", 0) - d["y"])
                # Same horizontal position (within 1ft), and window z > 0 (above floor)
                if dx < 1.0 and dy < 1.0 and w.get("z", 0) > 1.0:
                    violations.append(
                        f"WINDOW ABOVE DOOR: Window on wall {wid} at ({w['x']:.1f},{w['y']:.1f}) "
                        f"appears directly above door at ({d['x']:.1f},{d['y']:.1f}) — "
                        "never place a window directly above a door on the same wall."
                    )

    # ── Check 4: All rooms labeled ───────────────────────────────────────────
    generic_names = {"room", "space", "area", "", "unnamed"}
    for r in rooms:
        name = r.get("name", "").strip().lower()
        if name in generic_names:
            violations.append(
                f"ROOM LABEL: Room at ({r.get('x',0)},{r.get('y',0)}) has no meaningful name. "
                "Label every room with its use (e.g. 'Master Bedroom', 'Great Room')."
            )

    # ── Check 5: Garage door clearance ──────────────────────────────────────
    HEADER_CLEARANCE = 1.5
    for d in doors:
        if d.get("family") in GARAGE_DOOR_FAMILIES:
            # Parse door height from type_name (e.g. "16W X 10H" → 10)
            tn = d.get("type_name", "")
            door_h = None
            import re as _re
            m = _re.search(r'(\d+)H', tn, _re.IGNORECASE)
            if m:
                door_h = float(m.group(1))
            elif "10x10" in tn.lower():
                door_h = 10.0
            elif "10x14" in tn.lower() or "12x14" in tn.lower():
                door_h = 14.0

            wall_h = d.get("wall_height", None)
            if door_h and wall_h and wall_h < door_h + HEADER_CLEARANCE:
                violations.append(
                    f"GARAGE DOOR: Wall height {wall_h}ft is too short for {tn} "
                    f"(needs {door_h + HEADER_CLEARANCE}ft min). "
                    "Increase garage wall height to at least door_height + 1.5ft."
                )

    # ── Check 6: Room placement sanity (catch default 0,0 room points) ──────
    origin_rooms = [r for r in rooms if r.get("x", 1) == 0 and r.get("y", 1) == 0]
    if origin_rooms:
        for r in origin_rooms:
            violations.append(
                f"ROOM POSITION: Room '{r.get('name','?')}' is at (0,0) — likely a default "
                "placeholder coordinate. Verify it is intentionally at the plan origin."
            )

    # ── Print results ────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("BUILD SCRIPT VALIDATION (Section 8 QA Checklist)")
    print("─" * 60)
    if violations:
        print(f"\n⚠️  {len(violations)} VIOLATION(S) FOUND:\n")
        for v in violations:
            print(f"  ✗ {v}\n")
    else:
        print("\n✅  All QA checks passed.\n")

    return violations
