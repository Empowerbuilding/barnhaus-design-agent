"""
draft1_bundle.py — Creates the Draft 1 sheet set.

Sheets created:
  A100   Cover Sheet
  A101.1 Floor Plan Level 1
  A102.1 Dimension Plan L1
  A103   Roof Plan
  A101.2 Floor Plan Level 2  (two-story only)
  A102.2 Dimension Plan L2   (two-story only)

Idempotent — skips sheets that already exist.
"""

from core import revit_client as rc
from core.constants import SHEETS, STANDARD_NOTES
from core.project_state import load_state, existing_sheet_numbers, all_views


def run(state: dict = None):
    if state is None:
        state = load_state()

    is_two_story     = state.get("summary", {}).get("is_two_story", False)
    existing_numbers = existing_sheet_numbers(state)

    sheets_to_create = list(SHEETS["draft1"])
    if is_two_story:
        sheets_to_create += [
            {"number": "A101.2", "name": "Floor Plan Level 2"},
            {"number": "A102.2", "name": "Dimension Plan L2"},
        ]

    print(f"\n📋 Draft 1 Bundle — creating {len(sheets_to_create)} sheets...")
    created = []
    skipped = []

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

            # Place the matching view if it exists
            _place_matching_view(s["number"], sheet_id, state)
        else:
            print(f"  ❌ Failed {s['number']}: {result.get('error')}")

    print(f"\nDraft 1 complete — {len(created)} created, {len(skipped)} skipped.")
    return {"created": created, "skipped": skipped}


def _place_matching_view(sheet_number: str, sheet_id: int, state: dict):
    """Find the matching floor plan / roof plan view and place it on the sheet."""
    view_map = {
        "A101.1": ["Floor Plan", "Level 1", "L1"],
        "A101.2": ["Floor Plan", "Level 2", "L2"],
        "A102.1": ["Floor Plan", "Level 1", "L1"],  # dimension plan uses same view
        "A102.2": ["Floor Plan", "Level 2", "L2"],
        "A103":   ["Roof Plan", "Roof"],
        "A100":   [],  # cover sheet — no view to place
    }

    keywords = view_map.get(sheet_number, [])
    if not keywords:
        return

    views = all_views(state)
    for view in views:
        view_name = view.get("name", "").lower()
        if any(kw.lower() in view_name for kw in keywords):
            result = rc.place_view_on_sheet(sheet_id, view.get("id"), x=1.0, y=1.0)
            if result.get("success"):
                print(f"      → Placed '{view.get('name')}' on {sheet_number}")
            return
