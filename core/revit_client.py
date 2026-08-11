"""
revit_client.py — Low-level MCP bridge communication layer.
All Revit API calls go through here.

Bridge URL: http://localhost:3000/execute
Health:     http://localhost:3000/health
"""

import requests
import json
import time
import os
from core.constants import WALL, LEVEL, FACE_TO_ROT, WALL_FACE_TO_FRONT

BRIDGE_URL    = os.environ.get("REVIT_BRIDGE_URL", "http://localhost:3000") + "/execute"
HEALTH_URL    = os.environ.get("REVIT_BRIDGE_URL", "http://localhost:3000") + "/health"
REQUEST_TIMEOUT = 30  # seconds

DRY_RUN = False  # Set True to preview without touching Revit


# ─────────────────────────────────────────────
# CORE CALL
# ─────────────────────────────────────────────

def call(tool: str, payload: dict) -> dict:
    """
    Send a command to the Revit MCP bridge.
    Returns normalized dict: {success, result, error, raw}
    """
    if DRY_RUN:
        print(f"[DRY RUN] {tool}: {json.dumps(payload, indent=2)}")
        return {"success": True, "dry_run": True}

    req_id = f"{tool}_{int(time.time() * 1000)}"
    body = {
        "request_id": req_id,
        "tool": tool,
        "payload": payload,
    }

    try:
        r = requests.post(BRIDGE_URL, json=body, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        raw = r.json()
        status  = (raw.get("Status") or raw.get("status") or "").lower()
        result  = raw.get("Result") or raw.get("result")
        message = raw.get("Message") or raw.get("message", "")
        return {
            "success": status == "ok",
            "result":  result,
            "error":   message if status != "ok" else None,
            "raw":     raw,
        }
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Bridge not reachable — is Revit open with the addin loaded?"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def health_check() -> bool:
    """Returns True if bridge is healthy."""
    try:
        r = requests.get(HEALTH_URL, timeout=5)
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
# WALLS
# ─────────────────────────────────────────────

def create_wall(x0: float, y0: float, x1: float, y1: float,
                wall_type: str = WALL["EXT"],
                level: str = LEVEL["L1"],
                height: float = 11.0,
                upper_limit_level: str = None,
                label: str = "") -> dict:
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
    result = call("revit.create_wall", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Wall failed [{label}]: {result.get('error')}")
    return result


def create_rect_exterior(x0, y0, x1, y1,
                          wall_type=WALL["EXT"],
                          level=LEVEL["L1"],
                          height=11.0,
                          upper_limit_level=None) -> list:
    """4 exterior walls forming a rectangle."""
    walls = [
        (x0, y0, x1, y0, "S wall"),
        (x1, y0, x1, y1, "E wall"),
        (x1, y1, x0, y1, "N wall"),
        (x0, y1, x0, y0, "W wall"),
    ]
    return [create_wall(*w, wall_type, level, height, upper_limit_level) for w in walls]


def get_wall_orientation(wall_id: int) -> dict | None:
    result = call("revit.get_wall_orientation", {"wall_id": wall_id})
    if result.get("success"):
        return result.get("result", {}).get("orientation")
    return None


def flip_wall(wall_id: int) -> bool:
    return call("revit.flip_wall", {"wall_id": wall_id}).get("success", False)


def verify_wall_facing(wall_id: int, expected_nx: float, expected_ny: float, label: str = ""):
    """Check exterior face orientation and flip if wrong."""
    orient = get_wall_orientation(wall_id)
    if orient is None:
        print(f"  [FACING] cannot get orientation for wall {wall_id}")
        return
    ox, oy = orient.get("x", 0), orient.get("y", 0)
    correct = (
        (expected_nx == 0 or (expected_nx > 0 and ox > 0.5) or (expected_nx < 0 and ox < -0.5)) and
        (expected_ny == 0 or (expected_ny > 0 and oy > 0.5) or (expected_ny < 0 and oy < -0.5))
    )
    if not correct:
        print(f"  [FACING] {label} wall {wall_id} wrong ({ox:.1f},{oy:.1f}) → flipping")
        flip_wall(wall_id)
    else:
        print(f"  [FACING] {label} wall {wall_id} ok")


# ─────────────────────────────────────────────
# FLOORS
# ─────────────────────────────────────────────

def create_floor_polygon(boundary_points: list,
                          floor_type: str = "Floor 6\" Concrete",
                          level: str = LEVEL["L1"],
                          label: str = "") -> dict:
    payload = {
        "boundary_points": boundary_points,
        "floor_type": floor_type,
        "level": level,
        "label": label,
    }
    return call("revit.create_floor", payload)


# ─────────────────────────────────────────────
# DOORS & WINDOWS
# ─────────────────────────────────────────────

def place_door(wall_id: int, position_along: float,
               family: str, type_name: str,
               level: str = LEVEL["L1"],
               flip: bool = False,
               label: str = "") -> dict:
    payload = {
        "wall_id": wall_id,
        "position_along_wall": position_along,
        "family_name": family,
        "type_name": type_name,
        "level": level,
        "flip": flip,
        "label": label,
    }
    return call("revit.place_door", payload)


def place_window(wall_id: int, position_along: float,
                 family: str, type_name: str,
                 sill_height: float = 1.0,
                 level: str = LEVEL["L1"],
                 label: str = "") -> dict:
    payload = {
        "wall_id": wall_id,
        "position_along_wall": position_along,
        "family_name": family,
        "type_name": type_name,
        "sill_height": sill_height,
        "level": level,
        "label": label,
    }
    return call("revit.place_window", payload)


# ─────────────────────────────────────────────
# FAMILY INSTANCES (fixtures, cabinets, furniture)
# ─────────────────────────────────────────────

def place_family(family: str, type_name: str,
                 x: float, y: float, z: float = 0,
                 rotation: float = 0,
                 level: str = LEVEL["L1"],
                 label: str = "") -> dict:
    payload = {
        "family_name": family,
        "type_name": type_name,
        "location": {"x": x, "y": y, "z": z},
        "rotation": rotation,
        "level": level,
        "label": label,
    }
    result = call("revit.place_family_instance", payload)
    if not result.get("success") and not result.get("dry_run"):
        print(f"❌ Family failed [{label}]: {result.get('error')}")
    return result


def place_against_wall(family: str, type_name: str,
                        wall_coord: float, wall_face: str,
                        position_along: float, z: float,
                        level: str, fixture_depth: float = 2.0,
                        label: str = "") -> dict:
    """
    Place a fixture against a wall using compass face direction.
    wall_coord: x-coord for N/S walls, y-coord for E/W walls
    wall_face:  which wall face ('N','S','E','W') the fixture is against
    fixture_depth: how far from wall face to center of fixture
    """
    from core.constants import WALL_HALF, WALL_FACE_TO_FRONT, FACE_TO_ROT
    front = WALL_FACE_TO_FRONT[wall_face.upper()]
    rotation = FACE_TO_ROT[front]
    half_wall = WALL_HALF["EXT"]
    offset = half_wall + fixture_depth / 2

    if wall_face.upper() in ("N", "S"):
        # wall runs E-W, coord is y
        y = wall_coord + (offset if wall_face.upper() == "S" else -offset)
        x = position_along
    else:
        # wall runs N-S, coord is x
        x = wall_coord + (offset if wall_face.upper() == "W" else -offset)
        y = position_along

    return place_family(family, type_name, x, y, z, rotation, level, label)


# ─────────────────────────────────────────────
# ROOMS
# ─────────────────────────────────────────────

def get_all_rooms() -> list:
    """Return list of all rooms with name, area, and bounding box."""
    result = call("revit.list_elements_by_category", {"category": "Rooms"})
    if result.get("success"):
        return result.get("result", {}).get("rooms", [])
    return []


def place_room(x: float, y: float, name: str,
               level: str = LEVEL["L1"]) -> dict:
    payload = {"location": {"x": x, "y": y}, "name": name, "level": level}
    return call("revit.place_room", payload)


# ─────────────────────────────────────────────
# VIEWS & SHEETS
# ─────────────────────────────────────────────

def list_views() -> list:
    result = call("revit.list_views", {})
    if result.get("success"):
        return result.get("result", {}).get("views", [])
    return []


def list_sheets() -> list:
    result = call("revit.list_sheets", {})
    if result.get("success"):
        return result.get("result", {}).get("sheets", [])
    return []


def create_sheet(sheet_number: str, sheet_name: str,
                 title_block: str = "Barnhaus Title Block") -> dict:
    payload = {
        "sheet_number": sheet_number,
        "sheet_name": sheet_name,
        "title_block_family": title_block,
    }
    return call("revit.create_sheet", payload)


def place_view_on_sheet(sheet_id: int, view_id: int,
                         x: float = 1.0, y: float = 1.0) -> dict:
    payload = {"sheet_id": sheet_id, "view_id": view_id, "location": {"x": x, "y": y}}
    return call("revit.place_viewport_on_sheet", payload)


def create_elevation(name: str, x: float, y: float,
                      facing: str = "S",
                      level: str = LEVEL["L1"]) -> dict:
    """Create an elevation marker. facing = N/S/E/W."""
    rotation = FACE_TO_ROT.get(facing.upper(), 0)
    payload = {
        "name": name,
        "location": {"x": x, "y": y},
        "rotation": rotation,
        "level": level,
    }
    return call("revit.create_elevation", payload)


# ─────────────────────────────────────────────
# DIMENSIONS
# ─────────────────────────────────────────────

def add_dimension(references: list, line_start: dict,
                   line_end: dict, view_id: int) -> dict:
    """Add a dimension string across a list of element references."""
    payload = {
        "references": references,
        "line_start": line_start,
        "line_end": line_end,
        "view_id": view_id,
    }
    return call("revit.add_dimension", payload)


# ─────────────────────────────────────────────
# TAGS
# ─────────────────────────────────────────────

def tag_element(element_id: int, view_id: int,
                tag_family: str = None, leader: bool = False) -> dict:
    payload = {
        "element_id": element_id,
        "view_id": view_id,
        "leader": leader,
    }
    if tag_family:
        payload["tag_family"] = tag_family
    return call("revit.tag_element", payload)


# ─────────────────────────────────────────────
# MODEL QUERY HELPERS
# ─────────────────────────────────────────────

def get_all_walls() -> list:
    result = call("revit.list_elements_by_category", {"category": "Walls"})
    if result.get("success"):
        return result.get("result", {}).get("elements", [])
    return []


def get_all_doors() -> list:
    result = call("revit.list_elements_by_category", {"category": "Doors"})
    if result.get("success"):
        return result.get("result", {}).get("elements", [])
    return []


def get_all_windows() -> list:
    result = call("revit.list_elements_by_category", {"category": "Windows"})
    if result.get("success"):
        return result.get("result", {}).get("elements", [])
    return []


def get_element_geometry(element_id: int) -> dict:
    result = call("revit.get_element_geometry", {"element_id": element_id, "detail_level": "medium"})
    if result.get("success"):
        return result.get("result", {})
    return {}


def get_element_parameters(element_id: int) -> dict:
    result = call("revit.get_element_parameters", {"element_id": element_id})
    if result.get("success"):
        return result.get("result", {})
    return {}


def get_elements_in_room(room_id: int) -> list:
    result = call("revit.get_elements_in_room", {"room_id": room_id})
    if result.get("success"):
        return result.get("result", {}).get("elements", [])
    return []


# ─────────────────────────────────────────────
# GENERIC QUERIES (wrap existing DLL commands)
# ─────────────────────────────────────────────

def list_elements_by_category(category: str, view_id: int = None) -> list:
    """
    Generic category query. Optional view_id scopes results to elements
    visible in that view (supported by the bridge since Aug 2026 build).
    Returns list of {id, name, category, type, start_x/y, end_x/y,
    length_ft, level, area_sf, dim_value, dim_value_string}.
    """
    payload = {"category": category}
    if view_id is not None:
        payload["view_id"] = view_id
    result = call("revit.list_elements_by_category", payload)
    if result.get("success"):
        return result.get("result", {}).get("elements", [])
    return []


def get_type_parameters(element_id: int) -> dict:
    """All type parameters for an element. Returns {type_name, type_family, parameters: [...]}"""
    result = call("revit.get_type_parameters", {"element_id": element_id})
    if result.get("success"):
        return result.get("result", {})
    return {}


def get_type_param_map(element_id: int) -> dict:
    """Type parameters as a simple {name: value} dict."""
    info = get_type_parameters(element_id)
    return {p.get("name"): p.get("value") for p in info.get("parameters", [])}


def get_parameter_value(element_id: int, parameter_name: str):
    """Read a single instance parameter value (or None)."""
    result = call("revit.get_parameter_value",
                  {"element_id": element_id, "parameter_name": parameter_name})
    if result.get("success"):
        return (result.get("result") or {}).get("value")
    return None


def get_element_bounding_box(element_id: int) -> dict:
    result = call("revit.get_element_bounding_box", {"element_id": element_id})
    if result.get("success"):
        return result.get("result", {})
    return {}


def get_sheet_info(sheet_id: int) -> dict:
    """Sheet detail incl. viewports: [{viewport_id, view_id, view_name}]."""
    result = call("revit.get_sheet_info", {"sheet_id": sheet_id})
    if result.get("success"):
        return result.get("result", {})
    return {}


def get_warnings() -> list:
    result = call("revit.get_warnings", {})
    if result.get("success"):
        return result.get("result", {}).get("warnings", [])
    return []


def export_image(view_id: int, output_path: str,
                 image_format: str = "PNG", resolution: int = 1500) -> dict:
    """
    Export a view/sheet as an image ON THE BRIDGE HOST (Mitch's Windows disk).
    Returns {expected_file_path, file_exists, ...}. NOTE: the file lands on
    the Windows machine — fetching bytes back through the tunnel requires the
    Phase 2 bridge file-serving endpoint.
    """
    result = call("revit.export_image", {
        "view_id": view_id,
        "output_path": output_path,
        "format": image_format,
        "resolution": resolution,
    })
    if result.get("success"):
        return result.get("result", {})
    return {"error": result.get("error", "unknown")}


# ─────────────────────────────────────────────
# DIMENSIONS — READ (existing manually placed)
# ─────────────────────────────────────────────

def list_dimensions(view_id: int = None) -> list:
    """
    Read existing Dimension elements (does NOT modify anything).
    view_id scopes to a single view. Each entry carries:
      dim_value (raw ft), dim_value_string (e.g. 12' - 6\"),
      start/end coords + length_ft of the dimension line.
    Reference/target detail (which wall layer, core vs finish) requires the
    Phase 2 DLL command — not available yet.
    """
    return list_elements_by_category("Dimensions", view_id=view_id)


# ─────────────────────────────────────────────
# DIAGNOSTIC TOOLS
# ─────────────────────────────────────────────

def try_delete(element_id: int) -> dict:
    """
    Attempt to delete an element in a transaction that is ALWAYS rolled back.
    Captures every Revit error/warning via IFailuresPreprocessor before
    any popup appears. Returns {can_delete, errors, warnings, summary}.
    """
    result = call("revit.try_delete", {"element_id": element_id})
    if result.get("success"):
        return result.get("result", result)
    return {"can_delete": False, "errors": [result.get("error", "unknown")], "warnings": []}


def get_dependencies(element_id: int) -> dict:
    """
    Call GetDependentElements(null) and return full context per dependent.
    Shows what’s attached — hosted families, sketch lines, constraints, etc.
    Returns {dependent_count, dependents: [{id, category, class_name, name, location}]}
    """
    result = call("revit.get_dependencies", {"element_id": element_id})
    if result.get("success"):
        return result.get("result", result)
    return {"dependent_count": 0, "dependents": [], "error": result.get("error")}


def inspect_roof_sketch(element_id: int) -> dict:
    """
    Walk the element’s dependent ModelCurve sketch lines and check each for
    locked Dimension constraints (alignment locks to wall faces).
    Returns {sketch_curve_count, constrained_curve_count, diagnosis, sketch_curves}
    """
    result = call("revit.inspect_roof_sketch", {"element_id": element_id})
    if result.get("success"):
        return result.get("result", result)
    return {"sketch_curve_count": 0, "constrained_curve_count": 0, "error": result.get("error")}


def inspect_element(element_id: int) -> dict:
    """
    Deep-dive inspection of a single element: class, category, type, level,
    location, bounding box, host, joined walls, all instance + type params,
    and all dependent element IDs.
    """
    result = call("revit.inspect_element", {"element_id": element_id})
    if result.get("success"):
        return result.get("result", result)
    return {"error": result.get("error", "unknown")}
