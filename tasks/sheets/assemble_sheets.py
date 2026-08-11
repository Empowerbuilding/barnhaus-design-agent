"""
assemble_sheets.py — Automated view-to-sheet assembly.

Matches existing unplaced views to existing EMPTY sheets by name — mimicking
the manual drag-a-view-onto-a-sheet workflow — then places them.

Safety model:
  - Only ever fills EMPTY sheets (viewport_count == 0)
  - Never moves/removes existing viewports
  - A view already placed on any sheet is never reused (Revit forbids it anyway)
  - Requires an unambiguous best match; ties are reported, not guessed
  - DRY-RUN by default — prints the plan. Pass --apply to actually place.

Usage:
    python3 run.py assemble-sheets           # dry run (report only)
    python3 run.py assemble-sheets --apply   # place viewports
"""

import re
from core import revit_client as rc

# Words that carry no matching signal
_STOPWORDS = {"plan", "plans", "sheet", "the", "and", "of", "-", "&"}

# Normalizations: map variants to one token
_SYNONYMS = {
    "l1": "level1", "l2": "level2", "l3": "level3",
    "level 1": "level1", "level 2": "level2", "level 3": "level3",
    "1st": "level1", "2nd": "level2", "first": "level1", "second": "level2",
    "elevations": "elevation", "columns": "column", "foundations": "foundation",
    "elec": "electrical", "plumb": "plumbing", "dim": "dimension",
    "dimensions": "dimension", "rcp": "ceiling",
}

# View types eligible for auto-placement
_PLACEABLE_TYPES = {"FloorPlan", "CeilingPlan", "AreaPlan", "EngineeringPlan",
                    "Elevation", "Section", "ThreeD", "Schedule",
                    "Detail", "DraftingView", "Legend"}


def _tokens(text: str) -> set:
    t = text.lower()
    # normalize "level 1" style before splitting
    for k, v in _SYNONYMS.items():
        if " " in k:
            t = t.replace(k, v)
    parts = re.split(r"[\s_\-./()]+", t)
    out = set()
    for p in parts:
        if not p or p in _STOPWORDS:
            continue
        out.add(_SYNONYMS.get(p, p))
    return out


def _score(sheet_tokens: set, view_tokens: set) -> int:
    return len(sheet_tokens & view_tokens)


def build_plan() -> dict:
    """Compute the assembly plan without touching the model."""
    sheets = rc.list_sheets()
    views  = rc.list_views()

    empty_sheets = [s for s in sheets if s.get("viewport_count", 0) == 0
                    and not s.get("is_placeholder")]

    # Views already used on any sheet
    used_view_ids = set()
    for s in sheets:
        if s.get("viewport_count", 0) > 0:
            info = rc.get_sheet_info(s["id"])
            used_view_ids.update(vp["view_id"] for vp in info.get("viewports", []))

    candidates = [v for v in views
                  if v.get("type") in _PLACEABLE_TYPES and v["id"] not in used_view_ids]

    plan = {"place": [], "ambiguous": [], "no_match": []}

    claimed = set()  # view ids claimed by earlier sheets in this run
    for sheet in empty_sheets:
        st = _tokens(f"{sheet.get('sheet_number','')} {sheet.get('sheet_name','')}")
        scored = []
        for v in candidates:
            if v["id"] in claimed:
                continue
            sc = _score(st, _tokens(v.get("name", "")))
            if sc >= 2:  # need at least 2 shared meaningful tokens
                scored.append((sc, v))
        scored.sort(key=lambda x: -x[0])

        if not scored:
            plan["no_match"].append({"sheet": sheet})
        elif len(scored) > 1 and scored[0][0] == scored[1][0]:
            plan["ambiguous"].append({
                "sheet": sheet,
                "candidates": [{"id": v["id"], "name": v["name"], "score": sc}
                               for sc, v in scored[:4]],
            })
        else:
            sc, v = scored[0]
            claimed.add(v["id"])
            plan["place"].append({"sheet": sheet, "view": v, "score": sc})

    return plan


def run(apply: bool = False) -> dict:
    print(f"\n📑 View-to-Sheet Assembly {'(APPLY)' if apply else '(DRY RUN — pass --apply to place)'}")
    plan = build_plan()

    if plan["place"]:
        print(f"\n   Will place {len(plan['place'])} views:")
        for p in plan["place"]:
            s, v = p["sheet"], p["view"]
            print(f"     ✅ {s['sheet_number']} \"{s['sheet_name']}\"  ←  "
                  f"{v['name']} ({v['type']}, score {p['score']})")
    if plan["ambiguous"]:
        print(f"\n   ⚠️  {len(plan['ambiguous'])} sheets have TIED candidates (skipped — resolve manually):")
        for a in plan["ambiguous"]:
            s = a["sheet"]
            opts = ", ".join(f"{c['name']}({c['score']})" for c in a["candidates"])
            print(f"     ⚠️  {s['sheet_number']} \"{s['sheet_name']}\" — {opts}")
    if plan["no_match"]:
        nums = ", ".join(n["sheet"]["sheet_number"] for n in plan["no_match"])
        print(f"\n   ℹ️  No matching view found for: {nums}")

    if not apply:
        print("\n   Dry run complete — nothing placed.")
        return plan

    placed, failed = 0, 0
    for p in plan["place"]:
        s, v = p["sheet"], p["view"]
        res = rc.place_view_on_sheet(s["id"], v["id"], x=1.4, y=1.0)
        if res.get("success"):
            placed += 1
            print(f"   ✅ Placed {v['name']} → {s['sheet_number']}")
        else:
            failed += 1
            print(f"   ❌ FAILED {v['name']} → {s['sheet_number']}: {res.get('error')}")

    print(f"\n   Done — {placed} placed, {failed} failed.")
    return plan
