"""
barnhaus_revit_utils_v2.py
Clean rewrite — designed top-down from the model JSON output schema.

Key improvements over v1:
- Compass directions (N/S/E/W) instead of rotation degrees
- All family/type names sourced from revit_template_manifest.json
- Named constants for offsets — no magic numbers
- Stage checkpointing — resume from last completed stage
- Dry-run mode — preview without hitting Revit
- Consistent error handling — every call returns success/error
- Single polygon floor always — no adjacent zone overlaps
"""

import requests
import json
import os
import time

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BRIDGE_URL = "http://localhost:3000/execute"
CHECKPOINT_FILE = "/tmp/revit_stage_checkpoint.json"
DRY_RUN = False  # Set True to preview without touching Revit

# ─────────────────────────────────────────────
# LEVELS (from manifest)
# ─────────────────────────────────────────────
LEVEL = {
    "L1":       "Level 1.0",    # z = 0
    "L1_ROOF":  "L1 Roof",      # z = 10
    "L2":       "Level 2.0",    # z = 11
    "GAR_ROOF": "Garage Roof",  # z = 12
    "L2_ROOF":  "L2 Roof",      # z = 20
}

# ─────────────────────────────────────────────
# WALL TYPES
# ─────────────────────────────────────────────
WALL = {
    "EXT":  "Wall 7.5\" EXT PBR",
    "INT":  "Wall 4.5 Interior\"",
}

# ─────────────────────────────────────────────
# CABINET OFFSETS (ft from wall face)
# Named so intent is clear — no magic numbers
# ─────────────────────────────────────────────
BASE_CAB_DEPTH   = 2.0   # 24" base cabinet depth
UPPER_CAB_DEPTH  = 1.0   # 12" upper cabinet depth
APPL_DEPTH       = 2.0   # appliance depth (fridge, range, DW)
SINK_HALF_DEPTH  = 0.875 # sink origin is center, 21" total
TOILET_HALF      = 1.25  # toilet origin is center
SHOWER_HALF      = 0.5   # shower placed close to wall

# Wall offset = wall thickness/2 + fixture depth/2
# For PBR ext wall: 0.625ft thick → back of cab at wall + 0.625 + depth
EXT_WALL_OFFSET = 0.625  # half of 7.5" wall
INT_WALL_OFFSET = 0.375  # half of 4.5" wall

# ─────────────────────────────────────────────
# ROTATION CONVENTION
# Converts compass face direction to Revit rotation degrees
# Face = direction the FRONT of the fixture points toward
# ─────────────────────────────────────────────
FACE_TO_ROT = {
    "S":  0,    # front faces south (fixture against north wall)
    "N":  180,  # front faces north (fixture against south wall)
    "E":  90,   # front faces east  (fixture against west wall)
    "W":  270,  # front faces west  (fixture against east wall)
}

def face_to_rotation(face: str) -> float:
    """Convert compass direction to Revit rotation degrees."""
    rot = FACE_TO_ROT.get(face.upper())
    if rot is None:
        raise ValueError(f"Invalid face direction '{face}'. Use N/S/E/W.")
    return rot

# ─────────────────────────────────────────────
# WALL FACE CONVENTION
# wall_face = which wall the fixture is against
# fixture front faces INTO the room (away from wall)
# ─────────────────────────────────────────────
WALL_FACE_TO_FRONT = {
    "N": "S",   # against north wall → faces south (rotation=0)
    "S": "N",   # against south wall → faces north (rotation=180)
    "W": "E",   # against west wall  → faces east  (rotation=90)
    "E": "W",   # against east wall  → faces west  (rotation=270)
}

# ─────────────────────────────────────────────
# FAMILY / TYPE CATALOG (from manifest)
# ─────────────────────────────────────────────

# DOORS
DOOR = {
    # Interior
    "int_single":       ("Door-Interior-Single-1_Panel-Wood", "32\" x 96\""),
    "int_single_30":    ("Door-Interior-Single-1_Panel-Wood", "30\" x 96\""),
    "int_single_36":    ("Door-Interior-Single-1_Panel-Wood", "36\" x 96\""),
    "int_single_28":    ("Door-Interior-Single-1_Panel-Wood", "28\""),
    "int_pocket":       ("Door-Interior-Single-Pocket-2_Panel-Wood", "36\" x 96\""),
    "int_barn":         ("Interior_barn_door_18732", "Interior_barn_door_18732"),
    "int_bifold":       ("4_Panel_Bifold_Door_18619", "72\" x 84\""),
    "int_double_slide": ("Door-Interior-Double-Sliding-2_Panel-Wood", "72\" x 96\""),
    "int_opening":      ("Int-Opening-Craftsman_Casing_1726", "36\" x 96\""),
    "int_opening_wide": ("Int-Opening-Craftsman_Casing_1726", "Wide"),
    "int_opening_48":   ("Int-Opening-Craftsman_Casing_1726", "48\""),
    "int_opening_72":   ("Int-Opening-Craftsman_Casing_1726", "72\""),
    # Exterior
    "ext_single":       ("Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", "36\" x 96\""),
    "ext_double_glass": ("Door-Exterior-Double-Full Glass-Wood_Clad", "72\" x 96\""),
    "ext_slide_6":      ("Exterior_Sliding_Door_3843", "6'-0\"W. x 8'-0\"H."),
    "ext_slide_8":      ("Exterior_Sliding_Door_3843", "8'-0\"W. x 8'-0\"H. 2"),
    "ext_3panel_slide": ("Three_Panel_Sliding_Door_17534", "108\" x 84\""),
    "ext_4panel_slide": ("Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00"),
    "ext_anderson":     ("Door-Inswing-Andersen-E_Series-Double", "6080 EXT"),
    # Garage / overhead
    "gar_oh_10x10":     ("Door-Garage-Flush_Panel", "10x10"),
    "gar_oh_10x14":     ("Door-Garage-Flush_Panel", "10x14"),
    "gar_oh_16x10":     ("Door-Garage-Flush_Panel", "16W X 10H"),
    "gar_oh_12x12":     ("Door-Garage-Flush_Panel", "12 X 12"),
    "gar_oh_12x14":     ("Door-Garage-Flush_Panel", "12X14"),
    "gar_oh_glass_10":  ("Overhead_Door_-_Sectional_with_Glass_13396", "10'W X 12'H"),
    "gar_oh_glass_16":  ("Overhead_Door_-_Sectional_with_Glass_13396", "16' W X 8' H"),
    # Bath
    "shower_door":      ("Frameless_Glass_shower_door_19168", "2'-6\" x 8'-0\""),
    "shower_double":    ("Double_Glass_Sliding_Shower_Door_20748", "Interior - Double Sliding Glass Shower Door"),
}

# WINDOWS
WINDOW = {
    # Fixed
    "fx_72x36":  ("Instance-Window-Fixed", "72\" x 36\""),
    "fx_60x24":  ("Instance-Window-Fixed", "60\" x 24\""),
    "fx_48x96":  ("Instance-Window-Fixed", "48\" x 96\""),
    "fx_24x96":  ("Instance-Window-Fixed", "24\" x 96\""),
    "fx_72x24":  ("Instance-Window-Fixed", "72\" x 24\""),
    "fx_72x30":  ("Instance-Window-Fixed", "72\" x 30\""),
    "fx_6080":   ("Instance-Window-Fixed", "6080 FX"),
    "fx_48x48":  ("Instance-Window-Fixed", "48\" x 48\""),
    "fx_60x30":  ("Instance-Window-Fixed", "60\" x 30\""),
    # Transom / clerestory
    "cl_6020":   ("Window-Double_Hung_Transom-Andersen-E_Series", "6020 FX"),
    "cl_5020":   ("Window-Double_Hung_Transom-Andersen-E_Series", "5020 FX"),
    "cl_4040":   ("Window-Double_Hung_Transom-Andersen-E_Series", "4040 FX"),
    "cl_3026":   ("Window-Double_Hung_Transom-Andersen-E_Series", "3026 FX"),
    "cl_4620":   ("Window-Double_Hung_Transom-Andersen-E_Series", "4620 FX"),
    # Single hung (operable)
    "sh_3060":   ("Window-Double_Hung-Andersen-E_Series", "3060 SH"),
    "sh_3050":   ("Window-Double_Hung-Andersen-E_Series", "3050 SH"),
    "sh_3040":   ("Window-Double_Hung_Transom-Andersen-E_Series", "3040 SH"),
    # Awning
    "aw_36x60":  ("Window-Awning-Single", "36\" x 60\""),
    "aw_36x72":  ("Window-Awning-Single", "36\" x 72\""),
    "aw_24x72":  ("Window-Awning-Single", "24\" x 72\""),
    # Casement
    "ca_36x60":  ("Window-Casement-Single_Left", "36\" x 60\""),
}

# CASEWORK (cabinets)
CABINET = {
    # Base
    "base_dd_36":    ("Base Cabinet-Double Door & 1 Drawer", "36\""),
    "base_dd_30":    ("Base Cabinet-Double Door & 1 Drawer", "30\""),
    "base_dd_24":    ("Base Cabinet-Double Door & 1 Drawer", "24\""),
    "base_sink_36":  ("Base Cabinet-Double Door Sink Unit", "36\""),
    "base_sink_30":  ("Base Cabinet-Double Door Sink Unit", "30\""),
    "base_3drw_36":  ("Base Cabinet-3 Drawers", "36\""),
    "base_3drw_24":  ("Base Cabinet-3 Drawers", "24\""),
    "base_shelf_36": ("Base Cabinet-Shelf Unit", "36\""),
    # Upper
    "upper_dd_36":   ("Upper Cabinet-Double Door-Wall", "36\""),
    "upper_dd_30":   ("Upper Cabinet-Double Door-Wall", "30\""),
    "upper_dd_42":   ("Upper Cabinet-Double Door-Wall", "42\""),
    "upper_sd_24":   ("Upper Cabinet-Single Door-Wall", "24\""),
    # Tall / pantry
    "tall_dd_36":    ("Tall Cabinet-Double Door", "36\""),
    "tall_dd_42":    ("Tall Cabinet-Double Door", "42\""),
    "tall_dd_48":    ("Tall Cabinet-Double Door", "48\""),
    "tall_shelf_36": ("Tall Cabinet-Shelf Unit(2)", "36\""),
    # Vanity
    "van_dd_36":     ("Vanity Cabinet-Double Door & 1 Drawer", "36\""),
    "van_dd_30":     ("Vanity Cabinet-Double Door & 1 Drawer", "30\""),
    "van_sink_36":   ("Vanity Cabinet-Double Door Sink Unit", "36\""),
    "van_sink_30":   ("Vanity Cabinet-Double Door Sink Unit", "30\""),
    "van_3drw_24":   ("Vanity Cabinet-3 Drawers", "24\""),
}

# PLUMBING
PLUMBING = {
    "toilet":       ("Toilet-Domestic-3D", "Toilet-Domestic-3D"),
    "tub_rect":     ("Tub-Rectangular-3D", "Tub-Rectangular-3D"),
    "tub_freestand":("Tub-Free Standing-3D", "30\" x 60\""),
    "sink_kitchen": ("Sink Kitchen-Single", "30\" x 21\""),
    "sink_island":  ("Sink Kitchen-Island", "18\" x 18\""),
    "sink_vanity":  ("Sink Vanity-Square", "20\" x 18\""),
    "washer_dryer": ("Washer-Dryer-Stack", "27\" x 30\""),
    "shower_col":   ("Shower_columns_15486", "Shower_columns_15486"),
}

# COLUMNS
COLUMN = {
    "hss6x6":  ("HSS-Hollow Structural Section-Column", "HSS6X6X3/16"),
    "hss4x4":  ("HSS-Hollow Structural Section-Column", "HSS4X4X3/8"),
    "wf_W10":  ("W-Wide Flange-Column", "W10X12"),
}

# ─────────────────────────────────────────────
# BRIDGE COMMUNICATION
# ─────────────────────────────────────────────

def _call(tool: str, payload: dict) -> dict:
    """Send a command to the Revit bridge. Returns response dict."""
    if DRY_RUN:
        print(f"[DRY RUN] {tool}: {json.dumps(payload, indent=2)}")
        return {"success": True, "dry_run": True}

    req_id = f"{tool}_{int(time.time()*1000)}"
    body = {"request_id": req_id, "tool": tool, "payload": payload}

    try:
        r = requests.post(BRIDGE_URL, json=body, timeout=30)
        r.raise_for_status()
        raw = r.json()
        # Normalize DLL response (Status/Result) to internal (success/result/error)
        status = raw.get("Status") or raw.get("status", "")
        result = raw.get("Result") or raw.get("result")
        message = raw.get("Message") or raw.get("message", "")
        return {
            "success": status.lower() == "ok",
            "result": result,
            "error": message if status.lower() != "ok" else None,
            "raw": raw
        }
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Bridge not reachable. Is Revit open with DLL loaded?"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def health_check() -> bool:
    """Check bridge is alive. Returns True if healthy."""
    try:
        r = requests.get("http://localhost:3000/health", timeout=5)
        data = r.json()
        if data.get("status") == "healthy":
            print(f"✅ Bridge healthy — Revit {data.get('revit_version')}, doc: {data.get('active_document')}")
            return True
        print(f"⚠️  Bridge unhealthy: {data}")
        return False
    except Exception as e:
        print(f"❌ Bridge unreachable: {e}")
        return False


# ─────────────────────────────────────────────
# STAGE CHECKPOINTING
# ─────────────────────────────────────────────

def checkpoint_save(submission_id: str, stage: int, element_ids: list):
    """Save completed element IDs for a stage so we can resume."""
    data = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
    if submission_id not in data:
        data[submission_id] = {}
    data[submission_id][f"stage_{stage}"] = element_ids
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Checkpoint saved: {submission_id} stage {stage} ({len(element_ids)} elements)")


def checkpoint_load(submission_id: str, stage: int) -> list:
    """Load element IDs from a previous stage run."""
    if not os.path.exists(CHECKPOINT_FILE):
        return []
    with open(CHECKPOINT_FILE) as f:
        data = json.load(f)
    return data.get(submission_id, {}).get(f"stage_{stage}", [])


def checkpoint_clear(submission_id: str):
    """Clear all checkpoints for a submission (fresh start)."""
    if not os.path.exists(CHECKPOINT_FILE):
        return
    with open(CHECKPOINT_FILE) as f:
        data = json.load(f)
    data.pop(submission_id, None)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"🗑️  Checkpoints cleared for {submission_id}")


# ─────────────────────────────────────────────
# WALLS
# ─────────────────────────────────────────────

def get_wall_orientation(wall_id: int) -> dict:
    """Get wall exterior face orientation vector."""
    result = _call("revit.get_wall_orientation", {"wall_id": wall_id})
    if result.get("success"):
        return result.get("result", {}).get("orientation")
    return None


def flip_wall(wall_id: int) -> bool:
    """Flip a wall's facing direction."""
    result = _call("revit.flip_wall", {"wall_id": wall_id})
    return result.get("success", False)


def verify_wall_facing(wall_id: int, expected_nx: float, expected_ny: float, label: str = ""):
    """
    Check wall exterior face orientation and flip if wrong.
    Expected normals: south wall=(0,-1), north=(0,+1), east=(+1,0), west=(-1,0)
    """
    orient = get_wall_orientation(wall_id)
    if orient is None:
        print(f"  [FACING] could not get orientation for wall {wall_id}")
        return
    ox, oy = orient.get("x", 0), orient.get("y", 0)
    correct = (
        (expected_nx == 0 or (expected_nx > 0 and ox > 0.5) or (expected_nx < 0 and ox < -0.5)) and
        (expected_ny == 0 or (expected_ny > 0 and oy > 0.5) or (expected_ny < 0 and oy < -0.5))
    )
    if not correct:
        print(f"  [FACING] {label} wall {wall_id} facing wrong ({ox:.1f},{oy:.1f}), "
              f"expected ({expected_nx},{expected_ny}) — flipping")
        flip_wall(wall_id)
    else:
        print(f"  [FACING] {label} wall {wall_id} ok ({ox:.1f},{oy:.1f})")


def create_wall(x0: float, y0: float, x1: float, y1: float,
                wall_type: str = WALL["EXT"],
                level: str = LEVEL["L1"],
                height: float = 11.0,
                upper_limit_level: str = None,
                label: str = "") -> dict:
    """Create a single wall segment."""
    payload = {
        "start_point": {"x": x0, "y": y0, "z": 0},
        "end_point":   {"x": x1, "y": y1, "z": 0},
        "wall_type": wall_type,
        "level": level,
        "height": height,
        "label": label,
    }
    if upper_limit_level:
        payload["upper_limit_level"] = upper_limit_level
    result = _call("revit.create_wall", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Wall failed [{label}]: {result.get('error')}")
    return result


def create_rect_exterior(x0: float, y0: float, x1: float, y1: float,
                          wall_type: str = WALL["EXT"],
                          level: str = LEVEL["L1"],
                          height: float = 11.0,
                          upper_limit_level: str = None) -> list:
    """Create 4 exterior walls forming a rectangle. Returns list of results."""
    walls = [
        (x0, y0, x1, y0, "S wall"),
        (x1, y0, x1, y1, "E wall"),
        (x1, y1, x0, y1, "N wall"),
        (x0, y1, x0, y0, "W wall"),
    ]
    results = []
    for wx0, wy0, wx1, wy1, label in walls:
        r = create_wall(wx0, wy0, wx1, wy1, wall_type, level, height, upper_limit_level, label)
        results.append(r)
    return results


# ─────────────────────────────────────────────
# FLOORS
# ─────────────────────────────────────────────

def create_floor_polygon(boundary_points: list,
                          floor_type: str = "Floor 6\" Concrete",
                          level: str = LEVEL["L1"],
                          label: str = "") -> dict:
    """
    Create a floor from a polygon boundary.
    boundary_points: list of {x, y} dicts tracing the perimeter.
    Always use ONE polygon per building — never call twice for adjacent zones.
    """
    payload = {
        "boundary_points": boundary_points,
        "level": level,
        "label": label,
    }
    if floor_type:
        payload["floor_type"] = floor_type
    result = _call("revit.create_floor", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Floor failed [{label}]: {result.get('error')}")
    return result


# ─────────────────────────────────────────────
# ROOFS
# ─────────────────────────────────────────────

def make_roof(boundary_points: list,
              roof_type: str = "Basic Roof: Metal Standing Seam",
              level_name: str = LEVEL["L1_ROOF"],
              pitch: float = 4.0,
              label: str = "") -> dict:
    """Create a roof element."""
    payload = {
        "boundary_points": boundary_points,
        "roof_type": roof_type,
        "level": level_name,
        "pitch": pitch,
        "slope_style": "shed",
        "shed_low_edge": 2,
        "label": label,
    }
    result = _call("revit.create_roof", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Roof failed [{label}]: {result.get('error')}")
    return result


# ─────────────────────────────────────────────
# DOORS
# ─────────────────────────────────────────────

def place_door(wall_id: int, x: float, y: float,
               family: str, type_name: str,
               face: str = "S",
               z: float = 0,
               level: str = LEVEL["L1"],
               label: str = "") -> dict:
    """
    Place a door on a wall.
    face: compass direction the door SWINGS toward (N/S/E/W).
    """
    payload = {
        "wall_id": wall_id,
        "location": {"x": x, "y": y, "z": z},
        "family_name": family,
        "type_name": type_name,
        "level": level,
        "label": label,
    }
    result = _call("revit.place_door", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Door failed [{label}]: {result.get('error')}")
    return result


# ─────────────────────────────────────────────
# WINDOWS
# ─────────────────────────────────────────────

def place_window(wall_id: int, x: float, y: float,
                 family: str, type_name: str,
                 sill_height: float = 3.0,
                 level: str = LEVEL["L1"],
                 label: str = "") -> dict:
    """Place a window on a wall at given sill height."""
    payload = {
        "wall_id": wall_id,
        "location": {"x": x, "y": y, "z": sill_height},
        "family_name": family,
        "type_name": type_name,
        "level": level,
        "label": label,
    }
    result = _call("revit.place_window", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Window failed [{label}]: {result.get('error')}")
    return result


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

def place_fixture(family: str, type_name: str,
                  x: float, y: float,
                  face: str,
                  level: str = LEVEL["L1"],
                  label: str = "") -> dict:
    """
    Place a fixture (cabinet, plumbing, appliance) at x,y facing compass direction.
    face: which direction the FRONT of the fixture faces (N/S/E/W).
    """
    payload = {
        "family_name": family,
        "type_name": type_name,
        "location": {"x": x, "y": y, "z": 0},
        "rotation": face_to_rotation(face),
        "level": level,
        "label": label,
    }
    result = _call("revit.place_family_instance", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Fixture failed [{label}]: {result.get('error')}")
    return result


def place_against_wall(family: str, type_name: str,
                        wall_coord: float,
                        position_along: float,
                        wall_face: str,
                        fixture_depth: float,
                        wall_thickness: float = None,
                        level: str = LEVEL["L1"],
                        label: str = "",
                        door_positions: list = None) -> dict:
    """
    Place a fixture flush against a wall.

    wall_coord: the fixed axis value of the wall (x if N/S wall, y if E/W wall)
    position_along: the varying axis value (center of fixture along wall)
    wall_face: which wall the fixture is against (N/S/E/W)
    fixture_depth: how deep the fixture is (ft) — origin to back face
    wall_thickness: defaults to EXT_WALL_OFFSET if None (assumes exterior wall)
    door_positions: list of (door_center, door_width, clearance) tuples to skip

    fixture FRONT faces INTO the room (away from wall).
    """
    wt = wall_thickness if wall_thickness is not None else INT_WALL_OFFSET

    # Check door conflicts
    if door_positions:
        for door_center, door_width, clearance in door_positions:
            min_pos = door_center - door_width/2 - clearance
            max_pos = door_center + door_width/2 + clearance
            if min_pos <= position_along <= max_pos:
                print(f"[DOOR CONFLICT] Skipping {label} at {position_along} — too close to door at {door_center}")
                return {"success": False, "error": "door_conflict", "label": label}

    # Determine front face (fixture faces away from wall)
    front_face = WALL_FACE_TO_FRONT[wall_face.upper()]

    # Compute x,y based on which wall
    offset = wt + fixture_depth / 2
    if wall_face.upper() in ("N", "S"):
        # Wall runs E-W, coord is y
        y = wall_coord + (offset if wall_face.upper() == "S" else -offset)
        x = position_along
    else:
        # Wall runs N-S, coord is x
        x = wall_coord + (offset if wall_face.upper() == "W" else -offset)
        y = position_along

    return place_fixture(family, type_name, x, y, front_face, level, label)


# ─────────────────────────────────────────────
# COLUMNS / PORCH POSTS
# ─────────────────────────────────────────────

def place_column(x: float, y: float,
                 family: str = COLUMN["hss6x6"][0],
                 type_name: str = COLUMN["hss6x6"][1],
                 base_level: str = LEVEL["L1"],
                 top_level: str = LEVEL["L1_ROOF"],
                 label: str = "") -> dict:
    """Place a structural column."""
    payload = {
        "x": x, "y": y,
        "family": family,
        "type_name": type_name,
        "base_level": base_level,
        "top_level": top_level,
        "label": label,
    }
    result = _call("revit.place_column", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Column failed [{label}]: {result.get('error')}")
    return result


def place_porch_posts(x0: float, x1: float, y: float,
                      spacing: float = 15.0,
                      base_level: str = LEVEL["L1"],
                      top_level: str = LEVEL["L1_ROOF"]) -> list:
    """
    Place evenly-spaced HSS6x6 porch posts along a line.
    x0, x1: start and end along X axis
    y: fixed Y coordinate of post line
    spacing: max spacing between posts (ft)
    """
    import math
    length = abs(x1 - x0)
    n_spans = max(1, math.ceil(length / spacing))
    n_posts = n_spans + 1
    results = []
    for i in range(n_posts):
        px = x0 + (length / n_spans) * i
        r = place_column(px, y, label=f"porch_post_{i}")
        results.append(r)
    return results


# ─────────────────────────────────────────────
# ROOM LABELS
# ─────────────────────────────────────────────

def label_rooms(rooms: list, level: str = LEVEL["L1"]) -> list:
    """
    Place room labels.
    rooms: list of dicts with keys: name, x, y
    Place AFTER fixtures — use same x,y as fixtures for accurate room detection.
    """
    results = []
    for room in rooms:
        payload = {
            "name": room["name"],
            "x": room["x"],
            "y": room["y"],
            "level": level,
        }
        r = _call("revit.place_room", payload)
        if not r.get("success") and not r.get("dry_run"):
            print(f"❌ Room label failed [{room['name']}]: {r.get('error')}")
        results.append(r)
    return results


# ─────────────────────────────────────────────
# WALL UTILITIES
# ─────────────────────────────────────────────

def attach_walls_to_roof(wall_ids: list, roof_id: int) -> list:
    """Attach exterior walls to a roof element."""
    results = []
    for wid in wall_ids:
        r = _call("revit.attach_wall_to_roof", {"wall_id": wid, "roof_id": roof_id})
        results.append(r)
    return results


def flip_door(door_id: int) -> dict:
    """Flip a door's facing direction."""
    return _call("revit.flip_door", {"element_id": door_id})


# ─────────────────────────────────────────────
# CONVENIENCE LOOKUPS
# ─────────────────────────────────────────────

def door(key: str) -> tuple:
    """Get (family, type_name) for a door key."""
    if key not in DOOR:
        raise KeyError(f"Unknown door key '{key}'. Available: {list(DOOR.keys())}")
    return DOOR[key]


def window(key: str) -> tuple:
    """Get (family, type_name) for a window key."""
    if key not in WINDOW:
        raise KeyError(f"Unknown window key '{key}'. Available: {list(WINDOW.keys())}")
    return WINDOW[key]


def cabinet(key: str) -> tuple:
    """Get (family, type_name) for a cabinet key."""
    if key not in CABINET:
        raise KeyError(f"Unknown cabinet key '{key}'. Available: {list(CABINET.keys())}")
    return CABINET[key]


def plumbing(key: str) -> tuple:
    """Get (family, type_name) for a plumbing fixture key."""
    if key not in PLUMBING:
        raise KeyError(f"Unknown plumbing key '{key}'. Available: {list(PLUMBING.keys())}")
    return PLUMBING[key]


# ─────────────────────────────────────────────
# QUICK REFERENCE
# ─────────────────────────────────────────────

def print_catalog():
    """Print all available families and keys."""
    print("\n=== DOORS ===")
    for k, (f, t) in DOOR.items():
        print(f"  {k}: {f} | {t}")
    print("\n=== WINDOWS ===")
    for k, (f, t) in WINDOW.items():
        print(f"  {k}: {f} | {t}")
    print("\n=== CABINETS ===")
    for k, (f, t) in CABINET.items():
        print(f"  {k}: {f} | {t}")
    print("\n=== PLUMBING ===")
    for k, (f, t) in PLUMBING.items():
        print(f"  {k}: {f} | {t}")
    print("\n=== COLUMNS ===")
    for k, (f, t) in COLUMN.items():
        print(f"  {k}: {f} | {t}")
    print("\n=== LEVELS ===")
    for k, v in LEVEL.items():
        print(f"  {k}: {v}")
    print("\n=== ROTATION (face direction) ===")
    for face, deg in FACE_TO_ROT.items():
        print(f"  Face {face} = {deg}°")


if __name__ == "__main__":
    print_catalog()
