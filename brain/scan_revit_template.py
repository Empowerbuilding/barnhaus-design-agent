"""
scan_revit_template.py
Run this on any fresh Revit template/project to build a full manifest of
everything available: levels, wall types, floor types, roof types, door/window
families and types, and any other loaded families.

Output: revit_template_manifest.json (workspace root)

Usage:
  python3 scan_revit_template.py
  python3 scan_revit_template.py --out my_template.json
"""

import sys, json, argparse
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import _call

OUT_FILE = '/home/mitch/.openclaw/workspace/revit_template_manifest.json'

def query(tool, payload=None):
    r = _call(tool, payload or {})
    if r['Status'] != 'ok':
        print(f"  [WARN] {tool}: {r.get('Message', 'error')}")
        return None
    return r['Result']

print("=" * 60)
print("REVIT TEMPLATE SCANNER")
print("=" * 60)

manifest = {}

# ── Document info ─────────────────────────────────────────────
print("\n── Document ──")
doc = query("revit.get_document_info")
manifest["document"] = doc
if doc:
    print(f"  Title: {doc.get('title')}")
    print(f"  Path:  {doc.get('path')}")
    print(f"  Units: {doc.get('units')}")

# ── Levels ────────────────────────────────────────────────────
print("\n── Levels ──")
levels_r = query("revit.list_levels")
levels = levels_r.get("levels", []) if levels_r else []
manifest["levels"] = levels
for lv in levels:
    print(f"  [{lv['name']}] elevation={lv['elevation']}")

# ── Wall types ────────────────────────────────────────────────
print("\n── Wall Types ──")
wall_els = query("revit.list_elements_by_category", {"category": "Walls", "element_type": "type"})
wall_types = []
if wall_els and "elements" in wall_els:
    for el in wall_els["elements"]:
        wt = {"id": el["id"], "name": el.get("name", ""), "family": el.get("family", "")}
        wall_types.append(wt)
        print(f"  {wt['name']}")
manifest["wall_types"] = wall_types

# ── Floor types ───────────────────────────────────────────────
print("\n── Floor Types ──")
floor_els = query("revit.list_elements_by_category", {"category": "Floors", "element_type": "type"})
floor_types = []
if floor_els and "elements" in floor_els:
    for el in floor_els["elements"]:
        ft = {"id": el["id"], "name": el.get("name", ""), "family": el.get("family", "")}
        floor_types.append(ft)
        print(f"  {ft['name']}")
manifest["floor_types"] = floor_types

# ── Roof types ────────────────────────────────────────────────
print("\n── Roof Types ──")
roof_els = query("revit.list_elements_by_category", {"category": "Roofs", "element_type": "type"})
roof_types = []
if roof_els and "elements" in roof_els:
    for el in roof_els["elements"]:
        rt = {"id": el["id"], "name": el.get("name", ""), "family": el.get("family", "")}
        roof_types.append(rt)
        print(f"  {rt['name']}")
manifest["roof_types"] = roof_types

# ── Door families ─────────────────────────────────────────────
print("\n── Door Families ──")
doors_r = query("revit.list_families", {"category": "Doors"})
door_families = doors_r.get("families", []) if doors_r else []
manifest["door_families"] = door_families
for fam in door_families:
    print(f"  [{fam['name']}]")
    for t in fam.get("types", []):
        print(f"    {t['name']}")

# ── Window families ───────────────────────────────────────────
print("\n── Window Families ──")
wins_r = query("revit.list_families", {"category": "Windows"})
win_families = wins_r.get("families", []) if wins_r else []
manifest["window_families"] = win_families
for fam in win_families:
    print(f"  [{fam['name']}]")
    for t in fam.get("types", []):
        print(f"    {t['name']}")

# ── Stair families ────────────────────────────────────────────
print("\n── Stair Families ──")
stairs_r = query("revit.list_families", {"category": "Stairs"})
stair_families = stairs_r.get("families", []) if stairs_r else []
manifest["stair_families"] = stair_families
for fam in stair_families:
    print(f"  [{fam['name']}]")
    for t in fam.get("types", []):
        print(f"    {t['name']}")

# ── Generic model / specialty families ───────────────────────
print("\n── All Other Loaded Families ──")
for cat in ["Casework", "Furniture", "Plumbing Fixtures", "Lighting Fixtures",
            "Specialty Equipment", "Generic Models", "Structural Columns", "Railings"]:
    r = query("revit.list_families", {"category": cat})
    fams = r.get("families", []) if r else []
    if fams:
        manifest.setdefault("other_families", {})[cat] = fams
        print(f"\n  [{cat}]")
        for fam in fams:
            print(f"    {fam['name']}: {[t['name'] for t in fam.get('types', [])]}")

# ── Views ─────────────────────────────────────────────────────
print("\n── Views ──")
views_r = query("revit.list_views")
views = views_r.get("views", []) if views_r else []
manifest["views"] = views
for v in views:
    print(f"  [{v.get('type','?')}] {v.get('name','?')}")

# ── Warnings ──────────────────────────────────────────────────
print("\n── Active Warnings ──")
warn_r = query("revit.get_warnings")
warnings = warn_r.get("warnings", []) if warn_r else []
manifest["warnings"] = warnings
if warnings:
    for w in warnings[:10]:
        print(f"  ⚠ {w.get('description', w)}")
else:
    print("  None")

# ── Write manifest ─────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--out", default=OUT_FILE)
args, _ = parser.parse_known_args()

with open(args.out, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\n✅ Manifest saved → {args.out}")
print(f"   Levels: {len(levels)} | Wall types: {len(wall_types)} | Floor types: {len(floor_types)}")
print(f"   Door families: {len(door_families)} | Window families: {len(win_families)}")
