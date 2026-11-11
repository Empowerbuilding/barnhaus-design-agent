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
    # openings (2026-11-11): a phase that places doors / windows must have them scanned
    "Doors",
    "Windows",
]

# Shell and site (2026-11-11, Tony: a phase that writes anything shows coverage of what it
# wrote). Scanned when the gate is scoped to recent changes or a phase names what it wrote
# (must_cover); a plain full scan stays on the placement categories.
SHELL_CATEGORIES = ["Walls", "Floors", "Roofs", "Toposolid"]
# An element of these must be in the model as geometry.
_NEEDS_GEOMETRY = set(SHELL_CATEGORIES) | {"Doors", "Windows"}

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


def _norm_bbox(b):
    """A bounding box the checks can use, or None (the bridge says has_bbox false for none)."""
    if not isinstance(b, dict) or b.get("has_bbox") is False or "min" not in b or "max" not in b:
        return None
    return b


def _lookup_ids(ids):
    """Read elements by id, whatever their category (one call). An id a phase wrote that sits
    in no scanned category is looked up here, so the gate can say what it is, or that it is
    not in the model. Returns element dicts; an id that does not exist is simply absent."""
    if not ids:
        return []
    try:
        raw = rc.get_elements_info(sorted(ids))
    except Exception:
        raw = []
    out = []
    for el in raw or []:
        eid = _el_field(el, "id", "element_id", "Id")
        if eid is None:
            continue
        out.append({
            "id": eid,
            "category": _el_field(el, "category", "Category") or "Uncategorised",
            "family": _el_field(el, "family", "family_name", "Family") or "",
            "type": _el_field(el, "type", "type_name", "Type") or "",
            "name": _el_field(el, "name", "Name") or "",
            "bbox": _norm_bbox(el.get("bbox")),
            "looked_up": True,
        })
    return out


def _scan_category(category, only_ids=None, context=None):
    """List a placement category and pull bboxes. Returns element dicts.
    context: a list. When the scan is scoped (only_ids) and something of this category is
    in scope, the REST of the category is appended to it with bboxes, so a new element
    can be compared with what was already there (double placement)."""
    res = rc.call("revit.list_elements_by_category", {"category": category})
    if not res.get("success"):
        return []
    raw = res.get("result")
    if isinstance(raw, dict):
        raw = raw.get("elements", raw.get("result", []))
    if not isinstance(raw, list):
        return []

    out, rest = [], []
    for el in raw:
        eid = _el_field(el, "id", "element_id", "Id")
        if eid is None:
            continue
        fam = _el_field(el, "family", "family_name", "Family")
        typ = _el_field(el, "type", "type_name", "Type")
        name = _el_field(el, "name", "Name", "element_name")
        rec = {
            "id": eid,
            "category": category,
            "family": fam or "",
            "type": typ or "",
            "name": name or "",
            "bbox": None,
        }
        if only_ids is not None and eid not in only_ids:
            rest.append(rec)
        else:
            out.append(rec)
    # the rest of the category matters only when something of it is in scope
    with_rest = out + rest if (context is not None and out) else out
    # ONE bbox call for the whole category (falls back per-element on old DLL)
    boxes = rc.get_bboxes([e["id"] for e in with_rest]) if with_rest else {}
    for e in with_rest:
        e["bbox"] = _norm_bbox(boxes.get(e["id"]))
    if context is not None and out:
        context.extend(rest)
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
    # Counter candidates, in priority order:
    #   a) name-matched counters (any category, any height)
    #   b) thin slabs (0.1–0.8 ft tall) in placement categories — geometry, not
    #      names, because Barnhaus counters are named "Walnut Block", "Quartz", etc.
    name_matched = [e for e in elements if e["category"] in ("Casework", "Furniture",
                                                             "Specialty Equipment",
                                                             "Generic Models")
                    and _COUNTER.search(f"{e['family']} {e['type']} {e['name']}")]
    slab_like = [e for e in elements if e["category"] in ("Casework", "Furniture",
                                                          "Specialty Equipment",
                                                          "Generic Models")
                 and e["bbox"]
                 and 0.1 <= (e["bbox"]["max"]["z"] - e["bbox"]["min"]["z"]) <= 0.8]
    counters = name_matched + [e for e in slab_like if e not in name_matched]

    issues = []
    for s in sinks:
        if not s["bbox"]:
            continue
        best = None   # (overlap_frac, counter) — largest single, for the z-check
        covered = 0.0  # union coverage across ALL overlapping counters
        for c in counters:
            if not c["bbox"]:
                continue
            ov = _xy_overlap(s["bbox"], c["bbox"])
            if ov and ov > 0.05:
                covered += ov
                if best is None or ov > best[0]:
                    best = (ov, c)
        if best is None or covered < 0.5:
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
        sink_top = s["bbox"]["max"]["z"]  # rim, or faucet tip if integrated
        # Seated = counter top cuts through the sink's z-range: bowl below
        # (undermounts hang 6-10in below by design), rim/faucet at-or-above.
        if sink_top < counter_top - 0.2:
            issues.append({
                "type": "sink_sunken",
                "severity": "fix",
                "element_id": s["id"],
                "message": f"Sink {s['id']} is SUNKEN: even its top ({sink_top:.2f}) is "
                           f"{counter_top - sink_top:.2f} ft below counter {c['id']} top "
                           f"({counter_top:.2f}). The whole fixture dropped — likely set off "
                           f"the family bbox top (faucet tip), not the rim. Re-seat.",
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


def _check_duplicates(elements, context=None):
    """Same category + same type + bbox centers within 0.15 ft = double-placed.
    context: elements of the same categories that are NOT in scope (already in the model).
    A pair is reported when at least one of the two is in scope."""
    issues = []
    by_key = {}
    in_scope = {el["id"] for el in elements}
    for el in list(elements) + list(context or []):
        if not el["bbox"]:
            continue
        key = (el["category"], el["family"], el["type"])
        by_key.setdefault(key, []).append(el)
    for (cat, fam, typ), els in by_key.items():
        for i in range(len(els)):
            for j in range(i + 1, len(els)):
                a, b = els[i], els[j]
                if a["id"] not in in_scope and b["id"] not in in_scope:
                    continue
                if b["id"] not in in_scope:
                    a, b = b, a   # name the in-scope one as the one to look at
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


def _check_openings(elements):
    """A door or window that was 'placed' but has no geometry: the bridge can return
    an id for an opening that did not cut its host (an id can be returned for nothing)."""
    issues = []
    for el in elements:
        if el["category"] in SHELL_CATEGORIES:
            bb = el["bbox"]
            flat = 0
            if bb:
                flat = sum(1 for ax in ("x", "y", "z") if abs(bb["max"][ax] - bb["min"][ax]) < 0.01)
            if bb and flat < 2:
                continue
            issues.append({
                "type": "element_without_geometry",
                "severity": "fix",
                "element_id": el["id"],
                "category": el["category"],
                "message": f"{el['category']} element {el['id']} ('{(el['family'] + ' ' + el['type']).strip() or el['name']}') "
                           + ("has no bounding box: it is not in the model as geometry."
                              if not bb else "has a bounding box with no size in two directions: it has no real geometry.")
                           + " Re-create it.",
                "auto_fixable": False,
            })
            continue
        if el["category"] not in ("Doors", "Windows") or el["bbox"]:
            continue
        issues.append({
            "type": "opening_without_geometry",
            "severity": "fix",
            "element_id": el["id"],
            "category": el["category"],
            "message": f"{el['category'][:-1]} {el['id']} ('{(el['family'] + ' ' + el['type']).strip()}') has no "
                       f"bounding box: it is not in the model as geometry. Re-place it.",
            "auto_fixable": False,
        })
    return issues


def _check_coverage(elements, must_cover):
    """A write phase names the ids it created or changed. Each one must have been scanned;
    an id the gate never looked at is a FAIL, not a silent pass."""
    if not must_cover:
        return [], None
    scanned = {e["id"] for e in elements}
    missing = sorted(set(must_cover) - scanned)
    issues = [{
        "type": "not_covered",
        "severity": "fix",
        "element_id": i,
        "message": f"Element {i} was written by this phase but the gate could not look at it: "
                   f"it is in no scanned category and reading it by id returned nothing "
                   f"(it is not in the model, or the read failed).",
        "auto_fixable": False,
    } for i in missing]
    by_cat = {}
    for e in elements:
        if e["id"] in must_cover:
            by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    return issues, {"required": sorted(set(must_cover)), "covered": sorted(set(must_cover) & scanned), "missing": missing,
                    "covered_by_category": by_cat}


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

def run_model_work_qa(element_ids=None, categories=None, must_cover=None):
    """Scan placement categories and run all model-work checks.

    element_ids: optional set/list — scope to these ids (e.g. from the change
                 feed). None = full placement scan.
    must_cover:  optional ids a write phase created or changed. Any of them that
                 was not scanned is a 'fix' finding (gate FAIL).
    Returns report dict; report["fix"] non-empty = gate FAIL.
    """
    cats = list(categories or PLACEMENT_CATEGORIES)
    only = set(element_ids) if element_ids is not None else None
    if categories is None and (only is not None or must_cover):
        # a scoped gate, or a phase that names what it wrote: walls, floors, roofs and site too
        cats += [c for c in SHELL_CATEGORIES if c not in cats]

    print("\n🔎 Model-work QA gate — scanning placement categories...")
    elements = []
    context = [] if only is not None else None   # the rest of a category something in scope belongs to
    for cat in cats:
        els = _scan_category(cat, only_ids=only, context=context)
        print(f"  {cat}: {len(els)} elements")
        elements += els

    # ids a phase wrote that sit in none of the scanned categories: read them by id, so the
    # gate names what they are (a railing, a sheet, a viewport) or reports them as not there
    if must_cover:
        unseen = set(must_cover) - {e["id"] for e in elements}
        if unseen:
            found = _lookup_ids(unseen)
            for e in found:
                print(f"  by id: {e['id']} is in {e['category']}")
            elements += found

    levels = _scan_levels()
    rooms = _scan_rooms()

    all_issues = []
    all_issues += _check_naming_discipline(elements)
    all_issues += _check_sink_seating(elements)
    all_issues += _check_ceiling_boundaries(elements, rooms)
    all_issues += _check_duplicates(elements, context)
    all_issues += _check_floor_mounted(elements, levels)
    all_issues += _check_openings(elements)
    cov_issues, coverage = _check_coverage(elements, must_cover)
    all_issues += cov_issues

    # Dedupe (type + message prefix)
    seen, deduped = set(), []
    for i in all_issues:
        key = (i.get("type"), i.get("message", "")[:80])
        if key not in seen:
            seen.add(key)
            deduped.append(i)

    by_cat = {}
    for e in elements:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    report = {
        "scanned": len(elements),
        "scanned_by_category": by_cat,
        "scanned_ids": sorted(e["id"] for e in elements),
        "categories_scanned": cats,
        "compared_with_existing": len(context or []),
        "must_cover": coverage,
        "total": len(deduped),
        "fix": [i for i in deduped if i["severity"] == "fix"],
        "consider": [i for i in deduped if i["severity"] == "consider"],
        "fyi": [i for i in deduped if i["severity"] == "fyi"],
    }
    _print(report)
    return report


def _print(report):
    print("─" * 50)
    cov = report.get("must_cover")
    looked = report.get("scanned_by_category") or {}
    print("Looked at: " + (", ".join(f"{k} {v}" for k, v in sorted(looked.items())) or "nothing")
          + (f" (compared with {report['compared_with_existing']} element(s) already in those categories)"
             if report.get("compared_with_existing") else ""))
    if cov:
        print(f"Coverage: {len(cov['covered'])} of {len(cov['required'])} element(s) this phase wrote were scanned"
              + (f" — NOT scanned: {cov['missing']}" if cov["missing"] else ""))
    if report["total"] == 0:
        print(f"✅ Model-work QA CLEAN ({report['scanned']} elements scanned)")
        return
    print(f"MODEL-WORK QA — {report['total']} findings "
          f"({report['scanned']} elements scanned)")
    for sev, sym in (("fix", "🔴"), ("consider", "🟡"), ("fyi", "🔵")):
        for i in report[sev]:
            print(f"  {sym} [{i['type']}] {i['message']}")
    print("─" * 50)
