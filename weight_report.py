"""
weight_report.py — Model weight report (ROADMAP Priority 5).

550MB files stall portal uploads. This ranks the likely file-size drivers so
the strip-to-2D effort is targeted instead of guesswork:

    - instance counts by family/type per model category
    - imported CAD (ImportInstance) detection
    - loaded-but-unused family candidates
    - top-20 hit list weighted toward heavy categories

Wired to `python3 run.py weight`.

LIMITS (bridge DLL, as of 2026-08): the bridge has no per-element/per-family
byte-size query, no geometry-complexity metric, and no purge-unused listing.
Where data isn't available we degrade gracefully and say exactly which DLL
support is missing rather than fabricating numbers.

⚠️ UNTESTED AGAINST LIVE BRIDGE — see DEV_NOTES.md on this branch.
"""

from collections import Counter
from core import revit_client as rc

# Categories scanned for instance counts. Weight = heuristic file-size cost
# per instance (heavy 3D content families cost far more than walls/floors).
MODEL_CATEGORIES = [
    # (category string for list_elements_by_category, weight)
    ("Walls",                 1),
    ("Floors",                1),
    ("Roofs",                 1),
    ("Ceilings",              1),
    ("Doors",                 2),
    ("Windows",               2),
    ("Stairs",                2),
    ("Railings",              2),
    ("Structural Framing",    1),
    ("Structural Columns",    1),
    ("Structural Foundations", 1),
    ("Casework",              3),
    ("Furniture",             3),
    ("Plumbing Fixtures",     3),
    ("Lighting Fixtures",     3),
    ("Electrical Fixtures",   2),
    ("Mechanical Equipment",  3),
    ("Specialty Equipment",   3),
    ("Generic Models",        3),
    ("Planting",              5),
    ("Entourage",             5),
    ("Site",                  2),
    ("Mass",                  3),
]

# Category name candidates for imported CAD — the bridge category mapping for
# ImportInstance is unverified; we try each until one returns elements.
IMPORT_CATEGORY_CANDIDATES = ["Imports", "Import Instances", "ImportInstance",
                              "Imports in Families", "DWG"]

HEAVY_WEIGHT_THRESHOLD = 3   # weight ≥ this ⇒ "heavy category" flag
HIGH_INSTANCE_COUNT    = 25  # instances per family/type ⇒ "high count" flag


def _family_type_key(e: dict) -> str:
    fam = e.get("family") or e.get("family_name") or ""
    typ = e.get("type") or e.get("type_name") or e.get("name") or "?"
    return f"{fam} : {typ}" if fam and fam != typ else str(typ)


def run_weight() -> dict:
    print("\n🏋️  Model weight report\n")

    # ── Per-category family/type counts ─────────────────────────────────
    rows = []          # (score, count, category, family_type, flags)
    category_totals = []
    for category, weight in MODEL_CATEGORIES:
        elements = rc.list_elements_by_category(category)
        if not elements:
            continue
        category_totals.append((category, len(elements), weight))
        by_type = Counter(_family_type_key(e) for e in elements)
        for ft, count in by_type.items():
            flags = []
            if weight >= HEAVY_WEIGHT_THRESHOLD:
                flags.append("heavy-category")
            if count >= HIGH_INSTANCE_COUNT:
                flags.append("high-instance-count")
            rows.append((count * weight, count, category, ft, flags))

    if not category_totals:
        print("❌ No elements returned for any category — is a model open?")
        return {"hit_list": [], "imports": [], "unused_family_candidates": []}

    print("── Instances by category ──")
    for category, total, weight in sorted(category_totals, key=lambda t: -t[1]):
        heavy = "  🔥 heavy" if weight >= HEAVY_WEIGHT_THRESHOLD else ""
        print(f"  {total:>5}  {category}{heavy}")

    # ── Imported CAD ─────────────────────────────────────────────────────
    print("\n── Imported CAD (ImportInstance) ──")
    imports = []
    import_category_found = None
    for cand in IMPORT_CATEGORY_CANDIDATES:
        elements = rc.list_elements_by_category(cand)
        if elements:
            import_category_found = cand
            imports = elements
            break
    if imports:
        print(f"  ⚠️  {len(imports)} imported CAD instances (category '{import_category_found}') "
              f"— imports are the #1 file-bloat suspect:")
        for e in imports[:20]:
            print(f"     id {e.get('id')} — {e.get('name') or e.get('type') or '?'}")
    else:
        print("  none found via bridge. NOTE: list_elements_by_category may not map "
              "ImportInstance — verifying imports needs a dedicated DLL command "
              "(revit.list_imports) if this model is known to contain linked/imported DWGs.")

    # ── Loaded-but-unused family candidates ──────────────────────────────
    print("\n── Loaded-but-unused family candidates ──")
    unused = []
    fam_res = rc.call("revit.list_families", {})
    if fam_res.get("success"):
        loaded = [f.get("name", "") for f in
                  fam_res.get("result", {}).get("families", [])]
        # Names seen on any scanned instance (family or type field)
        seen_text = " | ".join(r[3] for r in rows).lower()
        unused = [name for name in loaded
                  if name and name.lower() not in seen_text]
        if unused:
            print(f"  {len(unused)} loaded families with no instances in scanned "
                  f"categories (purge candidates — verify in Revit before purging):")
            for name in unused[:25]:
                print(f"     • {name}")
            if len(unused) > 25:
                print(f"     … +{len(unused) - 25} more")
        else:
            print("  none — every loaded family has at least one scanned instance.")
        print("  NOTE: approximation only. Families used solely in schedules, "
              "legends, or unscanned categories will appear here. A true "
              "purge-unused list needs DLL support (Document.GetUnusedElements).")
    else:
        print(f"  ⚠️  list_families failed: {fam_res.get('error')}")

    # ── Top-20 hit list ──────────────────────────────────────────────────
    rows.sort(key=lambda r: -r[0])
    hit_list = rows[:20]
    print("\n── Top-20 hit list (weighted: count × category heaviness) ──")
    for i, (score, count, category, ft, flags) in enumerate(hit_list, 1):
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        print(f"  {i:>2}. {count:>4}× {ft}  ({category}){flag_str}")

    print("\n── Missing DLL support (data this report can NOT see) ──")
    print("  • per-family / per-element byte size — needs revit.get_family_sizes "
          "(export each family doc and stat it, or EstimatedSize workarounds)")
    print("  • geometry complexity (face/vertex counts) — needs a geometry-stats command")
    print("  • true purge-unused listing — needs Document.GetUnusedElements exposure")
    print("  • linked RVT/DWG file sizes — needs revit.list_links with path+size")
    print("\nUntil those land, treat the hit list as ranked suspicion: imports first, "
          "then heavy-category families with high instance counts.\n")

    return {
        "category_totals": category_totals,
        "hit_list": [{"count": c, "category": cat, "family_type": ft,
                      "flags": fl, "score": s}
                     for (s, c, cat, ft, fl) in hit_list],
        "imports": imports,
        "unused_family_candidates": unused,
    }
