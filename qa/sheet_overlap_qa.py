"""
sheet_overlap_qa.py — Sheet-level overlap QA across populated sheets (lesson 965f5d1e).

Checks every populated sheet over the live Revit bridge (read-only) to verify
nothing overlaps on a page:
  1. viewport_overlap_on_sheet — two viewports on the same sheet whose rendered
     bounding boxes (Viewport.GetBoxOutline(), which includes crop + exterior
     dimensions/annotations) intersect by more than OVERLAP_TOL_FT in both X and Y.
     Catches floor-plan overall dimensions running into an Area Map / Area Plan
     inset, stacked elevations bleeding into each other, or colliding details.
  2. viewport_off_sheet — a viewport extending > OFF_SHEET_TOL_FT outside the
     title block outline.

Usage:
    python3 run.py qa-overlaps [sheet_filter]
"""

import json
from core import revit_client as rc

OVERLAP_TOL_FT = 0.015   # ~0.18 in paper tolerance before flagging viewport collision
OFF_SHEET_TOL_FT = 0.02  # ~0.24 in outside title block outline
REPORT_PATH = "sheet_overlap_qa_report.json"


def _box_from_vp(vp: dict):
    try:
        mn, mx = vp["outline_min"], vp["outline_max"]
        x0, y0 = float(mn["x"]), float(mn["y"])
        x1, y1 = float(mx["x"]), float(mx["y"])
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, y0, x1, y1)
    except (KeyError, TypeError, ValueError):
        return None


def check_sheet_viewports(sheet_data: dict) -> list:
    """Pure geometry check on a get_viewports_on_sheet result payload."""
    issues = []
    num = str(sheet_data.get("sheet_number") or "?").strip()
    name = str(sheet_data.get("sheet_name") or "").strip()
    label = f"{num} ({name})" if name else num
    tb = sheet_data.get("title_block") or {}
    tb_box = _box_from_vp(tb) if tb else None
    vps = sheet_data.get("viewports") or []

    parsed = []
    for vp in vps:
        box = _box_from_vp(vp)
        if not box:
            continue
        vid = vp.get("viewport_id")
        vname = str(vp.get("view_name") or f"view {vp.get('view_id')}").strip()
        parsed.append({"id": vid, "view_id": vp.get("view_id"), "name": vname, "box": box})

        if tb_box:
            tx0, ty0, tx1, ty1 = tb_box
            x0, y0, x1, y1 = box
            off = max(tx0 - x0, ty0 - y0, x1 - tx1, y1 - ty1, 0.0)
            if off > OFF_SHEET_TOL_FT:
                issues.append({
                    "check": "viewport_off_sheet",
                    "type": "viewport_off_sheet",
                    "severity": "warning",
                    "sheet": num,
                    "element_id": vid,
                    "message": (f"[{label}] Viewport '{vname}' (id {vid}) extends "
                                f"{off * 12:.2f}\" outside the sheet title block outline."),
                })

    for i in range(len(parsed)):
        a = parsed[i]
        ax0, ay0, ax1, ay1 = a["box"]
        for j in range(i + 1, len(parsed)):
            b = parsed[j]
            bx0, by0, bx1, by1 = b["box"]
            ix = min(ax1, bx1) - max(ax0, bx0)
            iy = min(ay1, by1) - max(ay0, by0)
            if ix > OVERLAP_TOL_FT and iy > OVERLAP_TOL_FT:
                issues.append({
                    "check": "viewport_overlap_on_sheet",
                    "type": "viewport_overlap_on_sheet",
                    "severity": "warning",
                    "sheet": num,
                    "element_id": a["id"],
                    "other_element_id": b["id"],
                    "overlap_in": [round(ix * 12.0, 2), round(iy * 12.0, 2)],
                    "message": (
                        f"[{label}] Page overlap: '{a['name']}' (vp {a['id']}) and "
                        f"'{b['name']}' (vp {b['id']}) overlap by "
                        f"{ix * 12:.2f}\" × {iy * 12:.2f}\" on the sheet "
                        f"(check exterior dimensions/annotations crossing into adjacent view or Area Map)."
                    ),
                })

    return issues


def run_sheet_overlap_qa(sheet_filter: str = None, quiet: bool = False) -> list:
    """Live read-only check across all populated sheets (or filtered substring)."""
    if not quiet:
        print(f"\n📐 Sheet Overlap QA{' — filter: ' + sheet_filter if sheet_filter else ''}")

    r_sh = rc.call("revit.list_sheets", {})
    if not isinstance(r_sh, dict) or not r_sh.get("success"):
        if not quiet:
            print(f"   ⚠️  Could not list sheets: {(r_sh or {}).get('error')}")
        return []

    res = r_sh.get("result")
    raw_sheets = res.get("sheets") if isinstance(res, dict) else (res if isinstance(res, list) else [])
    populated = [s for s in raw_sheets if int(s.get("viewport_count") or 0) > 0]

    if sheet_filter:
        needle = sheet_filter.lower()
        populated = [
            s for s in populated
            if needle in str(s.get("sheet_number") or "").lower()
            or needle in str(s.get("sheet_name") or "").lower()
        ]

    all_issues = []
    for s in populated:
        sid = s.get("id", s.get("sheet_id"))
        if sid is None:
            continue
        rv = rc.call("revit.get_viewports_on_sheet", {"sheet_id": sid})
        if not isinstance(rv, dict) or not rv.get("success") or not isinstance(rv.get("result"), dict):
            continue
        payload = dict(rv["result"])
        payload.setdefault("sheet_number", s.get("sheet_number"))
        payload.setdefault("sheet_name", s.get("sheet_name"))
        all_issues.extend(check_sheet_viewports(payload))

    try:
        with open(REPORT_PATH, "w") as f:
            json.dump({"checked_sheets": len(populated), "total": len(all_issues), "issues": all_issues}, f, indent=2)
    except OSError:
        pass

    if not quiet:
        if all_issues:
            print(f"   ❌ {len(all_issues)} sheet overlap/bounds issue(s) across {len(populated)} populated sheet(s):")
            for iss in all_issues:
                print(f"   ⚠️  {iss['message']}")
        else:
            print(f"   ✅ 0 overlaps across {len(populated)} populated sheet(s)")
        print(f"   💾 {REPORT_PATH} saved")

    return all_issues
