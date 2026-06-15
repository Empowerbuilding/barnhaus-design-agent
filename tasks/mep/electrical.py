"""
electrical.py — Auto-generates electrical plans (A108).

Rules (IRC + Barnhaus standard):
- GFI outlets within 6ft of any sink (kitchen, bath, laundry)
- Dedicated 20A circuit outlet at each major appliance (range, DW, fridge, microwave)
- Floor outlets at 12ft intervals in open areas > 400 SF (great room, bonus)
- Exterior GFI at each exterior door
- Smoke detectors: each bedroom, each level, kitchen
- Ceiling fan rough-in: master bedroom, great room, all secondary bedrooms
- Recessed can layout: 4ft grid in kitchen, 6ft grid elsewhere
"""

from core import revit_client as rc
from core.constants import LIGHTING, LEVEL
from core.project_state import load_state


WET_ROOMS = {"kitchen", "master bath", "master bathroom", "bathroom", "bath", "laundry", "laundry room"}
OPEN_ROOMS = {"great room", "bonus room", "living", "game room"}
BED_ROOMS  = {"master bedroom", "bedroom", "bonus room"}


def run_l1(state: dict = None, sheet_id: int = None):
    if state is None:
        state = load_state()
    print("\n⚡ Electrical Plan — Level 1...")
    _run_level(state, LEVEL["L1"], sheet_id)


def run_l2(state: dict = None, sheet_id: int = None):
    if state is None:
        state = load_state()
    print("\n⚡ Electrical Plan — Level 2...")
    _run_level(state, LEVEL["L2"], sheet_id)


def _run_level(state: dict, level: str, sheet_id: int):
    rooms = [r for r in state.get("rooms", []) if r.get("level") == level]
    if not rooms:
        print(f"  No rooms found on {level}")
        return

    placed = 0
    for room in rooms:
        name_lower = room.get("name", "").lower()

        # GFI outlets near sinks in wet rooms
        if any(wet in name_lower for wet in WET_ROOMS):
            placed += _place_gfi_outlets(room, state, level)

        # Appliance circuits in kitchen
        if "kitchen" in name_lower:
            placed += _place_appliance_circuits(room, state, level)

        # Floor outlets in large open rooms
        if any(open_r in name_lower for open_r in OPEN_ROOMS):
            if room.get("area_sf", 0) > 400:
                placed += _place_floor_outlets(room, level)

        # Ceiling fan rough-in in bedrooms and great room
        if any(bed in name_lower for bed in BED_ROOMS) or "great room" in name_lower:
            placed += _place_ceiling_fan(room, level)

        # Smoke detector in each bedroom and kitchen
        if any(bed in name_lower for bed in BED_ROOMS) or "kitchen" in name_lower:
            placed += _place_smoke_detector(room, level)

        # Recessed cans
        placed += _place_recessed_cans(room, level)

    # Smoke detector on each level (hallway/landing)
    _place_level_smoke_detector(state, level)

    print(f"  ✅ Placed {placed} electrical elements on {level}")


def _place_gfi_outlets(room: dict, state: dict, level: str) -> int:
    """Place GFI outlets near sinks in this room."""
    placed = 0
    room_id = room.get("id")
    plumbing = state.get("elements_by_room", {}).get(str(room_id), {}).get("elements", [])
    sinks = [p for p in plumbing if "sink" in p.get("family_name", "").lower()]

    for sink in sinks:
        sx, sy = sink.get("x", 0), sink.get("y", 0)
        # Place GFI 2ft to the side of sink center
        result = rc.call("revit.place_electrical_outlet", {
            "location": {"x": sx + 2.0, "y": sy, "z": 1.25},  # 15" AFF
            "outlet_type": "GFI",
            "level": level,
            "label": f"GFI near {room.get('name')} sink",
        })
        if result.get("success"):
            placed += 1

    return placed


def _place_appliance_circuits(room: dict, state: dict, level: str) -> int:
    """Place dedicated circuit outlets at each major kitchen appliance."""
    placed = 0
    room_id = room.get("id")
    appliances = state.get("elements_by_room", {}).get(str(room_id), {}).get("elements", [])

    appliance_keywords = ["range", "dishwasher", "fridge", "refrigerator", "microwave", "hood"]
    for appl in appliances:
        fname = appl.get("family_name", "").lower()
        if any(kw in fname for kw in appliance_keywords):
            result = rc.call("revit.place_electrical_outlet", {
                "location": {"x": appl.get("x", 0), "y": appl.get("y", 0), "z": 1.5},
                "outlet_type": "Dedicated 20A",
                "level": level,
                "label": f"Dedicated circuit — {appl.get('family_name')}",
            })
            if result.get("success"):
                placed += 1

    return placed


def _place_floor_outlets(room: dict, level: str) -> int:
    """Place floor outlets at 12ft intervals in large open rooms."""
    placed = 0
    bbox = room.get("bounding_box", {})
    if not bbox:
        return 0

    x0 = bbox.get("min_x", 0) + 6
    x1 = bbox.get("max_x", 0) - 6
    y  = (bbox.get("min_y", 0) + bbox.get("max_y", 0)) / 2

    x = x0
    while x <= x1:
        result = rc.call("revit.place_electrical_outlet", {
            "location": {"x": x, "y": y, "z": 0},
            "outlet_type": "Floor Outlet",
            "level": level,
            "label": f"Floor outlet — {room.get('name')}",
        })
        if result.get("success"):
            placed += 1
        x += 12.0

    return placed


def _place_ceiling_fan(room: dict, level: str) -> int:
    cx = (room.get("bounding_box", {}).get("min_x", 0) +
          room.get("bounding_box", {}).get("max_x", 0)) / 2
    cy = (room.get("bounding_box", {}).get("min_y", 0) +
          room.get("bounding_box", {}).get("max_y", 0)) / 2

    result = rc.place_family(
        LIGHTING["ceiling_fan"][0], LIGHTING["ceiling_fan"][1],
        cx, cy, z=0, level=level, label=f"Ceiling fan — {room.get('name')}"
    )
    return 1 if result.get("success") else 0


def _place_smoke_detector(room: dict, level: str) -> int:
    cx = (room.get("bounding_box", {}).get("min_x", 0) +
          room.get("bounding_box", {}).get("max_x", 0)) / 2
    cy = (room.get("bounding_box", {}).get("min_y", 0) +
          room.get("bounding_box", {}).get("max_y", 0)) / 2

    result = rc.call("revit.place_annotation", {
        "annotation_type": "Smoke Detector",
        "location": {"x": cx, "y": cy, "z": 0},
        "level": level,
        "label": f"Smoke detector — {room.get('name')}",
    })
    return 1 if result.get("success") else 0


def _place_recessed_cans(room: dict, level: str) -> int:
    """Place recessed can lights on a grid across the room."""
    bbox = room.get("bounding_box", {})
    if not bbox:
        return 0

    name_lower = room.get("name", "").lower()
    grid = 4.0 if "kitchen" in name_lower else 6.0

    x0 = bbox.get("min_x", 0) + grid / 2
    y0 = bbox.get("min_y", 0) + grid / 2
    x1 = bbox.get("max_x", 0)
    y1 = bbox.get("max_y", 0)

    placed = 0
    x = x0
    while x < x1:
        y = y0
        while y < y1:
            result = rc.place_family(
                LIGHTING["recessed_6in"][0], LIGHTING["recessed_6in"][1],
                x, y, z=0, level=level,
                label=f"Recessed can — {room.get('name')}"
            )
            if result.get("success"):
                placed += 1
            y += grid
        x += grid

    return placed


def _place_level_smoke_detector(state: dict, level: str):
    """Place a hallway/landing smoke detector for this level."""
    landing = next((r for r in state.get("rooms", [])
                    if r.get("level") == level and
                    any(kw in r.get("name", "").lower()
                        for kw in ["hallway", "hall", "landing", "foyer", "corridor"])), None)
    if landing:
        cx = (landing.get("bounding_box", {}).get("min_x", 0) +
              landing.get("bounding_box", {}).get("max_x", 0)) / 2
        cy = (landing.get("bounding_box", {}).get("min_y", 0) +
              landing.get("bounding_box", {}).get("max_y", 0)) / 2
        rc.call("revit.place_annotation", {
            "annotation_type": "Smoke Detector",
            "location": {"x": cx, "y": cy, "z": 0},
            "level": level,
            "label": f"Smoke detector — {landing.get('name')} (level detector)",
        })
