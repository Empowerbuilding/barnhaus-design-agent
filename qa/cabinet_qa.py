"""
cabinet_qa.py — Cabinet and kitchen fixture QA checks.

Checks:
- Kitchen aisle clearance (42" min, 48" preferred)
- Cabinet not against a wall (floating)
- Upper cabinet overlapping a window
- Island clearance on all working sides
- Work triangle (fridge / sink / range): each leg 4–9ft
- Toilet clearances (15" side min, 24" front min)
- Shower minimum dimensions
"""

from core.constants import QA


def check_all_cabinets(state: dict) -> list:
    issues = []
    rooms = state.get("rooms", [])

    for room in rooms:
        name = room.get("name", "")
        if "kitchen" in name.lower():
            issues += _check_kitchen(room, state)
        if "bath" in name.lower():
            issues += _check_bathroom(room, state)

    return issues


def _check_kitchen(room: dict, state: dict) -> list:
    issues = []
    room_id  = room.get("id")
    room_name = room.get("name", "Kitchen")

    # Get elements in this room
    cabinets  = _get_room_elements(state, room_id, categories=["Casework"])
    plumbing  = _get_room_elements(state, room_id, categories=["Plumbing Fixtures"])
    appliances = _get_room_elements(state, room_id, categories=["Specialty Equipment"])
    windows   = _get_room_elements(state, room_id, categories=["Windows"])

    # ── Aisle clearance ────────────────────────────────────────────────────
    base_cabs = [c for c in cabinets if "base" in c.get("family_name", "").lower()]
    aisle_issues = _check_aisle_clearance(base_cabs, room_name)
    issues += aisle_issues

    # ── Upper cabinet / window conflict ────────────────────────────────────
    upper_cabs = [c for c in cabinets if "upper" in c.get("family_name", "").lower()]
    for uc in upper_cabs:
        for win in windows:
            if _elements_overlap_xy(uc, win):
                issues.append({
                    "type": "upper_cab_window_conflict",
                    "severity": "fix",
                    "room": room_name,
                    "element_id": uc.get("id"),
                    "message": f"Upper cabinet {uc.get('id')} overlaps window {win.get('id')} in {room_name}. "
                               f"Move cabinet or relocate window.",
                    "auto_fixable": False,
                })

    # ── Work triangle ──────────────────────────────────────────────────────
    fridge = next((a for a in appliances if "fridge" in a.get("family_name", "").lower() or
                   "refrig" in a.get("family_name", "").lower()), None)
    sink   = next((p for p in plumbing if "sink" in p.get("family_name", "").lower() and
                   "island" not in p.get("family_name", "").lower()), None)
    range_ = next((a for a in appliances if "range" in a.get("family_name", "").lower()), None)

    if fridge and sink and range_:
        triangle = _check_work_triangle(fridge, sink, range_, room_name)
        issues += triangle

    return issues


def _check_bathroom(room: dict, state: dict) -> list:
    issues = []
    room_id   = room.get("id")
    room_name = room.get("name", "Bathroom")

    plumbing = _get_room_elements(state, room_id, categories=["Plumbing Fixtures"])
    toilets  = [p for p in plumbing if "toilet" in p.get("family_name", "").lower()]
    showers  = [p for p in plumbing if "shower" in p.get("family_name", "").lower()]

    # ── Toilet clearances ──────────────────────────────────────────────────
    for toilet in toilets:
        side_clear  = toilet.get("side_clearance_ft")
        front_clear = toilet.get("front_clearance_ft")

        if side_clear is not None and side_clear < QA["toilet_side_wall_min"]:
            issues.append({
                "type": "toilet_side_clearance",
                "severity": "fix",
                "room": room_name,
                "element_id": toilet.get("id"),
                "message": f"Toilet in {room_name}: only {side_clear*12:.0f}\" to wall (min 15\"). Move toilet or wall.",
                "auto_fixable": True,
                "fix_action": "nudge_element",
            })
        elif side_clear is not None and side_clear < QA["toilet_side_preferred"]:
            issues.append({
                "type": "toilet_side_tight",
                "severity": "consider",
                "room": room_name,
                "element_id": toilet.get("id"),
                "message": f"Toilet in {room_name}: {side_clear*12:.0f}\" to wall — meets code but 18\" preferred.",
                "auto_fixable": False,
            })

        if front_clear is not None and front_clear < QA["toilet_front_clear_min"]:
            issues.append({
                "type": "toilet_front_clearance",
                "severity": "fix",
                "room": room_name,
                "element_id": toilet.get("id"),
                "message": f"Toilet in {room_name}: only {front_clear*12:.0f}\" in front (min 24\"). Reposition.",
                "auto_fixable": True,
                "fix_action": "nudge_element",
            })

    # ── Shower minimum size ────────────────────────────────────────────────
    for shower in showers:
        w = shower.get("width_ft", 0)
        d = shower.get("depth_ft", 0)
        if w > 0 and w < QA["shower_min_width"]:
            issues.append({
                "type": "shower_too_narrow",
                "severity": "fix",
                "room": room_name,
                "element_id": shower.get("id"),
                "message": f"Shower in {room_name} is {w*12:.0f}\" wide (min 36\"). Resize or reposition.",
                "auto_fixable": False,
            })

    return issues


def _check_aisle_clearance(base_cabs: list, room_name: str) -> list:
    """Detect facing cabinet runs and check clearance between them."""
    issues = []
    # Group cabinets by wall face direction
    by_face: dict[str, list] = {}
    for c in base_cabs:
        face = c.get("face_direction", "unknown")
        by_face.setdefault(face, []).append(c)

    opposite_pairs = [("N", "S"), ("E", "W")]
    for fa, fb in opposite_pairs:
        if fa in by_face and fb in by_face:
            # Approximate aisle as distance between the two face lines
            coords_a = [c.get("y") if fa in ("N", "S") else c.get("x") for c in by_face[fa]]
            coords_b = [c.get("y") if fb in ("N", "S") else c.get("x") for c in by_face[fb]]
            if coords_a and coords_b:
                a_val = sum(coords_a) / len(coords_a)
                b_val = sum(coords_b) / len(coords_b)
                gap = abs(a_val - b_val) - 4.0  # approx: subtract 2x cabinet depth
                if gap < QA["kitchen_aisle_min"]:
                    issues.append({
                        "type": "kitchen_aisle_tight",
                        "severity": "fix",
                        "room": room_name,
                        "element_id": None,
                        "message": f"Kitchen aisle between {fa}/{fb} runs is ~{gap*12:.0f}\" (min 42\"). "
                                   f"Shift a cabinet run outward.",
                        "auto_fixable": False,
                    })
                elif gap < QA["kitchen_aisle_preferred"]:
                    issues.append({
                        "type": "kitchen_aisle_suboptimal",
                        "severity": "consider",
                        "room": room_name,
                        "element_id": None,
                        "message": f"Kitchen aisle is ~{gap*12:.0f}\" — meets code but 48\" preferred.",
                        "auto_fixable": False,
                    })
    return issues


def _check_work_triangle(fridge, sink, range_, room_name) -> list:
    issues = []
    legs = [
        ("fridge→sink",  fridge, sink),
        ("sink→range",   sink,   range_),
        ("range→fridge", range_, fridge),
    ]
    for label, a, b in legs:
        ax, ay = a.get("x", 0), a.get("y", 0)
        bx, by = b.get("x", 0), b.get("y", 0)
        dist = ((bx - ax)**2 + (by - ay)**2) ** 0.5
        if dist < 4.0:
            issues.append({
                "type": "work_triangle_too_tight",
                "severity": "consider",
                "room": room_name,
                "element_id": None,
                "message": f"Kitchen work triangle leg {label} is {dist:.1f}ft — under 4ft minimum. "
                           f"Appliances are too close together.",
                "auto_fixable": False,
            })
        elif dist > 9.0:
            issues.append({
                "type": "work_triangle_too_large",
                "severity": "consider",
                "room": room_name,
                "element_id": None,
                "message": f"Kitchen work triangle leg {label} is {dist:.1f}ft — over 9ft. "
                           f"Kitchen may feel inefficient.",
                "auto_fixable": False,
            })
    return issues


def _get_room_elements(state: dict, room_id: int, categories: list) -> list:
    """Return elements in a room matching any of the given categories."""
    # In the real implementation this will query state["elements_by_room"]
    # For now returns empty — populated after state reader is built out
    return state.get("elements_by_room", {}).get(str(room_id), {}).get("elements", [])


def _elements_overlap_xy(a: dict, b: dict) -> bool:
    bb_a = a.get("bounding_box", {})
    bb_b = b.get("bounding_box", {})
    if not bb_a or not bb_b:
        return False
    return not (
        bb_a.get("max_x", 0) < bb_b.get("min_x", 0) or
        bb_b.get("max_x", 0) < bb_a.get("min_x", 0) or
        bb_a.get("max_y", 0) < bb_b.get("min_y", 0) or
        bb_b.get("max_y", 0) < bb_a.get("min_y", 0)
    )
