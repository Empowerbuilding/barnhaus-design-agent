"""
completeness.py — Sheet-set completeness gate (offline, state-only).

The classic drafter misses: forgot a sheet, empty populated sheets, blank
titleblock fields, phantom rooms. All computable from project_state.json —
no bridge calls needed.

Required-set config: reference/required_sheets.json (optional) —
  {"required_purposes": ["cover", "floor_plan", ...]}
Falls back to the Barnhaus default set below.
"""

import json
import os

# Default: purposes that a complete Barnhaus residential set must have
# at least one POPULATED sheet for. (Sheet purposes are auto-detected
# from sheet names by core/project_state.py.)
DEFAULT_REQUIRED_PURPOSES = [
    "cover", "floor_plan", "dimension_plan", "elevation",
    "electrical", "plumbing", "roof_plan", "schedule",
]

CONFIG_PATH = os.path.join("reference", "required_sheets.json")


def _required_purposes() -> list:
    if os.path.exists(CONFIG_PATH):
        try:
            cfg = json.load(open(CONFIG_PATH))
            return cfg.get("required_purposes", DEFAULT_REQUIRED_PURPOSES)
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_REQUIRED_PURPOSES


def check_completeness(state: dict) -> list:
    """Run all completeness checks. Returns list of issue dicts."""
    issues = []
    sheets = state.get("sheets") or {}
    if isinstance(sheets, list):
        sheets = {s.get("number", str(s.get("id"))): s for s in sheets}

    issues += _check_required_purposes(sheets)
    issues += _check_empty_sheets(sheets)
    issues += _check_blank_fields(sheets)
    issues += _check_phantom_rooms(state)
    issues += _check_openings_data(state)

    for i in issues:
        i["source"] = "completeness"
    return issues


def _check_required_purposes(sheets: dict) -> list:
    issues = []
    populated_purposes = {s.get("purpose") for s in sheets.values()
                          if s.get("has_content") or s.get("viewport_count", 0) > 0}
    all_purposes = {s.get("purpose") for s in sheets.values()}

    for purpose in _required_purposes():
        if purpose in populated_purposes:
            continue
        if purpose in all_purposes:
            nums = [n for n, s in sheets.items() if s.get("purpose") == purpose]
            issues.append({
                "type": "empty_required_sheet", "severity": "warning",
                "message": f"Required '{purpose}' sheet exists but is EMPTY "
                           f"(no viewports): {', '.join(nums)}",
            })
        else:
            issues.append({
                "type": "missing_required_sheet", "severity": "warning",
                "message": f"No '{purpose}' sheet in the set — required for a "
                           f"complete Barnhaus package.",
            })
    return issues


def _check_empty_sheets(sheets: dict) -> list:
    """Non-required sheets that exist but hold nothing — scrap or fill."""
    required = set(_required_purposes())
    empties = [n for n, s in sheets.items()
               if not s.get("has_content") and s.get("viewport_count", 0) == 0
               and s.get("purpose") not in required]
    if empties:
        return [{
            "type": "empty_sheets", "severity": "info",
            "message": f"{len(empties)} empty sheet(s) in the set: "
                       f"{', '.join(sorted(empties))} — fill or delete before issue.",
        }]
    return []


def _check_blank_fields(sheets: dict) -> list:
    issues = []
    for num, s in sheets.items():
        name = (s.get("name") or "").strip()
        if not name or name.lower() in ("unnamed", "sheet", "new sheet"):
            issues.append({
                "type": "blank_sheet_name", "severity": "warning", "sheet": num,
                "message": f"Sheet {num} has a blank/placeholder name ('{name}').",
            })
        if not (num or "").strip():
            issues.append({
                "type": "blank_sheet_number", "severity": "error",
                "message": f"Sheet id {s.get('id')} has no sheet number.",
            })
    return issues


def _check_phantom_rooms(state: dict) -> list:
    """Large counts of unnamed 'Room' entries = auto-created phantom rooms."""
    rooms = state.get("rooms") or []
    if not rooms:
        return []
    unnamed = [r for r in rooms
               if (r.get("name") or "").strip().lower() in ("room", "", "unnamed")]
    if len(rooms) > 20 and len(unnamed) / len(rooms) > 0.3:
        return [{
            "type": "phantom_rooms", "severity": "warning",
            "message": f"{len(unnamed)} of {len(rooms)} rooms are unnamed 'Room' "
                       f"placeholders — likely phantom rooms from separators. "
                       f"They will pollute schedules and SF totals.",
        }]
    return []


def _check_openings_data(state: dict) -> list:
    """Doors/windows with missing size data — breaks schedules and takeoffs."""
    issues = []
    for cat in ("doors", "windows"):
        bad = [e for e in (state.get(cat) or [])
               if not e.get("width_ft") or not e.get("height_ft")]
        if bad:
            ids = ", ".join(str(e["id"]) for e in bad[:6])
            issues.append({
                "type": f"{cat}_missing_dims", "severity": "warning",
                "message": f"{len(bad)} {cat} missing width/height data "
                           f"(ids: {ids}{'…' if len(bad) > 6 else ''}) — schedule "
                           f"and takeoff rows will be blank.",
            })
    return issues
