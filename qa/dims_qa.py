"""
dims_qa.py — Dimension consistency QA using Phase 2 reference data.

Checks every dimension on dimension-bearing views:
  1. MIXED_PLANES     — one string references both finish faces and core faces
                        of walls (inconsistent measuring convention)
  2. LINE_ANCHORED    — dimension attached to detail/model Lines instead of
                        actual model elements (fragile: breaks if line moves,
                        measures nothing real)
  3. UNRESOLVED_REF   — reference could not be resolved to an element
  4. DUPLICATE_DIM    — two dimensions in the same view with identical values
                        and near-identical line geometry (double-dimensioned)

Usage:
    python3 run.py qa-dims [keyword]     # default: views with 'dimension'
                                         # or 'foundation' in name + their sheets
"""

import json
from core import revit_client as rc
from tasks.dimensions.read_dimensions import _matching_view_ids

WALL_FACE_KINDS = {"exterior_finish_face", "interior_finish_face"}
WALL_CORE_KINDS = {"core_face_exterior", "core_face_interior"}


def _check_view(view_id: int, label: str, stats: dict = None) -> list:
    data = rc.list_dimensions_detailed(view_id=view_id)
    if not data.get("available"):
        return [{"check": "dll_stale", "severity": "error",
                 "message": "Bridge DLL predates detailed dimension reads — run the Bridge Updater"}]

    dims = data.get("dimensions", [])
    issues = []
    seen_geom = []
    is_foundation = "foundation" in label.lower()
    if stats is not None:
        stats.setdefault(view_id, {"label": label, "face": 0, "core": 0, "dim_count": len(dims)})

    for d in dims:
        did = d.get("id")
        refs = [r for r in (d.get("references") or []) if isinstance(r, dict)]
        vs = d.get("value_string") or " + ".join(
            (s.get("value_string") or "?") for s in (d.get("segments") or [])) or "?"

        attached = [(r.get("attached_to") or "").lower() for r in refs]
        cats = [(r.get("category") or "") for r in refs]

        # 1. Mixed measuring planes on walls
        has_face = any(a in WALL_FACE_KINDS for a in attached)
        has_core = any(a in WALL_CORE_KINDS for a in attached)
        if has_face and has_core:
            issues.append({"check": "mixed_planes", "severity": "warning", "dim_id": did,
                           "message": f"[{label}] {vs} (id {did}): mixes finish-face and "
                                      f"core-face references in one string"})
        # Track view-level convention for cross-level comparison
        if stats is not None:
            stats[view_id]["face"] += sum(1 for a in attached if a in WALL_FACE_KINDS)
            stats[view_id]["core"] += sum(1 for a in attached if a in WALL_CORE_KINDS)

        # 2. Anchored to Lines instead of model elements
        line_refs = sum(1 for c in cats if c == "Lines")
        if line_refs and line_refs == len(refs):
            sev = "warning"
            note = "measures drafting lines, not the model"
            if is_foundation:
                note = "foundation dims should reference slab edges or columns, not drafting/grid lines"
            issues.append({"check": "line_anchored", "severity": sev, "dim_id": did,
                           "message": f"[{label}] {vs} (id {did}): ALL references are Lines — {note}"})
        elif line_refs:
            issues.append({"check": "line_anchored_partial", "severity": "info", "dim_id": did,
                           "message": f"[{label}] {vs} (id {did}): {line_refs}/{len(refs)} "
                                      f"references are Lines"})

        # 3. Unresolved references
        unresolved = sum(1 for r in refs if r.get("element_id") is None)
        if unresolved:
            issues.append({"check": "unresolved_ref", "severity": "info", "dim_id": did,
                           "message": f"[{label}] {vs} (id {did}): {unresolved} unresolved reference(s)"})

        # 4. Duplicates — same value string + nearly same line
        line = d.get("line") or {}
        s, e = line.get("start") or {}, line.get("end") or {}
        geom_key = (vs, round(s.get("x", 0), 1), round(s.get("y", 0), 1),
                    round(e.get("x", 0), 1), round(e.get("y", 0), 1))
        for prev_id, prev_key in seen_geom:
            if geom_key == prev_key:
                issues.append({"check": "duplicate_dim", "severity": "warning", "dim_id": did,
                               "message": f"[{label}] {vs}: dims {prev_id} and {did} are "
                                          f"identical (double-dimensioned)"})
        seen_geom.append((did, geom_key))

    return issues


def run(keyword: str = None) -> list:
    print(f"\n📐 Dimension Consistency QA{' — filter: ' + keyword if keyword else ''}")

    keywords = [keyword] if keyword else ["dimension", "foundation"]
    targets = {}
    for kw in keywords:
        targets.update(_matching_view_ids(kw))
    if not targets:
        print("   No matching views.")
        return []

    all_issues = []
    stats = {}
    for view_id, label in targets.items():
        issues = _check_view(view_id, label, stats=stats)
        all_issues.extend(issues)

    # 5. CROSS-VIEW CONVENTION — e.g. L1 dims measure finish-face, L2 measures core
    conventions = {}
    for vid, s in stats.items():
        total = s["face"] + s["core"]
        if total < 3:
            continue  # not enough wall refs to establish a convention
        conventions[vid] = {
            "label": s["label"],
            "dominant": "finish_face" if s["face"] >= s["core"] else "core_face",
            "face": s["face"], "core": s["core"],
        }
    dominants = {c["dominant"] for c in conventions.values()}
    if len(dominants) > 1:
        desc = "; ".join(f"{c['label']}: {c['dominant']} ({c['face']}F/{c['core']}C)"
                         for c in conventions.values())
        all_issues.append({"check": "convention_mismatch", "severity": "warning",
                           "message": f"Views use DIFFERENT measuring conventions — {desc}. "
                                      f"Dimension plans should measure to the same wall plane "
                                      f"on every level."})

    warns = [i for i in all_issues if i["severity"] == "warning"]
    infos = [i for i in all_issues if i["severity"] == "info"]
    print(f"\n   {len(warns)} warnings, {len(infos)} info across {len(targets)} views")
    for i in all_issues:
        icon = {"warning": "⚠️ ", "info": "ℹ️ ", "error": "❌"}.get(i["severity"], "•")
        print(f"   {icon} {i['message']}")
    if not all_issues:
        print("   ✅ No dimension consistency issues found")

    with open("dims_qa_report.json", "w") as f:
        json.dump(all_issues, f, indent=2)
    print("   💾 dims_qa_report.json saved")
    return all_issues
