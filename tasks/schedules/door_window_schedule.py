"""
door_window_schedule.py — Generates the A105 Door & Window Schedule sheet.

Reads all placed doors and windows from the model, creates Revit schedules,
and places them on sheet A105 in Barnhaus format.
"""

from core import revit_client as rc
from core.project_state import load_state


def run(state: dict = None):
    if state is None:
        state = load_state()

    print("\n📋 Generating Door & Window Schedule (A105)...")

    # Check if A105 already exists
    existing = {s.get("number") for s in state["sheets"]["existing"]}
    if "A105" in existing:
        print("  ↩️  A105 already exists — skipping.")
        return

    # Create door schedule
    door_result = rc.call("revit.create_schedule", {
        "category": "Doors",
        "name": "Door Schedule",
        "fields": ["Mark", "Family and Type", "Width", "Height", "Count", "Comments"],
    })
    door_schedule_id = door_result.get("result", {}).get("schedule_id") if door_result.get("success") else None
    print(f"  {'✅' if door_result.get('success') else '❌'} Door Schedule created")

    # Create window schedule
    win_result = rc.call("revit.create_schedule", {
        "category": "Windows",
        "name": "Window Schedule",
        "fields": ["Mark", "Family and Type", "Width", "Height", "Sill Height", "Count", "Comments"],
    })
    win_schedule_id = win_result.get("result", {}).get("schedule_id") if win_result.get("success") else None
    print(f"  {'✅' if win_result.get('success') else '❌'} Window Schedule created")

    # Create A105 sheet
    sheet_result = rc.create_sheet("A105", "Door & Window Schedule")
    if not sheet_result.get("success"):
        print(f"  ❌ Failed to create A105: {sheet_result.get('error')}")
        return

    sheet_id = sheet_result.get("result", {}).get("sheet_id")
    print(f"  ✅ Sheet A105 created")

    # Place schedules on sheet
    if door_schedule_id:
        rc.place_view_on_sheet(sheet_id, door_schedule_id, x=0.5, y=2.0)
        print(f"  ✅ Door schedule placed on A105")

    if win_schedule_id:
        rc.place_view_on_sheet(sheet_id, win_schedule_id, x=0.5, y=0.5)
        print(f"  ✅ Window schedule placed on A105")

    # Print summary
    doors   = state.get("doors", [])
    windows = state.get("windows", [])
    print(f"\n  📊 Summary: {len(doors)} doors, {len(windows)} windows scheduled")
