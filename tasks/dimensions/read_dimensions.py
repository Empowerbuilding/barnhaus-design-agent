"""
read_dimensions.py — READ-ONLY inspection of manually placed dimensions.

Reads existing dimension strings from views — never modifies anything.
Supports targeting:
  - all views that have dimensions
  - views whose name matches a keyword (e.g. "dimension")
  - views placed on sheets whose name/number matches (e.g. "Foundation and Columns")

Each dimension reports: id, value string (12' - 6"), raw value, and the
dimension line geometry. What the dimension is ATTACHED to (wall layer,
core vs finish, slab edge) requires the Phase 2 DLL upgrade — flagged as
`references: "phase2"` for now.

Usage:
    python3 run.py read-dims                    # all views with dims
    python3 run.py read-dims dimension          # views/sheets matching "dimension"
    python3 run.py read-dims "foundation"       # Foundation and Columns sheet
"""

import json
from core import revit_client as rc


def _matching_view_ids(keyword: str = None) -> dict:
    """
    Build {view_id: label} for target views.
    Matches view names directly AND views placed on sheets whose
    sheet name/number matches the keyword.
    """
    targets = {}
    kw = (keyword or "").lower()

    views = rc.list_views()
    sheets = rc.list_sheets()

    # Direct view-name match (skip sheets/schedules/3D)
    plan_types = {"FloorPlan", "CeilingPlan", "AreaPlan", "EngineeringPlan",
                  "Section", "Elevation", "Detail", "DraftingView"}
    for v in views:
        if v.get("type") not in plan_types:
            continue
        if not kw or kw in v.get("name", "").lower():
            targets[v["id"]] = f"view: {v['name']}"

    # Sheet-name match → include every view placed on that sheet
    if kw:
        for s in sheets:
            label = f"{s.get('sheet_number','')} {s.get('sheet_name','')}".lower()
            if kw in label:
                info = rc.get_sheet_info(s["id"])
                for vp in info.get("viewports", []):
                    targets[vp["view_id"]] = (f"sheet {s.get('sheet_number')} "
                                              f"({s.get('sheet_name')}) → {vp.get('view_name')}")
    return targets


def run(keyword: str = None, save: bool = True) -> dict:
    """Read dimensions from matching views. Returns report dict."""
    print(f"\n📐 Reading existing dimensions (READ-ONLY){' — filter: ' + keyword if keyword else ''}")

    targets = _matching_view_ids(keyword)
    if not targets:
        print("   No matching views found.")
        return {"views": [], "total_dimensions": 0}

    report = {"filter": keyword, "views": [], "total_dimensions": 0}

    for view_id, label in targets.items():
        dims = rc.list_dimensions(view_id=view_id)
        if not dims:
            continue

        entries = []
        for d in dims:
            entries.append({
                "id":           d.get("id"),
                "value_string": d.get("dim_value_string"),
                "value_ft":     d.get("dim_value"),
                "type":         d.get("type"),
                "line": {
                    "start_x": d.get("start_x"), "start_y": d.get("start_y"),
                    "end_x":   d.get("end_x"),   "end_y":   d.get("end_y"),
                    "length_ft": d.get("length_ft"),
                },
                "references": "phase2",  # attachment detail needs DLL upgrade
            })

        report["views"].append({"view_id": view_id, "label": label,
                                "dimension_count": len(entries), "dimensions": entries})
        report["total_dimensions"] += len(entries)

        print(f"\n   {label} — {len(entries)} dimensions:")
        for e in entries[:30]:
            vs = e["value_string"] or (f"{e['value_ft']:.2f} ft" if e["value_ft"] else "?")
            print(f"     • {vs}  (id {e['id']}, {e['type'] or 'Linear'})")
        if len(entries) > 30:
            print(f"     ... +{len(entries) - 30} more")

    if not report["views"]:
        print("   Matching views found, but none contain dimension elements.")
        print("   (If you KNOW dims exist there, the installed bridge DLL may predate")
        print("    dimension-read support — rebuild via the Revit Bridge Updater.)")

    if save and report["total_dimensions"]:
        with open("dimensions_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n   💾 Saved to dimensions_report.json ({report['total_dimensions']} dims total)")

    return report
