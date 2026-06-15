"""
project_state.py — Scans the open Revit model and builds a full project state snapshot.

Run this at the start of every session. Everything else (QA, tasks, agent) reads from this.

Usage:
    from core.project_state import scan_project
    state = scan_project()  # returns dict, also saves project_state.json
"""

import json
import os
import time
from core import revit_client as rc


STATE_FILE = "project_state.json"


def scan_project(save: bool = True) -> dict:
    """
    Scan the active Revit model. Returns structured project state dict.
    Saves to project_state.json by default.
    """
    print("🔍 Scanning Revit model...")
    state = {
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "document":   None,
        "levels":     [],
        "rooms":      [],
        "walls":      {"exterior": [], "interior": [], "other": []},
        "doors":      [],
        "windows":    [],
        "sheets":     {"existing": [], "missing_draft1": [], "missing_draft2": [], "missing_draft3": []},
        "views":      {"on_sheet": [], "unplaced": []},
        "warnings":   [],
    }

    if not rc.health_check():
        print("❌ Bridge not reachable — open Revit and connect the addin first.")
        return state

    # ── Document info ───────────────────────────────────────────────────────
    doc_info = rc.call("revit.get_document_info", {})
    if doc_info.get("success"):
        state["document"] = doc_info.get("result", {})
        print(f"  Project: {state['document'].get('title', 'unknown')}")

    # ── Families loaded ─────────────────────────────────────────────────────
    fam_result = rc.call("revit.list_families", {})
    if fam_result.get("success"):
        families = fam_result.get("result", {}).get("families", [])
        state["loaded_families"] = [f.get("name") for f in families]
        print(f"  Families: {len(state['loaded_families'])} loaded")

    # ── Rooms ──────────────────────────────────────────────────────────────
    print("  Rooms...")
    rooms = rc.get_all_rooms()
    state["rooms"] = rooms
    print(f"    {len(rooms)} rooms found")

    # ── Walls ──────────────────────────────────────────────────────────────
    print("  Walls...")
    walls = rc.get_all_walls()
    for w in walls:
        wtype = w.get("type", w.get("type_name", ""))
        # Flexible matching — works with any template
        wtype_lower = wtype.lower()
        if any(x in wtype_lower for x in ["ext", "7.5", "pbr", "exterior", "6x", "2x6"]):
            state["walls"]["exterior"].append(w)
        elif any(x in wtype_lower for x in ["int", "4.5", "interior", "2x4"]):
            state["walls"]["interior"].append(w)
        else:
            state["walls"]["other"].append(w)
    ext_count = len(state["walls"]["exterior"])
    int_count  = len(state["walls"]["interior"])
    print(f"    {ext_count} exterior, {int_count} interior, {len(state['walls']['other'])} other")

    # ── Doors ──────────────────────────────────────────────────────────────
    print("  Doors...")
    doors = rc.get_all_doors()
    state["doors"] = doors
    print(f"    {len(doors)} doors")

    # ── Windows ────────────────────────────────────────────────────────────
    print("  Windows...")
    windows = rc.get_all_windows()
    state["windows"] = windows
    print(f"    {len(windows)} windows")

    # ── Sheets ─────────────────────────────────────────────────────────────
    print("  Sheets...")
    from core.constants import SHEETS
    existing_sheets = rc.list_sheets()
    state["sheets"]["existing"] = existing_sheets
    existing_numbers = {s.get("number") for s in existing_sheets}

    for s in SHEETS["draft1"]:
        if s["number"] not in existing_numbers:
            state["sheets"]["missing_draft1"].append(s)

    for s in SHEETS["draft2_additions"]:
        if s["number"] not in existing_numbers:
            state["sheets"]["missing_draft2"].append(s)

    for s in SHEETS["draft3_additions"]:
        if s["number"] not in existing_numbers:
            state["sheets"]["missing_draft3"].append(s)

    print(f"    {len(existing_sheets)} existing, "
          f"{len(state['sheets']['missing_draft1'])} missing D1, "
          f"{len(state['sheets']['missing_draft2'])} missing D2, "
          f"{len(state['sheets']['missing_draft3'])} missing D3")

    # ── Views ──────────────────────────────────────────────────────────────
    print("  Views...")
    views = rc.list_views()
    for v in views:
        if v.get("sheet_id"):
            state["views"]["on_sheet"].append(v)
        else:
            state["views"]["unplaced"].append(v)
    print(f"    {len(state['views']['on_sheet'])} on sheets, {len(state['views']['unplaced'])} unplaced")

    # ── Summary ────────────────────────────────────────────────────────────
    state["summary"] = _build_summary(state)
    _print_summary(state["summary"])

    if save:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        print(f"\n💾 State saved to {STATE_FILE}")

    return state


def load_state() -> dict:
    """Load the last saved project state."""
    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError(f"No project_state.json found. Run scan_project() first.")
    with open(STATE_FILE) as f:
        return json.load(f)


def _build_summary(state: dict) -> dict:
    rooms = state["rooms"]
    room_names = [r.get("name", "") for r in rooms]

    has_master   = any("master" in n.lower() for n in room_names)
    has_kitchen  = any("kitchen" in n.lower() for n in room_names)
    has_garage   = any("garage" in n.lower() for n in room_names)
    is_two_story = any(r.get("level", "").startswith("Level 2") for r in rooms)

    return {
        "room_count":     len(rooms),
        "room_names":     room_names,
        "has_master":     has_master,
        "has_kitchen":    has_kitchen,
        "has_garage":     has_garage,
        "is_two_story":   is_two_story,
        "door_count":     len(state["doors"]),
        "window_count":   len(state["windows"]),
        "sheet_count":    len(state["sheets"]["existing"]),
        "draft1_complete": len(state["sheets"]["missing_draft1"]) == 0,
        "draft2_complete": len(state["sheets"]["missing_draft2"]) == 0,
        "draft3_complete": len(state["sheets"]["missing_draft3"]) == 0,
    }


def _print_summary(summary: dict):
    print("\n─────────────────────────────────────")
    print("📋 PROJECT STATE SUMMARY")
    print(f"   Rooms: {summary['room_count']} — {', '.join(summary['room_names'][:6])}{'...' if len(summary['room_names']) > 6 else ''}")
    print(f"   Doors: {summary['door_count']}  Windows: {summary['window_count']}")
    print(f"   Two-story: {'Yes' if summary['is_two_story'] else 'No'}")
    print(f"   Sheets: {summary['sheet_count']} existing")
    print(f"   Draft 1: {'✅ Complete' if summary['draft1_complete'] else '⚠️  Incomplete'}")
    print(f"   Draft 2: {'✅ Complete' if summary['draft2_complete'] else '⚠️  Incomplete'}")
    print(f"   Draft 3: {'✅ Complete' if summary['draft3_complete'] else '⚠️  Incomplete'}")
    print("─────────────────────────────────────\n")
