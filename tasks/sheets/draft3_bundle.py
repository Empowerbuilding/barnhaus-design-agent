"""
draft3_bundle.py — Creates the Draft 3 sheet additions (MEP + structural).

Sheets created (on top of Draft 2):
  A104   Structural Column Grid
  A108.1 Electrical Plan L1
  A109.2 Plumbing Plan L1
  A108.2 Electrical Plan L2  (two-story only)
  A109.3 Plumbing Plan L2    (two-story only)

Delegates actual plan generation to tasks/mep/electrical.py and tasks/mep/plumbing.py.
"""

from core import revit_client as rc
from core.constants import SHEETS
from core.project_state import load_state
from tasks.mep import electrical, plumbing


def run(state: dict = None):
    if state is None:
        state = load_state()

    is_two_story     = state.get("summary", {}).get("is_two_story", False)
    existing_numbers = {s.get("number") for s in state["sheets"]["existing"]}

    sheets_to_create = list(SHEETS["draft3_additions"])
    if is_two_story:
        sheets_to_create += [
            {"number": "A108.2", "name": "Electrical Plan L2"},
            {"number": "A109.3", "name": "Plumbing Plan L2"},
        ]

    print(f"\n📋 Draft 3 Bundle — creating {len(sheets_to_create)} sheets...")
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

            # Run the actual plan generation for MEP sheets
            if s["number"] == "A108.1":
                electrical.run_l1(state, sheet_id)
            elif s["number"] == "A108.2":
                electrical.run_l2(state, sheet_id)
            elif s["number"] == "A109.2":
                plumbing.run_l1(state, sheet_id)
            elif s["number"] == "A109.3":
                plumbing.run_l2(state, sheet_id)
        else:
            print(f"  ❌ Failed {s['number']}: {result.get('error')}")

    print(f"\nDraft 3 complete — {len(created)} created, {len(skipped)} skipped.")
    return {"created": created, "skipped": skipped}
