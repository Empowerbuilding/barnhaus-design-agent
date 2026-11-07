"""
model_work_qa.py — Post-placement QA gate for interior build-out work.

Catches the error classes Mitch caught manually on Deubner D2 (2026-11-05/06):
  - bare / unnamed Specialty Equipment + DirectShapes (Component-First doctrine)
  - sinks not seated in countertop cutouts (sunken or floating)
  - ceilings protruding past their room boundary
  - double-placed elements (near-identical bboxes, same type)
  - floor-mounted fixtures floating above the floor

Self-contained scan: pulls only the placement categories (NOT a full project
scan) so it stays fast enough to gate every placement batch. All bridge access
goes through core.revit_client.call().

Usage:
    from qa.model_work_qa import run_model_work_qa
    report = run_model_work_qa()                      # full placement scan
    report = run_model_work_qa(element_ids=[...])     # scoped to changed ids
    report = run_model_work_qa(element_ids=[...], rooms_override=state_rooms)

Report format matches qa_runner: {"total", "fix", "consider", "fyi"} with
issue dicts {type, severity, element_id, room, message, auto_fixable}.
Exit-friendly: report["fix"] non-empty = gate FAIL.
"""

import re

from core import revit_client as rc

PLACEMENT_CATEGORIES = [
    "Casework",
    "Plumbing Fixtures",
    "Furniture",
    "Specialty Equipment",
    "Ceilings",
    "Generic Models",
]

# Floor-mounted fixture families (bbox min.z must sit near a level)
_FLOOR_MOUNTED = re.compile(
    r"toilet|vanity|range|cooktop|refrig|fridge|dishwasher|washer|dryer|bathtub|tub",
    re.IGNORECASE,
)
# Wall/ceiling-mounted items whose names contain floor-mount keywords
# ("Cabinet OVER TOILET", "RANGE Hood") must not be flagged as floating.
_WALL_MOUNTED = re.compile(
    r"over|wall|upper|hood|shelf|shelve|mirror|med cabinet|hung",
    re.IGNORECASE,
)
# Sink-ish plumbing fixtures (seating check applies)
_SINK = re.compile(r"sink|basin|lavatory|bowl", re.IGNORECASE)
# Counter-ish casework/furniture (thin-ish slab at counter height)
_COUNTER = re.compile(r"counter|countertop|base cab|vanity top|island|bar top|work top", re.IGNORECASE)
# Systematic DS naming per AGENTS.md doctrine: <Category> — <Item> — <Location> — <Finish>
def _is_systematically_named(label):
    """Doctrine: '<Category> — <Item> — <Location> — <Finish>' — 3+ dash-separated parts."""
    parts = re.split(r"—|\s-\s", label)
    return len([p for p in parts if p.strip()]) >= 3
_DEFAULT_NAME = re.compile(r"^\s*(direct ?shape|generic model|family|element)?\s*\d*\s*$", re.IGNORECASE)

# ─────────────────────────────────────────────
# SCAN
# ─────────────────────────────────────────────

def _el_field(el, *keys):
    for k in keys:
        if k in el and el[k] not in (None, ""):
            return el[k]
    return None


def _get_bbox(eid):
    try:
        res = rc.call("revit.get_element_bounding_box", {"element_id": eid})
        if res.get("success") and (res.get("result") or {}).get("has_bbox"):
            return res["result"]
    except Exception:
        pass
    return None


def _scan_category(category, only_ids=None):
    """List a placement category and pull bboxes. Returns element dicts."""
    res = rc.call("revit.list_elements_by_category", {"category": category})
    if not res.get("success"):
        return []
    raw = res.get("result")
    if isinstance(raw, dict):
        raw = raw.get("elements", raw.get("result", []))
    if not isinstance(raw, list):
        return []

    out = []
    for el in raw:
        eid = _el_field(el, "id", "element_id", "Id")
        if eid is None:
            continue
        if only_ids is not None and eid not in only_ids:
            continue
        fam = _el_field(el, "family", "family_name", "Family")
        typ = _el_field(el, "type", "type_name", "Type")
        name = _el_field(el, "name", "Name", "element_name")
        out.append({
            "id": eid,
            "category": category,
            "family": fam or "",
            "type": typ or "",
            "name": name or "",
            "bbox": _get_bbox(eid),
        })
    return out


def _scan_levels():
    res = rc.call("revit.list_levels", {})
    if not res.get("success"):
        return []
    raw = res.get("result")
    if isinstance(raw, dict):
        raw = raw.get("levels", raw.get("result", []))
    if not isinstance(raw, list):
        return []
    out = []
    for lv in raw:
        elev = _el_field(lv, "elevation", "elevation_ft", "Elevation")
        if elev is None:
            continue
        try:
            out.append(float(elev))
        except (TypeError, ValueError):
            continue
    return out


def _scan_rooms():
    res = rc.call("revit.list_elements_by_category", {"category": "Rooms"})
    if not res.get("success"):
        return []
    raw = res.get("result")
    if isinstance(raw, dict):
        raw = raw.get("elements", raw.get("result", []))
    if not isinstance(raw, list):
        return []
    out = []
    for el in raw:
        eid = _el_field(el, "id", "element_id", "Id")
        if eid is None:
            continue
        out.append({
            "id": eid,
            "name": _el_field(el, "name", "Name") or "",
            "bbox": _get_bbox(eid),
        })
    return out


# ─────────────────────────────────────────────
# GEOMETRY HELPERS
# ─────────────────────────────────────────────

def _xy_overlap(a, b):
    """XY footprint overlap fraction of a inside b (0..1). None if no bbox."""
    if not a or not b:
        return None
    ix = min(a["max"]["x"], b["max"]["x"]) - max(a["min"]["x"], b["min"]["x"])
    iy = min(a["max"]["y"], b["max"]["y"]) - max(a["min"]["y"], b["min"]["y"])
    if ix <= 0 or iy <= 0:
        return 0.0
    ax = a["max"]["x"] - a["min"]["x"]
    ay = a["max"]["y"] - a["min"]["y"]
    if ax <= 0 or ay <= 0:
        return 0.0
    return (ix * iy) / (ax * ay)


def _center_xy(bbox):
    return ((bbox["min"]["x"] + bbox["max"]["x"]) / 2.0,
            (bbox["min"]["y"] + bbox["max"]["y"]) / 2.0)


# ─────────────────────────────────────────────
# CHECKS
# ─────────────────────────────────────────────

def _check_naming_discipline(elements):
    """Component-First doctrine: no bare/unnamed Specialty Equipment or
    Generic-Model DirectShapes. Systematic names have the 3+ part pattern."""
    issues = []
    for el in elements:
        if el["category"] not in ("Specialty Equipment", "Generic Models"):
            continue
        label = el["name"] or el["type"] or el["family"]
        if not label or _DEFAULT_NAME.match(label):
            issues.append({
                "type": "unnamed_element",
                "severity": "fix",
                "element_id": el["id"],
                "category": el["category"],
                "message": f"{el['category']} {el['id']} has no systematic name "
                           f"(family='{el['family']}', type='{el['type']}'). "
                           f"Rebuild as family, or name it "
                           f"'<Category> — <Item> — <Location> — <Finish>'.",
                "auto_fixable": False,
            })
        elif "specialty" in el["category"].lower() and not _is_systematically_named(label):
            issues.append({
                "type": "bare_specialty_equipment",
                "severity": "consider",
                "element_id": el["id"],
                "category": el["category"],
                "message": f"Specialty Equipment {el['id']} ('{label}') is a DirectShape "
                           f"outside the naming discipline. Confirm category + shared "
                           f"params are right (schedules/takeoffs key off these).",
                "auto_fixable": False,
            })
    return issues


def _check_sink_seating(elements):
    """Every sink must sit in a countertop: bowl bottom slightly below counter
    top (seated), not sunken deep and not floating above it."""
    sinks = [e for e in elements if e["category"] == "Plumbing Fixtures"
             and _SINK.search(f"{e['family']} {e['type']} {e['name']}")]
    counters = [e for e in elements if e["category"] in ("Casework", "Furniture",
                                                          "Specialty Equipment",
                                                          "Generic Models")
                and _COUNTER.search(f"{e['family']} {e['type']} {e['name']}")]
    # Fall back: any casework slab whose bbox height is counter-ish (2–4.5 ft)
    # when no explicit counter names exist.
    if not counters:
        counters = [e for e in elements if e["category"] == "Casework" and e["bbox"]
                    and 1.5 <= (e["bbox"]["max"]["z"] - e["bbox"]["min"]["z"]) <= 4.5]

    issues = []
    for s in sinks:
        if not s["bbox"]:
            continue
        best = None  # (overlap_frac, counter)
        for c in counters:
            if not c["bbox"]:
                continue
            ov = _xy_overlap(s["bbox"], c["bbox"])
            if ov and (best is None or ov > best[0]):
                best = (ov, c)
        if best is None or best[0] < 0.5:
            issues.append({
                "type": "sink_no_counter",
                "severity": "fix",
                "element_id": s["id"],
                "message": f"Sink {s['id']} ('{s['family']} {s['type']}') has no countertop "
                           f"under it (no counter bbox overlap ≥50%). Place/extend the counter "
                           f"or cut it into the slab.",
                "auto_fixable": False,
            })
            continue
        c = best[1]
        counter_top = c["bbox"]["max"]["z"]
        bowl_bottom = s["bbox"]["min"]["z"]
        sink_top = s["bbox"]["max"]["z"]
        if bowl_bottom < counter_top - 0.35:
            issues.append({
                "type": "sink_sunken",
                "severity": "fix",
                "element_id": s["id"],
                "message": f"Sink {s['id']} is SUNKEN: bowl bottom "
                           f"{bowl_bottom:.2f} vs counter top {counter_top:.2f} "
                           f"({counter_top - bowl_bottom:.2f} ft below). Likely set off the "
                           f"family bbox top (faucet tip), not the rim. Re-seat on counter "
                           f"top minus rim depth.",
                "auto_fixable": False,
            })
        elif bowl_bottom > counter_top + 0.15:
            issues.append({
                "type": "sink_floating",
                "severity": "fix",
                "element_id": s["id"],
                "message": f"Sink {s['id']} FLOATS {bowl_bottom - counter_top:.2f} ft above "
                           f"counter {c['id']} top. Drop it into the cutout.",
                "auto_fixable": False,
            })
    return issues


def _check_ceiling_boundaries(elements, rooms):
    """Ceilings must stay inside room boundaries — the kitchen-ceiling-into-
    living-room class of error. Protrusion past ALL rooms = fix; spanning
    multiple rooms = consider (open-plan may be intentional)."""
    ceilings = [e for e in elements if e["category"] == "Ceilings" and e["bbox"]]
    room_bbs = [r["bbox"] for r in rooms if r["bbox"]]
    issues = []
    for ce in ceilings:
        inside_any = False
        spanning = 0
        for rb in room_bbs:
            ov = _xy_overlap(ce["bbox"], rb)
            if ov and ov > 0.05:
                spanning += 1
            # ceiling center inside this room?
            cx, cy = _center_xy(ce["bbox"])
            if (rb["min"]["x"] <= cx <= rb["max"]["x"]
                    and rb["min"]["y"] <= cy <= rb["max"]["y"]):
                inside_any = True
        if room_bbs and not inside_any:
            # Crosses a wall (overlaps a room but center outside) = likely wrong
            # boundary -> fix. Fully clear of all rooms = porch/overhang -> fyi.
            overlaps_room = any((_xy_overlap(ce["bbox"], rb) or 0) > 0.05 for rb in room_bbs)
            issues.append({
                "type": "ceiling_outside_rooms",
                "severity": "fix" if overlaps_room else "fyi",
                "element_id": ce["id"],
                "message": (f"Ceiling {ce['id']} center is not inside any room but overlaps one — "
                            f"boundary likely crosses a wall. Check the room/ceiling polygon."
                            if overlaps_room else
                            f"Ceiling {ce['id']} is outside all rooms — porch/overhang? Confirm "
                            f"intentional."),
                "auto_fixable": False,
            })
        elif spanning > 1:
            issues.append({
                "type": "ceiling_spans_rooms",
                "severity": "fyi",
                "element_id": ce["id"],
                "message": f"Ceiling {ce['id']} spans {spanning} rooms. "
                           f"Intentional for open plan; if not, split at the wall.",
                "auto_fixable": False,
            })
    return issues


def _check_duplicates(elements):
    """Same category + same type + bbox centers within 0.15 ft = double-placed."""
    issues = []
    by_key = {}
    for el in elements:
        if not el["bbox"]:
            continue
        key = (el["category"], el["family"], el["type"])
        by_key.setdefault(key, []).append(el)
    for (cat, fam, typ), els in by_key.items():
        for i in range(len(els)):
            for j in range(i + 1, len(els)):
                a, b = els[i], els[j]
                ax, ay = _center_xy(a["bbox"])
                bx, by = _center_xy(b["bbox"])
                az = (a["bbox"]["min"]["z"] + a["bbox"]["max"]["z"]) / 2.0
                bz = (b["bbox"]["min"]["z"] + b["bbox"]["max"]["z"]) / 2.0
                if abs(ax - bx) < 0.15 and abs(ay - by) < 0.15 and abs(az - bz) < 0.5:
                    issues.append({
                        "type": "duplicate_placement",
                        "severity": "fix",
                        "element_id": b["id"],
                        "message": f"Possible double-place: {cat} '{fam} {typ}' ids "
                                   f"{a['id']} and {b['id']} share a bbox center "
                                   f"(within 0.15 ft). Delete one.",
                        "auto_fixable": False,
                    })
    return issues


def _check_floor_mounted(elements, levels):
    """Floor-mounted fixtures must sit near a level elevation (not floating)."""
    if not levels:
        return []
    issues = []
    for el in elements:
        if el["category"] not in ("Plumbing Fixtures", "Casework", "Specialty Equipment",
                                  "Furniture", "Generic Models"):
            continue
        label = f"{el['family']} {el['type']}"
        if not _FLOOR_MOUNTED.search(label):
            continue
        if _WALL_MOUNTED.search(label):
            continue  # wall/ceiling-mounted (e.g. "Cabinet Over Toilet", "Range Hood")
        if not el["bbox"]:
            continue
        min_z = el["bbox"]["min"]["z"]
        nearest = min(abs(min_z - lv) for lv in levels)
        if nearest > 0.5:
            issues.append({
                "type": "floating_fixture",
                "severity": "fix",
                "element_id": el["id"],
                "message": f"Floor-mounted '{el['family']} {el['type']}' {el['id']} sits "
                           f"{nearest:.2f} ft from the nearest level elevation — floating. "
                           f"Re-host or drop to floor.",
                "auto_fixable": False,
            })
    return issues


# ─────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────

def run_model_work_qa(element_ids=None, categories=None):
    """Scan placement categories and run all model-work checks.

    element_ids: optional set/list — scope to these ids (e.g. from the change
                 feed). None = full placement scan.
    Returns report dict; report["fix"] non-empty = gate FAIL.
    """
    cats = categories or PLACEMENT_CATEGORIES
    only = set(element_ids) if element_ids is not None else None

    print("\n🔎 Model-work QA gate — scanning placement categories...")
    elements = []
    for cat in cats:
        els = _scan_category(cat, only_ids=only)
        print(f"  {cat}: {len(els)} elements")
        elements += els

    levels = _scan_levels()
    rooms = _scan_rooms()

    all_issues = []
    all_issues += _check_naming_discipline(elements)
    all_issues += _check_sink_seating(elements)
    all_issues += _check_ceiling_boundaries(elements, rooms)
    all_issues += _check_duplicates(elements)
    all_issues += _check_floor_mounted(elements, levels)

    # Dedupe (type + message prefix)
    seen, deduped = set(), []
    for i in all_issues:
        key = (i.get("type"), i.get("message", "")[:80])
        if key not in seen:
            seen.add(key)
            deduped.append(i)

    report = {
        "scanned": len(elements),
        "total": len(deduped),
        "fix": [i for i in deduped if i["severity"] == "fix"],
        "consider": [i for i in deduped if i["severity"] == "consider"],
        "fyi": [i for i in deduped if i["severity"] == "fyi"],
    }
    _print(report)
    return report


def _print(report):
    print("─" * 50)
    if report["total"] == 0:
        print(f"✅ Model-work QA CLEAN ({report['scanned']} elements scanned)")
        return
    print(f"MODEL-WORK QA — {report['total']} findings "
          f"({report['scanned']} elements scanned)")
    for sev, sym in (("fix", "🔴"), ("consider", "🟡"), ("fyi", "🔵")):
        for i in report[sev]:
            print(f"  {sym} [{i['type']}] {i['message']}")
    print("─" * 50)
