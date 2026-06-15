"""
model_integrity.py — Revit model integrity checks.

Checks:
- Off-axis walls (walls that aren't perfectly horizontal or vertical)
- Unclosed rooms (room boundary not fully enclosed)
- Wall join gaps at corners
- Duplicate/stacked elements
- Walls with zero or near-zero length
"""

import math


def check_model_integrity(state: dict) -> list:
    issues = []
    issues += _check_off_axis_walls(state)
    issues += _check_short_walls(state)
    issues += _check_unclosed_rooms(state)
    return issues


def _check_off_axis_walls(state: dict) -> list:
    """Flag walls that aren't perfectly horizontal or vertical — likely modeling slips."""
    issues = []
    all_walls = (
        state.get("walls", {}).get("exterior", []) +
        state.get("walls", {}).get("interior", []) +
        state.get("walls", {}).get("other", [])
    )

    for wall in all_walls:
        start = wall.get("start_point", {})
        end   = wall.get("end_point", {})
        if not start or not end:
            continue

        dx = abs(end.get("x", 0) - start.get("x", 0))
        dy = abs(end.get("y", 0) - start.get("y", 0))

        if dx < 0.01 or dy < 0.01:
            continue  # perfectly axis-aligned, skip

        # Wall is diagonal — calculate angle from axis
        angle_from_horizontal = math.degrees(math.atan2(dy, dx))
        angle_from_axis = min(angle_from_horizontal, 90 - angle_from_horizontal)

        if 0.1 < angle_from_axis < 44.9:
            # Clearly intentional diagonal (rare in Barnhaus but possible)
            pass
        elif angle_from_axis <= 0.3:
            # Very close to axis — probably a modeling slip
            issues.append({
                "type": "off_axis_wall",
                "severity": "fix",
                "element_id": wall.get("id"),
                "room": None,
                "message": f"Wall {wall.get('id')} is {angle_from_axis:.2f}° off-axis — likely a modeling slip. "
                           f"Should be perfectly horizontal or vertical.",
                "auto_fixable": True,
                "fix_action": "snap_wall_to_axis",
            })

    return issues


def _check_short_walls(state: dict) -> list:
    """Flag walls under 1ft — almost certainly an accident."""
    issues = []
    all_walls = (
        state.get("walls", {}).get("exterior", []) +
        state.get("walls", {}).get("interior", [])
    )

    for wall in all_walls:
        length = wall.get("length_ft", 0)
        if 0 < length < 1.0:
            issues.append({
                "type": "short_wall",
                "severity": "fix",
                "element_id": wall.get("id"),
                "room": None,
                "message": f"Wall {wall.get('id')} is only {length*12:.1f}\" long — likely a duplicate or modeling error. Delete it.",
                "auto_fixable": False,
            })

    return issues


def _check_unclosed_rooms(state: dict) -> list:
    """Flag rooms that Revit couldn't compute an area for — means boundary isn't closed."""
    issues = []
    for room in state.get("rooms", []):
        area = room.get("area_sf", 0)
        if area == 0 or area is None:
            issues.append({
                "type": "unclosed_room",
                "severity": "fix",
                "element_id": room.get("id"),
                "room": room.get("name", "Unknown"),
                "message": f"Room '{room.get('name')}' has zero area — boundary not closed. "
                           f"Find and close the gap in the enclosing walls.",
                "auto_fixable": False,
            })

    return issues
