"""
plumbing.py — Auto-generates plumbing plans (A109).

Barnhaus standard plumbing notes:
- Hose bibs at each exterior access point (typically 2 per level)
- Water heater location callout (utility/mechanical room or garage)
- Water softener callout (near water heater)
- All fixture locations pulled from placed plumbing families
- Note: "ALL PLUMBING CONNECTIONS TBD BY LICENSED PLUMBER"
"""

from core import revit_client as rc
from core.constants import LEVEL
from core.project_state import load_state


def run_l1(state: dict = None, sheet_id: int = None):
    if state is None:
        state = load_state()
    print("\n🚿 Plumbing Plan — Level 1...")
    _run_level(state, LEVEL["L1"], sheet_id)


def run_l2(state: dict = None, sheet_id: int = None):
    if state is None:
        state = load_state()
    print("\n🚿 Plumbing Plan — Level 2...")
    _run_level(state, LEVEL["L2"], sheet_id)


def _run_level(state: dict, level: str, sheet_id: int):
    rooms = [r for r in state.get("rooms", []) if r.get("level") == level]
    placed = 0

    for room in rooms:
        name_lower = room.get("name", "").lower()

        # Tag all existing plumbing fixtures in wet rooms
        if any(kw in name_lower for kw in ["bath", "kitchen", "laundry"]):
            placed += _tag_fixtures(room, state, level)

        # Hose bibs near exterior doors
        if "porch" in name_lower or "outdoor" in name_lower or "garage" in name_lower:
            placed += _place_hose_bib(room, level)

    # Water heater callout
    _place_water_heater_callout(state, level)

    print(f"  ✅ Tagged {placed} plumbing elements on {level}")


def _tag_fixtures(room: dict, state: dict, level: str) -> int:
    placed = 0
    room_id  = room.get("id")
    plumbing = state.get("elements_by_room", {}).get(str(room_id), {}).get("elements", [])

    fixture_keywords = ["toilet", "tub", "sink", "shower", "washer", "dryer"]
    views = state.get("views", {}).get("unplaced", []) + state.get("views", {}).get("on_sheet", [])
    plumbing_view = next((v for v in views if "plumbing" in v.get("name", "").lower() and
                          level.split(".")[-1] in v.get("name", "")), None)

    if not plumbing_view:
        return 0

    view_id = plumbing_view.get("id")
    for fixture in plumbing:
        if any(kw in fixture.get("family_name", "").lower() for kw in fixture_keywords):
            result = rc.call("revit.place_annotation", {
                "annotation_type": "Plumbing Tag",
                "element_id": fixture.get("id"),
                "view_id": view_id,
                "level": level,
            })
            if result.get("success"):
                placed += 1

    return placed


def _place_hose_bib(room: dict, level: str) -> int:
    bbox = room.get("bounding_box", {})
    if not bbox:
        return 0

    # Place at the exterior-facing edge of the room
    x = bbox.get("min_x", 0)
    y = (bbox.get("min_y", 0) + bbox.get("max_y", 0)) / 2

    result = rc.call("revit.place_annotation", {
        "annotation_type": "Hose Bib",
        "location": {"x": x, "y": y, "z": 0},
        "level": level,
        "label": "Hose Bib (typ)",
    })
    return 1 if result.get("success") else 0


def _place_water_heater_callout(state: dict, level: str):
    """Find utility/mechanical/garage room and add water heater + softener callouts."""
    utility_room = next((r for r in state.get("rooms", [])
                         if r.get("level") == level and
                         any(kw in r.get("name", "").lower()
                             for kw in ["utility", "mechanical", "garage", "mudroom"])), None)

    if not utility_room:
        return

    bbox = utility_room.get("bounding_box", {})
    cx   = (bbox.get("min_x", 0) + bbox.get("max_x", 0)) / 2
    cy   = (bbox.get("min_y", 0) + bbox.get("max_y", 0)) / 2

    rc.call("revit.place_annotation", {
        "annotation_type": "Equipment Tag",
        "location": {"x": cx - 1, "y": cy, "z": 0},
        "level": level,
        "label": "Water Heater (size TBD by plumber)",
    })
    rc.call("revit.place_annotation", {
        "annotation_type": "Equipment Tag",
        "location": {"x": cx + 1, "y": cy, "z": 0},
        "level": level,
        "label": "Water Softener (size TBD by plumber)",
    })
