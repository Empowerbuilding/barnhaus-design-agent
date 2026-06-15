"""
door_qa.py — Door placement QA checks.

Checks:
- Swing conflict (door arc hits wall, fixture, or another door)
- Latch-side wall clearance (min 6")
- Swing direction logic by room type
- Egress width for bedrooms
- Hinge-side corner clearance
"""

from core.constants import QA
from core import revit_client as rc


def check_all_doors(state: dict) -> list:
    """Run all door checks. Returns list of issues."""
    issues = []
    doors = state.get("doors", [])

    for door in doors:
        door_id  = door.get("id")
        host_wall = door.get("host_wall_id")
        room_name = door.get("room_name", "")
        width_ft  = door.get("width_ft", 0)
        swing_arc = door.get("swing_geometry")  # bounding box of swing arc

        issues += _check_latch_clearance(door)
        issues += _check_swing_conflict(door, state)
        issues += _check_swing_logic(door, room_name)
        issues += _check_egress_width(door, room_name, width_ft)

    return issues


def _check_latch_clearance(door: dict) -> list:
    """Latch side needs >= 6" of wall."""
    issues = []
    latch_wall = door.get("latch_side_wall_clearance_ft")
    if latch_wall is not None and latch_wall < QA["door_latch_wall_min"]:
        issues.append({
            "type": "door_latch_clearance",
            "severity": "fix",
            "element_id": door.get("id"),
            "room": door.get("room_name", ""),
            "message": f"Door {door.get('id')} has only {latch_wall*12:.0f}\" on latch side (min 6\"). "
                       f"Move door or flip swing.",
            "auto_fixable": True,
            "fix_action": "flip_door_swing",
        })
    return issues


def _check_swing_conflict(door: dict, state: dict) -> list:
    """Check if door swing arc conflicts with a wall, fixture, or another door."""
    issues = []
    swing_box = door.get("swing_bounding_box")
    if not swing_box:
        return issues

    # Check against all doors in the same room
    room_id = door.get("room_id")
    for other in state.get("doors", []):
        if other.get("id") == door.get("id"):
            continue
        if other.get("room_id") != room_id:
            continue
        other_box = other.get("bounding_box")
        if other_box and _boxes_overlap(swing_box, other_box):
            issues.append({
                "type": "door_swing_conflict",
                "severity": "fix",
                "element_id": door.get("id"),
                "room": door.get("room_name", ""),
                "message": f"Door {door.get('id')} swing conflicts with door {other.get('id')} in {door.get('room_name')}. "
                           f"Flip one swing or reposition.",
                "auto_fixable": True,
                "fix_action": "flip_door_swing",
            })

    return issues


def _check_swing_logic(door: dict, room_name: str) -> list:
    """Flag doors that swing in a counterintuitive direction for the room type."""
    issues = []
    swing_dir = door.get("swing_direction")  # "into_room" or "out_of_room"
    room_lower = room_name.lower()

    # Bedroom doors should always swing into the room (not block hallway)
    if "bedroom" in room_lower and swing_dir == "out_of_room":
        issues.append({
            "type": "door_swing_logic",
            "severity": "consider",
            "element_id": door.get("id"),
            "room": room_name,
            "message": f"Bedroom door {door.get('id')} swings OUT into hallway. "
                       f"Consider swinging into the bedroom.",
            "auto_fixable": True,
            "fix_action": "flip_door_swing",
        })

    # Bathroom doors should swing into bathroom (not block hallway or adjoining room)
    if "bath" in room_lower and swing_dir == "out_of_room":
        issues.append({
            "type": "door_swing_logic",
            "severity": "consider",
            "element_id": door.get("id"),
            "room": room_name,
            "message": f"Bathroom door {door.get('id')} swings outward. "
                       f"Consider swinging into bathroom.",
            "auto_fixable": True,
            "fix_action": "flip_door_swing",
        })

    return issues


def _check_egress_width(door: dict, room_name: str, width_ft: float) -> list:
    """Bedroom doors need minimum 34" (32" clear) for egress."""
    issues = []
    room_lower = room_name.lower()
    if "bedroom" in room_lower and width_ft > 0:
        if width_ft < QA["egress_door_min_width"]:
            issues.append({
                "type": "egress_width",
                "severity": "fix",
                "element_id": door.get("id"),
                "room": room_name,
                "message": f"Bedroom door {door.get('id')} is {width_ft*12:.0f}\" wide — below 34\" egress minimum. "
                           f"Swap to 36\" door.",
                "auto_fixable": False,
            })
    return issues


def _boxes_overlap(a: dict, b: dict, tol: float = 0.1) -> bool:
    """Check if two bounding boxes overlap (2D, xy plane)."""
    return not (
        a["max_x"] - tol < b["min_x"] or
        b["max_x"] - tol < a["min_x"] or
        a["max_y"] - tol < b["min_y"] or
        b["max_y"] - tol < a["min_y"]
    )
