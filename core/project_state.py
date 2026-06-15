"""
project_state.py — Scans the open Revit model and builds a full project state snapshot.

Reads everything: document info, levels, rooms (with areas + bboxes), walls (categorized),
doors (with dimensions), windows (with dimensions), sheets (with viewport counts),
views (typed and categorized), families loaded, and Revit warnings.

Usage:
    from core.project_state import scan_project, load_state
    state = scan_project()
"""

import json
import os
import time
from core import revit_client as rc


STATE_FILE = "project_state.json"

# Sheet purpose detection — maps keywords in sheet names to purpose tags
SHEET_PURPOSE_MAP = {
    "floor plan":       "floor_plan",
    "dimension":        "dimension_plan",
    "ceiling":          "ceiling_plan",
    "roof":             "roof_plan",
    "elevation":        "elevation",
    "interior elev":    "interior_elevation",
    "electrical":       "electrical",
    "plumbing":         "plumbing",
    "column":           "structural",
    "foundation":       "structural",
    "structural":       "structural",
    "section":          "section",
    "site":             "site_plan",
    "cover":            "cover",
    "take off":         "schedule",
    "schedule":         "schedule",
}


def scan_project(save: bool = True) -> dict:
    """
    Scan the active Revit model. Returns structured project state dict.
    Saves to project_state.json by default.
    """
    print("🔍 Scanning Revit model...")
    state = {
        "scanned_at":      time.strftime("%Y-%m-%dT%H:%M:%S"),
        "document":        {},
        "levels":          [],
        "loaded_families": [],
        "rooms":           [],
        "walls":           {"exterior": [], "interior": [], "other": []},
        "doors":           [],
        "windows":         [],
        "sheets":          {},
        "views":           {},
        "warnings":        [],
        "summary":         {},
    }

    if not rc.health_check():
        print("❌ Bridge not reachable — open Revit and connect the addin first.")
        return state

    # ── Document ───────────────────────────────────────────────────────────
    _scan_document(state)

    # ── Levels ─────────────────────────────────────────────────────────────
    _scan_levels(state)

    # ── Families ───────────────────────────────────────────────────────────
    _scan_families(state)

    # ── Rooms ──────────────────────────────────────────────────────────────
    _scan_rooms(state)

    # ── Walls ──────────────────────────────────────────────────────────────
    _scan_walls(state)

    # ── Doors ──────────────────────────────────────────────────────────────
    _scan_doors(state)

    # ── Windows ────────────────────────────────────────────────────────────
    _scan_windows(state)

    # ── Sheets ─────────────────────────────────────────────────────────────
    _scan_sheets(state)

    # ── Views ──────────────────────────────────────────────────────────────
    _scan_views(state)

    # ── Warnings ───────────────────────────────────────────────────────────
    _scan_warnings(state)

    # ── Summary ────────────────────────────────────────────────────────────
    state["summary"] = _build_summary(state)
    _print_summary(state)

    if save:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        print(f"\n💾 State saved to {STATE_FILE}")

    return state


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        raise FileNotFoundError("No project_state.json found. Run scan_project() first.")
    with open(STATE_FILE) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# SCAN SECTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _scan_document(state: dict):
    result = rc.call("revit.get_document_info", {})
    if result.get("success"):
        state["document"] = result.get("result", {})
        print(f"  📄 Project: {state['document'].get('title', 'unknown')}")


def _scan_levels(state: dict):
    result = rc.call("revit.list_levels", {})
    if result.get("success"):
        levels = result.get("result", {}).get("levels", [])
        state["levels"] = levels
        print(f"  🏢 Levels: {len(levels)} — {[l.get('name') for l in levels]}")


def _scan_families(state: dict):
    result = rc.call("revit.list_families", {})
    if result.get("success"):
        families = result.get("result", {}).get("families", [])
        state["loaded_families"] = [f.get("name") for f in families]
        print(f"  📦 Families: {len(state['loaded_families'])} loaded")


def _scan_rooms(state: dict):
    print("  🏠 Rooms...")
    raw = rc.call("revit.list_elements_by_category", {"category": "Rooms"})
    raw_list = raw.get("result", {}).get("elements", []) if raw.get("success") else []

    rooms = []
    for r in raw_list:
        eid = r.get("id")
        # Get clean name and area
        name_res = rc.call("revit.get_parameter_value", {"element_id": eid, "parameter_name": "Name"})
        area_res  = rc.call("revit.get_parameter_value", {"element_id": eid, "parameter_name": "Area"})
        level_res = rc.call("revit.get_parameter_value", {"element_id": eid, "parameter_name": "Level"})
        bb_res    = rc.call("revit.get_element_bounding_box", {"element_id": eid})

        name  = (name_res.get("result") or {}).get("value") or r.get("name", "")
        level = (level_res.get("result") or {}).get("value") or ""
        try:
            area_sf = round(float((area_res.get("result") or {}).get("value", 0)), 1)
        except:
            area_sf = 0

        bbox = None
        if bb_res.get("success") and bb_res.get("result", {}).get("has_bbox"):
            bbox = bb_res["result"]
            # Derive width and depth from bbox
            dx = abs(bbox["max"]["x"] - bbox["min"]["x"])
            dy = abs(bbox["max"]["y"] - bbox["min"]["y"])
            bbox["width_ft"]  = round(min(dx, dy), 2)
            bbox["depth_ft"]  = round(max(dx, dy), 2)

        rooms.append({
            "id":       eid,
            "name":     name,
            "area_sf":  area_sf,
            "level":    level,
            "bbox":     bbox,
            "width_ft": bbox["width_ft"] if bbox else 0,
            "depth_ft": bbox["depth_ft"] if bbox else 0,
        })

    state["rooms"] = rooms
    room_names = [r["name"] for r in rooms]
    print(f"    {len(rooms)} rooms: {', '.join(room_names)}")


def _scan_walls(state: dict):
    print("  🧱 Walls...")
    raw = rc.call("revit.list_elements_by_category", {"category": "Walls"})
    walls = raw.get("result", {}).get("elements", []) if raw.get("success") else []

    ext, int_, other = [], [], []
    for w in walls:
        wtype = w.get("type", w.get("type_name", "")).lower()
        # Enrich with bounding box for position-based checks
        bb_res = rc.call("revit.get_element_bounding_box", {"element_id": w["id"]})
        if bb_res.get("success") and bb_res.get("result", {}).get("has_bbox"):
            bb = bb_res["result"]
            dx = abs(bb["max"]["x"] - bb["min"]["x"])
            dy = abs(bb["max"]["y"] - bb["min"]["y"])
            w["bbox"]       = bb
            w["length_ft"]  = round(max(dx, dy), 2)
            w["orientation"] = "horizontal" if dx > dy else "vertical"
            w["midpoint"]    = {
                "x": (bb["min"]["x"] + bb["max"]["x"]) / 2,
                "y": (bb["min"]["y"] + bb["max"]["y"]) / 2,
            }

        if any(x in wtype for x in ["ext", "7.5", "pbr", "exterior", "2x6", "6\""]):
            ext.append(w)
        elif any(x in wtype for x in ["int", "4.5", "interior", "2x4", "4\""]):
            int_.append(w)
        else:
            other.append(w)

    state["walls"] = {"exterior": ext, "interior": int_, "other": other}
    print(f"    {len(ext)} exterior, {len(int_)} interior, {len(other)} other")


def _scan_doors(state: dict):
    print("  🚪 Doors...")
    raw = rc.call("revit.list_elements_by_category", {"category": "Doors"})
    door_list = raw.get("result", {}).get("elements", []) if raw.get("success") else []

    doors = []
    for d in door_list:
        eid = d.get("id")
        # Get type parameters (family, width, height)
        tp_res = rc.call("revit.get_type_parameters", {"element_id": eid})
        bb_res = rc.call("revit.get_element_bounding_box", {"element_id": eid})

        family_name = d.get("name", "")
        type_name   = d.get("type", "")
        width_ft    = 0.0
        height_ft   = 0.0

        if tp_res.get("success"):
            params = tp_res.get("result", {}).get("parameters", [])
            for p in params:
                pname = p.get("name", "")
                if pname == "Family Name":
                    family_name = p.get("value", family_name)
                elif pname == "Type Name":
                    type_name = p.get("value", type_name)
                elif pname == "Width":
                    try: width_ft = round(float(p.get("value", 0)), 3)
                    except: pass
                elif pname == "Height":
                    try: height_ft = round(float(p.get("value", 0)), 3)
                    except: pass

        bbox = None
        if bb_res.get("success") and bb_res.get("result", {}).get("has_bbox"):
            bbox = bb_res["result"]

        doors.append({
            "id":          eid,
            "family_name": family_name,
            "type_name":   type_name,
            "width_ft":    width_ft,
            "height_ft":   height_ft,
            "width_in":    round(width_ft * 12, 1),
            "height_in":   round(height_ft * 12, 1),
            "bbox":        bbox,
            "center": {
                "x": (bbox["min"]["x"] + bbox["max"]["x"]) / 2,
                "y": (bbox["min"]["y"] + bbox["max"]["y"]) / 2,
            } if bbox else None,
        })

    state["doors"] = doors

    # Print door summary
    door_types = {}
    for d in doors:
        key = f"{d['family_name']} {d['type_name']}"
        door_types[key] = door_types.get(key, 0) + 1
    print(f"    {len(doors)} doors:")
    for dtype, count in sorted(door_types.items(), key=lambda x: -x[1])[:8]:
        print(f"      {count}x {dtype}")


def _scan_windows(state: dict):
    print("  🪟 Windows...")
    raw = rc.call("revit.list_elements_by_category", {"category": "Windows"})
    win_list = raw.get("result", {}).get("elements", []) if raw.get("success") else []

    windows = []
    for w in win_list:
        eid = w.get("id")
        tp_res = rc.call("revit.get_type_parameters", {"element_id": eid})
        bb_res = rc.call("revit.get_element_bounding_box", {"element_id": eid})

        family_name = w.get("name", "")
        type_name   = w.get("type", "")
        width_ft    = 0.0
        height_ft   = 0.0
        sill_ft     = 0.0

        if tp_res.get("success"):
            params = tp_res.get("result", {}).get("parameters", [])
            for p in params:
                pname = p.get("name", "")
                if pname == "Family Name":
                    family_name = p.get("value", family_name)
                elif pname == "Type Name":
                    type_name = p.get("value", type_name)
                elif pname == "Width":
                    try: width_ft = round(float(p.get("value", 0)), 3)
                    except: pass
                elif pname == "Height":
                    try: height_ft = round(float(p.get("value", 0)), 3)
                    except: pass
                elif pname == "Sill Height":
                    try: sill_ft = round(float(p.get("value", 0)), 3)
                    except: pass

        bbox = None
        if bb_res.get("success") and bb_res.get("result", {}).get("has_bbox"):
            bbox = bb_res["result"]

        windows.append({
            "id":          eid,
            "family_name": family_name,
            "type_name":   type_name,
            "width_ft":    width_ft,
            "height_ft":   height_ft,
            "sill_ft":     sill_ft,
            "width_in":    round(width_ft * 12, 1),
            "height_in":   round(height_ft * 12, 1),
            "bbox":        bbox,
            "center": {
                "x": (bbox["min"]["x"] + bbox["max"]["x"]) / 2,
                "y": (bbox["min"]["y"] + bbox["max"]["y"]) / 2,
            } if bbox else None,
        })

    state["windows"] = windows

    win_types = {}
    for w in windows:
        key = f"{w['family_name']} {w['type_name']}"
        win_types[key] = win_types.get(key, 0) + 1
    print(f"    {len(windows)} windows:")
    for wtype, count in sorted(win_types.items(), key=lambda x: -x[1])[:8]:
        print(f"      {count}x {wtype}")


def _scan_sheets(state: dict):
    print("  📋 Sheets...")
    result = rc.call("revit.list_sheets", {})
    sheets_raw = result.get("result", {}).get("sheets", []) if result.get("success") else []

    sheets = {}
    for s in sheets_raw:
        num    = s.get("sheet_number", "")
        name   = s.get("sheet_name", "")
        vp_cnt = s.get("viewport_count", 0)
        purpose = _detect_sheet_purpose(name)
        sheets[num] = {
            "id":             s.get("id"),
            "number":         num,
            "name":           name,
            "viewport_count": vp_cnt,
            "has_content":    vp_cnt > 0,
            "purpose":        purpose,
        }

    state["sheets"] = sheets
    populated = sum(1 for s in sheets.values() if s["has_content"])
    empty     = [s["number"] for s in sheets.values() if not s["has_content"]]
    print(f"    {len(sheets)} sheets — {populated} populated, {len(empty)} empty: {empty}")


def _scan_views(state: dict):
    print("  👁️  Views...")
    result = rc.call("revit.list_views", {})
    views_raw = result.get("result", {}).get("views", []) if result.get("success") else []

    skip_types = {"ProjectBrowser", "SystemBrowser", "Undefined", "DrawingSheet"}
    views = {
        "floor_plans":   [],
        "elevations":    [],
        "sections":      [],
        "schedules":     [],
        "ceiling_plans": [],
        "area_plans":    [],
        "three_d":       [],
        "other":         [],
    }

    for v in views_raw:
        vtype = v.get("type", "")
        if vtype in skip_types:
            continue
        entry = {"id": v["id"], "name": v["name"], "type": vtype, "scale": v.get("scale")}
        if vtype == "FloorPlan":
            views["floor_plans"].append(entry)
        elif vtype == "Elevation":
            views["elevations"].append(entry)
        elif vtype == "Section":
            views["sections"].append(entry)
        elif vtype == "Schedule":
            views["schedules"].append(entry)
        elif vtype == "CeilingPlan":
            views["ceiling_plans"].append(entry)
        elif vtype == "AreaPlan":
            views["area_plans"].append(entry)
        elif vtype == "ThreeD":
            views["three_d"].append(entry)
        else:
            views["other"].append(entry)

    state["views"] = views
    print(f"    {len(views['floor_plans'])} floor plans, {len(views['elevations'])} elevations, "
          f"{len(views['sections'])} sections, {len(views['schedules'])} schedules")

    # Print schedule list — useful for knowing what's already built
    if views["schedules"]:
        sched_names = [v["name"] for v in views["schedules"]]
        print(f"    Schedules: {', '.join(sched_names)}")


def _scan_warnings(state: dict):
    print("  ⚠️  Warnings...")
    result = rc.call("revit.get_warnings", {})
    if result.get("success"):
        warnings = result.get("result", {}).get("warnings", [])
        state["warnings"] = warnings
        by_type = {}
        for w in warnings:
            desc = w["description"][:60]
            by_type[desc] = by_type.get(desc, 0) + 1
        print(f"    {len(warnings)} total:")
        for desc, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"      {count}x {desc}...")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY + HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(state: dict) -> dict:
    levels     = state.get("levels", [])
    rooms      = state.get("rooms", [])
    sheets     = state.get("sheets", {})
    views      = state.get("views", {})
    warnings   = state.get("warnings", [])

    room_names = [r["name"] for r in rooms]
    level_count = len([l for l in levels if "roof" not in l.get("name","").lower()])

    total_sf = sum(r["area_sf"] for r in rooms if r["area_sf"] > 0)

    empty_sheets = [num for num, s in sheets.items() if not s["has_content"]]

    warn_types = {
        "overlapping_walls":   len([w for w in warnings if "overlap" in w["description"].lower() and "wall" in w["description"].lower()]),
        "overlapping_inserts": len([w for w in warnings if "insert" in w["description"].lower() and "overlap" in w["description"].lower()]),
        "missing_targets":     len([w for w in warnings if "miss" in w["description"].lower() and "target" in w["description"].lower()]),
        "off_axis":            len([w for w in warnings if "off axis" in w["description"].lower()]),
        "stair_issues":        len([w for w in warnings if "stair" in w["description"].lower()]),
    }

    return {
        "title":           state["document"].get("title", ""),
        "level_count":     level_count,
        "is_two_story":    level_count >= 2,
        "is_three_story":  level_count >= 3,
        "room_count":      len(rooms),
        "room_names":      room_names,
        "total_sf":        round(total_sf, 0),
        "door_count":      len(state.get("doors", [])),
        "window_count":    len(state.get("windows", [])),
        "sheet_count":     len(sheets),
        "empty_sheets":    empty_sheets,
        "schedule_count":  len(views.get("schedules", [])),
        "section_count":   len(views.get("sections", [])),
        "warnings":        warn_types,
        "family_count":    len(state.get("loaded_families", [])),
    }


def _print_summary(state: dict):
    s   = state["summary"]
    doc = state["document"]
    print("\n" + "═"*55)
    print(f"  PROJECT: {s['title']}")
    print(f"  Path:    {doc.get('path','')}")
    print("═"*55)
    print(f"  Stories:  {s['level_count']}")
    print(f"  Rooms:    {s['room_count']}  ({s['total_sf']:.0f} SF total)")
    print(f"            {', '.join(s['room_names'])}")
    print(f"  Doors:    {s['door_count']}   Windows: {s['window_count']}")
    print(f"  Sheets:   {s['sheet_count']} total — {len(s['empty_sheets'])} empty ({', '.join(s['empty_sheets'])})")
    print(f"  Schedules:{s['schedule_count']}   Sections: {s['section_count']}")
    w = s["warnings"]
    print(f"  Warnings: {sum(w.values())} total — "
          f"{w['overlapping_inserts']} insert conflicts, "
          f"{w['missing_targets']} missing targets, "
          f"{w['off_axis']} off-axis, "
          f"{w['stair_issues']} stair issues")
    print("═"*55 + "\n")


def _detect_sheet_purpose(name: str) -> str:
    name_lower = name.lower()
    for keyword, purpose in SHEET_PURPOSE_MAP.items():
        if keyword in name_lower:
            return purpose
    return "other"
