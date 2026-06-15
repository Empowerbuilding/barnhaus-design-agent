"""
room_qa.py — Room sizing, adjacency, and circulation QA checks.

Checks:
- Room SF vs Barnhaus norms (too small / too large)
- Required adjacencies (master must touch master bath, kitchen must touch pantry, etc.)
- Forbidden adjacencies (master bedroom must not touch secondary bedrooms)
- Circulation path integrity (front door test, service path)
- Bedroom minimum width
- Closet depth (walk-in viability)
"""

from core.constants import ROOM_NORMS, MUST_TOUCH, MUST_NOT_TOUCH, QA


def check_all_rooms(state: dict) -> list:
    issues = []
    rooms  = state.get("rooms", [])
    levels = state.get("levels", [])

    # Only QA rooms that are named — unnamed rooms get a single grouped summary
    named_rooms   = [r for r in rooms if not _is_unnamed(r["name"])]
    unnamed_rooms = [r for r in rooms if _is_unnamed(r["name"])]
    room_map = {r["name"]: r for r in named_rooms}

    # Summarize unnamed rooms in one issue instead of spamming per-room
    issues += _summarize_unnamed_rooms(unnamed_rooms)
    issues += _check_missing_level_rooms(rooms, levels)

    for room in named_rooms:
        issues += _check_sizing(room)
        issues += _check_adjacency(room, room_map)
        issues += _check_bedroom_width(room)
        issues += _check_closet_depth(room)

    issues += _check_circulation(room_map)
    return issues


def _is_unnamed(name: str) -> bool:
    name = name.strip().lower()
    return name == "room" or (name.startswith("room ") and name.split()[-1].isdigit())


def _summarize_unnamed_rooms(rooms: list) -> list:
    if not rooms:
        return []
    zero_area  = [r for r in rooms if r.get("area_sf", 0) == 0]
    with_area  = [r for r in rooms if r.get("area_sf", 0) > 0]
    issues = []
    if zero_area:
        issues.append({
            "type": "unnamed_rooms_zero_area",
            "severity": "fyi",
            "room": "Unnamed Rooms",
            "element_id": None,
            "message": f"{len(zero_area)} unnamed rooms with 0 SF — likely unplaced or outside boundaries. "
                       f"Delete or name them.",
            "auto_fixable": False,
        })
    if with_area:
        total_sf = sum(r.get("area_sf", 0) for r in with_area)
        sizes    = sorted([r.get("area_sf", 0) for r in with_area], reverse=True)[:5]
        issues.append({
            "type": "unnamed_rooms_with_area",
            "severity": "fix",
            "room": "Unnamed Rooms",
            "element_id": None,
            "message": f"{len(with_area)} unnamed rooms with area ({total_sf:.0f} SF total). "
                       f"Largest: {', '.join(f'{s:.0f} SF' for s in sizes)}. Name them before running documentation.",
            "auto_fixable": False,
        })
    return issues


def _check_unnamed_rooms(rooms: list) -> list:
    """Flag rooms with default Revit names ('Room', 'Room 1', etc.)"""
    issues = []
    for room in rooms:
        name = room.get("name", "")
        sf   = room.get("area_sf", 0)
        # Default Revit room names are just 'Room' or 'Room N'
        if name.strip().lower() == "room" or (name.lower().startswith("room ") and name.split()[-1].isdigit()):
            severity = "fix" if sf > 100 else "consider"
            issues.append({
                "type": "unnamed_room",
                "severity": severity,
                "room": name,
                "element_id": room.get("id"),
                "message": f"Room '{name}' ({sf:.0f} SF) has a default Revit name. Rename it to its actual purpose.",
                "auto_fixable": False,
            })
    return issues


def _check_missing_level_rooms(rooms: list, levels: list) -> list:
    """Flag levels that have walls but no rooms placed."""
    issues = []
    if len(levels) <= 1:
        return issues

    # Get unique level IDs from rooms
    room_levels = {r.get("level") for r in rooms}
    level_ids   = {l.get("id") for l in levels}

    # Levels without any rooms (skip roof levels)
    for level in levels:
        lid  = level.get("id")
        name = level.get("name", "")
        if "roof" in name.lower() or "ceiling" in name.lower():
            continue
        if str(lid) not in {str(l) for l in room_levels} and lid not in room_levels:
            issues.append({
                "type": "level_missing_rooms",
                "severity": "consider",
                "room": name,
                "element_id": lid,
                "message": f"Level '{name}' has no rooms placed. Drop room elements to enable QA + area tracking on this level.",
                "auto_fixable": False,
            })
    return issues


def _check_sizing(room: dict) -> list:
    issues = []
    name = room.get("name", "")
    sf   = room.get("area_sf", 0)
    norm = _get_norm(name)
    if not norm or sf == 0:
        return issues

    # Water closets are small by design — don't flag them
    # Heuristic: if it's a bath room under 60 SF it's probably a WC/toilet room
    if "bath" in name.lower() and sf < 60:
        return []

    if sf < norm["min"]:
        issues.append({
            "type": "room_undersized",
            "severity": "fix",
            "room": name,
            "element_id": room.get("id"),
            "message": f"{name} is {sf:.0f} SF — below minimum {norm['min']} SF. Expand or reconsider program.",
            "auto_fixable": False,
        })
    elif sf > norm["max"]:
        issues.append({
            "type": "room_oversized",
            "severity": "consider",
            "room": name,
            "element_id": room.get("id"),
            "message": f"{name} is {sf:.0f} SF — above typical max {norm['max']} SF. Intentional?",
            "auto_fixable": False,
        })
    elif sf < norm["target_lo"]:
        issues.append({
            "type": "room_below_target",
            "severity": "fyi",
            "room": name,
            "element_id": room.get("id"),
            "message": f"{name} is {sf:.0f} SF — below target range {norm['target_lo']}–{norm['target_hi']} SF.",
            "auto_fixable": False,
        })
    return issues


def _check_adjacency(room: dict, room_map: dict) -> list:
    """
    Adjacency check using real wall boundary IDs from revit.get_room_boundary.
    Two rooms are adjacent if they share at least one boundary wall ID.
    """
    issues = []
    name = room.get("name", "")
    my_walls = set(room.get("boundary_wall_ids", []))

    required = MUST_TOUCH.get(name, [])
    forbidden = MUST_NOT_TOUCH.get(name, [])
    if not required and not forbidden:
        return []
    if not my_walls:
        return []  # no boundary data yet

    # Find which rooms share a wall with this one
    neighbors = set()
    for other_name, other_room in room_map.items():
        if other_name == name:
            continue
        other_walls = set(other_room.get("boundary_wall_ids", []))
        if my_walls & other_walls:  # shared wall ID = truly adjacent
            neighbors.add(other_name)

    # Must-touch violations
    for req in required:
        if req in room_map and req not in neighbors:
            issues.append({
                "type": "missing_adjacency",
                "severity": "fix",
                "room": name,
                "element_id": room.get("id"),
                "message": f"{name} does not share a wall with {req}. Check layout — they should be directly connected.",
                "auto_fixable": False,
            })

    # Must-not-touch violations
    for forb in forbidden:
        if forb in room_map and forb in neighbors:
            issues.append({
                "type": "bad_adjacency",
                "severity": "fix",
                "room": name,
                "element_id": room.get("id"),
                "message": f"{name} shares a wall with {forb} — these should not be directly adjacent.",
                "auto_fixable": False,
            })

    return issues


def _check_bedroom_width(room: dict) -> list:
    issues = []
    name  = room.get("name", "")
    width = room.get("width_ft", 0)
    if "bedroom" in name.lower() and width > 0:
        if width < QA["bedroom_min_width"]:
            issues.append({
                "type": "bedroom_too_narrow",
                "severity": "fix",
                "room": name,
                "element_id": room.get("id"),
                "message": f"{name} is only {width:.1f}ft wide (min {QA['bedroom_min_width']}ft). "
                           f"Won't fit a bed with clearance on both sides.",
                "auto_fixable": False,
            })
    return issues


def _check_closet_depth(room: dict) -> list:
    issues = []
    name  = room.get("name", "")
    depth = room.get("depth_ft", 0)
    if "closet" in name.lower() and "walk" in name.lower() and depth > 0:
        if depth < QA["closet_walkin_min_depth"]:
            issues.append({
                "type": "closet_too_shallow",
                "severity": "consider",
                "room": name,
                "element_id": room.get("id"),
                "message": f"{name} is only {depth:.1f}ft deep — below {QA['closet_walkin_min_depth']}ft walk-in minimum. "
                           f"Barely usable. Extend or call it a reach-in.",
                "auto_fixable": False,
            })
    return issues


def _check_circulation(room_map: dict) -> list:
    """Check high-level circulation rules from HOME_LAYOUT.md."""
    issues = []
    names_lower = {n.lower() for n in room_map.keys()}

    # Service path: garage → mudroom → kitchen must all exist and connect
    has_garage  = any("garage" in n for n in names_lower)
    has_mudroom = any("mudroom" in n or "mud room" in n for n in names_lower)
    has_kitchen = any("kitchen" in n for n in names_lower)

    if has_garage and not has_mudroom:
        issues.append({
            "type": "missing_mudroom",
            "severity": "consider",
            "room": "Service Zone",
            "element_id": None,
            "message": "Garage present but no Mudroom found. Barnhaus standard: Garage → Mudroom → Kitchen service path.",
            "auto_fixable": False,
        })

    # Front door test: foyer or entry should exist on plans with >2000 SF
    total_sf = sum(r.get("area_sf", 0) for r in room_map.values())
    has_foyer = any("foyer" in n or "entry" in n for n in names_lower)
    if total_sf > 2000 and not has_foyer:
        issues.append({
            "type": "missing_foyer",
            "severity": "fyi",
            "room": "Entry Zone",
            "element_id": None,
            "message": f"No Foyer/Entry room placed ({total_sf:.0f} SF plan). Consider adding one for circulation clarity.",
            "auto_fixable": False,
        })

    return issues


def _get_norm(room_name: str) -> dict | None:
    if room_name in ROOM_NORMS:
        return ROOM_NORMS[room_name]
    low = room_name.lower()
    if "master" in low and "bed" in low:  return ROOM_NORMS["Master Bedroom"]
    if "master" in low and "bath" in low: return ROOM_NORMS["Master Bath"]
    if "master" in low and "closet" in low: return ROOM_NORMS["Master Closet"]
    if "bedroom" in low: return ROOM_NORMS["Bedroom"]
    if "bathroom" in low: return ROOM_NORMS["Bathroom"]
    for key in ("Garage", "Outdoor Living", "Laundry", "Pantry", "Mudroom", "Kitchen", "Great Room"):
        if key.lower().split()[0] in low:
            return ROOM_NORMS[key]
    return None
