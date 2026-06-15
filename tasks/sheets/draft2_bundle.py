"""
draft2_bundle.py — Creates the Draft 2 sheet additions.

Sheets created (on top of Draft 1):
  A105   Door & Window Schedule
  A106   Exterior Elevations - Front
  A106.1 Exterior Elevations - Left
  A106.2 Exterior Elevations - Right / Rear
  A107   Interior Elevations - Kitchen
  A107.1 Interior Elevations - Master Bath
  A107.2 Interior Elevations - Laundry

Also creates elevation views if they don't exist yet (reads building footprint → places
elevation markers at each face).

Idempotent — skips sheets that already exist.
"""

from core import revit_client as rc
from core.constants import SHEETS, LEVEL
from core.project_state import load_state


ELEVATION_VIEWS = [
    {"sheet": "A106",   "name": "Elevation - Front (South)",  "face": "S"},
    {"sheet": "A106.1", "name": "Elevation - Left (West)",    "face": "W"},
    {"sheet": "A106.2", "name": "Elevation - Right (East)",   "face": "E"},
    {"sheet": "A106.2", "name": "Elevation - Rear (North)",   "face": "N"},
]

INTERIOR_ELEVATIONS = [
    {"sheet": "A107",   "room_keyword": "kitchen",     "name": "Interior Elev - Kitchen"},
    {"sheet": "A107.1", "room_keyword": "master bath",  "name": "Interior Elev - Master Bath"},
    {"sheet": "A107.2", "room_keyword": "laundry",      "name": "Interior Elev - Laundry"},
]


def run(state: dict = None):
    if state is None:
        state = load_state()

    existing_numbers = {s.get("number") for s in state["sheets"]["existing"]}
    sheets_to_create = SHEETS["draft2_additions"]

    print(f"\n📋 Draft 2 Bundle — creating {len(sheets_to_create)} sheets...")
    created = []
    skipped = []

    # Ensure exterior elevation views exist first
    _ensure_exterior_elevations(state)

    for s in sheets_to_create:
        if s["number"] in existing_numbers:
            print(f"  ↩️  Skip {s['number']} — already exists")
            skipped.append(s["number"])
            continue

        result = rc.create_sheet(s["number"], s["name"])
        if result.get("success"):
            sheet_id = result.get("result", {}).get("sheet_id")
            print(f"  ✅ Created {s['number']} — {s['name']}")
            created.append({"number": s["number"], "name": s["name"], "id": sheet_id})
            _place_matching_view(s["number"], sheet_id, state)
        else:
            print(f"  ❌ Failed {s['number']}: {result.get('error')}")

    print(f"\nDraft 2 complete — {len(created)} created, {len(skipped)} skipped.")
    return {"created": created, "skipped": skipped}


def _ensure_exterior_elevations(state: dict):
    """Create exterior elevation views if they don't already exist."""
    existing_views = {v.get("name") for v in
                      state.get("views", {}).get("on_sheet", []) +
                      state.get("views", {}).get("unplaced", [])}

    # Get approximate building center from exterior walls
    ext_walls = state.get("walls", {}).get("exterior", [])
    if not ext_walls:
        print("  ⚠️  No exterior walls found — can't auto-place elevation markers")
        return

    xs = [w.get("midpoint", {}).get("x", 0) for w in ext_walls]
    ys = [w.get("midpoint", {}).get("y", 0) for w in ext_walls]
    cx = sum(xs) / len(xs) if xs else 0
    cy = sum(ys) / len(ys) if ys else 0

    for ev in ELEVATION_VIEWS:
        if ev["name"] not in existing_views:
            result = rc.create_elevation(ev["name"], cx, cy, facing=ev["face"])
            if result.get("success"):
                print(f"  📐 Created elevation view: {ev['name']}")


def _place_matching_view(sheet_number: str, sheet_id: int, state: dict):
    all_views = (state.get("views", {}).get("unplaced", []) +
                 state.get("views", {}).get("on_sheet", []))

    # Map sheet numbers to view name keywords
    keywords_map = {
        "A105":   ["door", "window", "schedule"],
        "A106":   ["front", "south elevation"],
        "A106.1": ["left", "west elevation"],
        "A106.2": ["right", "east", "rear", "north elevation"],
        "A107":   ["kitchen", "interior elev"],
        "A107.1": ["master bath", "interior elev"],
        "A107.2": ["laundry", "interior elev"],
    }

    keywords = keywords_map.get(sheet_number, [])
    if not keywords:
        return

    for view in all_views:
        vname = view.get("name", "").lower()
        if any(kw.lower() in vname for kw in keywords):
            result = rc.place_view_on_sheet(sheet_id, view.get("id"), x=1.0, y=1.0)
            if result.get("success"):
                print(f"      → Placed '{view.get('name')}' on {sheet_number}")
            return
