"""
intent_queries.py — Targeted model query primitives + intent-vs-model verify.

Priority 1 from ROADMAP.md: Juanito maintains a structured per-project intent
checklist (portal Supabase, table design_intent_items); Blueprint answers each
item with a targeted bridge query and reports PASS / FAIL / NEEDS-HUMAN with
element evidence.

Primitives (usable standalone from any task):
    room_exists_in_region(name_keyword, region)  — region = n/s/e/w half
    elements_exist(category, type_keyword)       — matching element ids
    get_room_area(name_keyword)                  — summed area of matches
    count_elements(category, keyword=None)       — instance count

Verify entry point (wired to `python3 run.py verify <project>`):
    run_verify(project_name)

check_type dispatch (design_intent_items.check_type → primitive):
    room_region     params: {name_keyword, region}
    element_present params: {category, keyword}
    element_absent  params: {category, keyword}
    manual          — skipped, reported NEEDS-HUMAN

⚠️ UNTESTED AGAINST LIVE BRIDGE — see DEV_NOTES.md on this branch for the
assumption list to validate in the first desk session.
"""

import time
from core import revit_client as rc

VALID_REGIONS = {"n", "s", "e", "w"}


# ─────────────────────────────────────────────
# ROOM HELPERS
# ─────────────────────────────────────────────

def _fetch_rooms() -> list:
    """
    Placed rooms with clean name, area and bbox center. Mirrors the
    project_state._scan_rooms read pattern (Name/Area via get_parameter_value,
    bbox via get_element_bounding_box) but skips boundary walls — verify only
    needs name + area + center.
    """
    raw = rc.list_elements_by_category("Rooms")
    rooms = []
    for r in raw:
        eid = r.get("id")
        name = rc.get_parameter_value(eid, "Name") or r.get("name", "")
        try:
            area_sf = round(float(rc.get_parameter_value(eid, "Area") or 0), 1)
        except (TypeError, ValueError):
            area_sf = 0
        if area_sf <= 0:
            continue  # unplaced/phantom rooms — same exclusion as project_state
        bb = rc.get_element_bounding_box(eid)
        center = None
        if bb.get("has_bbox"):
            center = {
                "x": (bb["min"]["x"] + bb["max"]["x"]) / 2,
                "y": (bb["min"]["y"] + bb["max"]["y"]) / 2,
            }
        rooms.append({"id": eid, "name": name, "area_sf": area_sf,
                      "bbox": bb if bb.get("has_bbox") else None,
                      "center": center})
    return rooms


def _model_extents(rooms: list) -> dict | None:
    """
    Model plan extents = union of all placed room bboxes. Rooms define the
    habitable footprint, which is what compass regions are judged against.
    """
    boxes = [r["bbox"] for r in rooms if r.get("bbox")]
    if not boxes:
        return None
    return {
        "min_x": min(b["min"]["x"] for b in boxes),
        "max_x": max(b["max"]["x"] for b in boxes),
        "min_y": min(b["min"]["y"] for b in boxes),
        "max_y": max(b["max"]["y"] for b in boxes),
    }


def _room_regions(room: dict, extents: dict) -> set:
    """
    Which compass halves the room's bbox center falls in. A room can be in
    two regions at once (e.g. {'s', 'w'} = southwest). Center exactly on the
    midline lands in neither half of that axis.
    """
    if not room.get("center") or not extents:
        return set()
    mid_x = (extents["min_x"] + extents["max_x"]) / 2
    mid_y = (extents["min_y"] + extents["max_y"]) / 2
    regions = set()
    if room["center"]["y"] > mid_y:
        regions.add("n")
    elif room["center"]["y"] < mid_y:
        regions.add("s")
    if room["center"]["x"] > mid_x:
        regions.add("e")
    elif room["center"]["x"] < mid_x:
        regions.add("w")
    return regions


# ─────────────────────────────────────────────
# QUERY PRIMITIVES
# ─────────────────────────────────────────────

def room_exists_in_region(name_keyword: str, region: str) -> dict:
    """
    Is there a placed room whose name contains name_keyword with its bbox
    center in the given compass half (n/s/e/w) of the model extents?
    Returns {passed, matches, evidence}.
    """
    region = (region or "").strip().lower()[:1]
    if region not in VALID_REGIONS:
        return {"passed": False, "matches": [],
                "evidence": f"invalid region '{region}' (expected n/s/e/w)"}

    kw = name_keyword.lower()
    rooms = _fetch_rooms()
    extents = _model_extents(rooms)
    if extents is None:
        return {"passed": False, "matches": [],
                "evidence": "no placed rooms with bounding boxes — cannot compute model extents"}

    named = [r for r in rooms if kw in r["name"].lower()]
    if not named:
        return {"passed": False, "matches": [],
                "evidence": f"no room named like '{name_keyword}' "
                            f"(rooms: {', '.join(r['name'] for r in rooms[:15])})"}

    hits, misses = [], []
    for r in named:
        r["regions"] = _room_regions(r, extents)
        (hits if region in r["regions"] else misses).append(r)

    if hits:
        ev = "; ".join(f"Room '{r['name']}' (id {r['id']}, {r['area_sf']} SF) "
                       f"center in {region.upper()} half" for r in hits)
        return {"passed": True, "matches": hits, "evidence": ev}

    ev = "; ".join(f"Room '{r['name']}' (id {r['id']}) is in "
                   f"{'/'.join(sorted(r['regions'])).upper() or 'center'}"
                   f" — not {region.upper()}" for r in misses)
    return {"passed": False, "matches": misses, "evidence": ev}


def _matching_elements(category: str, type_keyword: str = None) -> list:
    """Elements in category whose name/type/family contains type_keyword."""
    elements = rc.list_elements_by_category(category)
    if not type_keyword:
        return elements
    kw = type_keyword.lower()
    out = []
    for e in elements:
        haystack = " ".join(str(e.get(k, "")) for k in
                            ("name", "type", "type_name", "family", "family_name")).lower()
        if kw in haystack:
            out.append(e)
    return out


def elements_exist(category: str, type_keyword: str = None) -> list:
    """Matching element ids for category (+ optional type keyword)."""
    return [e.get("id") for e in _matching_elements(category, type_keyword)]


def get_room_area(name_keyword: str) -> dict:
    """
    Summed area of all placed rooms matching name_keyword.
    Returns {total_sf, rooms: [{id, name, area_sf}]}.
    """
    kw = name_keyword.lower()
    matches = [r for r in _fetch_rooms() if kw in r["name"].lower()]
    return {
        "total_sf": round(sum(r["area_sf"] for r in matches), 1),
        "rooms": [{"id": r["id"], "name": r["name"], "area_sf": r["area_sf"]}
                  for r in matches],
    }


def count_elements(category: str, keyword: str = None) -> int:
    """Instance count for a category, optionally filtered by name/type keyword."""
    return len(_matching_elements(category, keyword))


# ─────────────────────────────────────────────
# VERIFY — intent checklist vs model
# ─────────────────────────────────────────────

def _check_item(item: dict) -> tuple:
    """
    Run one design_intent_items row against the model.
    Returns (result, evidence) where result ∈ PASS / FAIL / NEEDS-HUMAN.
    """
    check_type = (item.get("check_type") or "").strip().lower()
    params = item.get("check_params") or {}

    if check_type == "manual":
        return "NEEDS-HUMAN", "manual check — needs a human eye"

    if check_type == "room_region":
        res = room_exists_in_region(params.get("name_keyword", ""),
                                    params.get("region", ""))
        return ("PASS" if res["passed"] else "FAIL"), res["evidence"]

    if check_type in ("element_present", "element_absent"):
        category = params.get("category", "")
        keyword = params.get("keyword")
        matches = _matching_elements(category, keyword)
        ids = [e.get("id") for e in matches]
        label = f"{category}" + (f" ~ '{keyword}'" if keyword else "")
        if check_type == "element_present":
            if ids:
                return "PASS", f"{len(ids)} {label} found (ids: {_fmt_ids(ids)})"
            return "FAIL", f"no {label} elements in model"
        # element_absent
        if not ids:
            return "PASS", f"no {label} elements — correctly absent"
        return "FAIL", f"{len(ids)} {label} still in model (ids: {_fmt_ids(ids)})"

    return "NEEDS-HUMAN", f"unknown check_type '{check_type}' — cannot automate"


def _fmt_ids(ids: list, limit: int = 8) -> str:
    shown = ", ".join(str(i) for i in ids[:limit])
    more = len(ids) - limit
    return shown + (f" +{more} more" if more > 0 else "")


def run_verify(project_name: str, update_portal: bool = True) -> dict:
    """
    Fetch intent items for project_name from the portal, run each check,
    print one PASS/FAIL/NEEDS-HUMAN line per item, and PATCH each automated
    row's status (verified/failed) + details back to Supabase.
    Returns {passed, failed, needs_human, lines} for the gate.
    """
    from core.portal import fetch_intent_items, update_intent_item

    print(f"\n🔎 Verify — intent vs model for '{project_name}'")
    try:
        items = fetch_intent_items(project_name)
    except Exception as e:
        print(f"❌ Could not fetch intent items from portal: {e}")
        return {"passed": 0, "failed": 0, "needs_human": 0, "lines": [],
                "error": str(e)}

    if not items:
        print(f"  (no design_intent_items rows match '{project_name}')")
        return {"passed": 0, "failed": 0, "needs_human": 0, "lines": []}

    print(f"  {len(items)} intent item{'s' if len(items) != 1 else ''}\n")

    icons = {"PASS": "✅", "FAIL": "❌", "NEEDS-HUMAN": "🖐️"}
    counts = {"PASS": 0, "FAIL": 0, "NEEDS-HUMAN": 0}
    lines = []

    for item in items:
        try:
            result, evidence = _check_item(item)
        except Exception as e:
            result, evidence = "NEEDS-HUMAN", f"check crashed: {e}"
        counts[result] += 1

        line = f"{icons[result]} {result:<11} {item.get('item', '?')} — {evidence}"
        print(f"  {line}")
        lines.append(line)

        if update_portal and result in ("PASS", "FAIL"):
            update_intent_item(item["id"],
                               status="verified" if result == "PASS" else "failed",
                               details={
                                   "result":     result,
                                   "evidence":   evidence,
                                   "check_type": item.get("check_type"),
                                   "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                               })

    print(f"\n  Verify summary: {counts['PASS']} pass, {counts['FAIL']} fail, "
          f"{counts['NEEDS-HUMAN']} needs-human")
    return {"passed": counts["PASS"], "failed": counts["FAIL"],
            "needs_human": counts["NEEDS-HUMAN"], "lines": lines}
