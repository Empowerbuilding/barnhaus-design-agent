"""
sheet_work_qa.py — what a sheet phase wrote, counted from the open model.

Tony 2026-11-11 20:56Z: a phase that writes anything shows coverage of what it wrote, or it
does not pass. For sheet phases the coverage is the sheets and viewports created, counted
before and after (the change feed is not relied on for them).

How a sheet phase uses it:
    python3 run.py qa-model --sheet-snapshot <file>        # BEFORE the phase writes
    python3 run.py qa-model --sheets-since <file> [--must-cover ids] [--expect-sheets N] [--expect-viewports N]

Read-only. Bridge calls: get_document_info, list_sheets, list_elements_by_category (Viewports),
get_viewports_on_sheet for the sheets that are new or whose viewport count changed.
"""

import json
import time

from core import revit_client as rc

# a viewport may sit this far outside the title block outline before it counts as off the sheet
OFF_SHEET_TOL_FT = 0.02


class SheetReadError(Exception):
    """The model's sheets could not be read, or the snapshot is not of the open document."""


def _ok(tool, payload, what):
    r = rc.call(tool, payload)
    if not isinstance(r, dict) or not r.get("success"):
        err = (r or {}).get("error") if isinstance(r, dict) else None
        raise SheetReadError(f"{what} failed: {err or 'no answer from the bridge'}")
    return r.get("result")


def _utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_now():
    """Sheets and viewport ids of the open document, as they are now."""
    info = _ok("revit.get_document_info", {}, "reading the open document")
    title = (info.get("title") if isinstance(info, dict) else None) or ""
    if not str(title).strip():
        raise SheetReadError("the bridge named no open document")
    res = _ok("revit.list_sheets", {}, "listing sheets")
    raw = res.get("sheets") if isinstance(res, dict) else res
    if not isinstance(raw, list):
        raise SheetReadError("listing sheets gave no sheet list")
    sheets = []
    for s in raw:
        sid = s.get("id", s.get("sheet_id"))
        if sid is None:
            continue
        sheets.append({
            "id": int(sid),
            "number": str(s.get("sheet_number") or "").strip(),
            "name": str(s.get("sheet_name") or "").strip(),
            "placeholder": bool(s.get("is_placeholder")),
            "viewport_count": int(s.get("viewport_count") or 0),
        })
    vres = _ok("revit.list_elements_by_category", {"category": "Viewports"}, "listing viewports")
    vraw = vres.get("elements") if isinstance(vres, dict) else vres
    if not isinstance(vraw, list):
        raise SheetReadError("listing viewports gave no list")
    vids = sorted(int(v.get("id", v.get("element_id"))) for v in vraw if v.get("id", v.get("element_id")) is not None)
    return {"document": str(title).strip(), "taken_at": _utc_now(), "sheets": sheets, "viewport_ids": vids}


def take_snapshot(path):
    snap = read_now()
    with open(path, "w") as f:
        json.dump(snap, f, indent=1)
    return snap


def load_snapshot(path):
    try:
        with open(path) as f:
            snap = json.load(f)
    except (OSError, ValueError) as e:
        raise SheetReadError(f"the snapshot {path} could not be read: {e}")
    if not isinstance(snap, dict) or "sheets" not in snap or "viewport_ids" not in snap or not snap.get("document"):
        raise SheetReadError(f"{path} is not a sheet snapshot")
    return snap


def _viewports_of(sheet_id):
    res = _ok("revit.get_viewports_on_sheet", {"sheet_id": sheet_id}, f"reading the viewports of sheet {sheet_id}")
    if not isinstance(res, dict):
        raise SheetReadError(f"reading the viewports of sheet {sheet_id} gave no answer")
    return res


def _off_sheet(vp, block):
    """How far (ft) a viewport outline reaches outside the title block outline; None when unknown."""
    try:
        a0, a1, b0, b1 = vp["outline_min"], vp["outline_max"], block["outline_min"], block["outline_max"]
        return max(b0["x"] - a0["x"], b0["y"] - a0["y"], a1["x"] - b1["x"], a1["y"] - b1["y"], 0.0)
    except (KeyError, TypeError):
        return None


def compare(snapshot, must_cover=None, expect_sheets=None, expect_viewports=None):
    """Compare the open model with a snapshot taken before a sheet phase wrote.
    Returns a report; report["fix"] non-empty = gate FAIL."""
    now = read_now()
    if now["document"] != snapshot["document"]:
        raise SheetReadError(f"the snapshot is of \"{snapshot['document']}\" and the open document is \"{now['document']}\"")

    before_sheets = {s["id"]: s for s in snapshot["sheets"]}
    now_sheets = {s["id"]: s for s in now["sheets"]}
    created_sheets = [now_sheets[i] for i in sorted(set(now_sheets) - set(before_sheets))]
    removed_sheets = [before_sheets[i] for i in sorted(set(before_sheets) - set(now_sheets))]
    before_v, now_v = set(snapshot["viewport_ids"]), set(now["viewport_ids"])
    created_vids = sorted(now_v - before_v)
    removed_vids = sorted(before_v - now_v)

    # where the new viewports are: new sheets and sheets whose count changed first, the rest only if needed
    located, read_sheets = {}, []
    def read_sheet(sid):
        res = _viewports_of(sid)
        read_sheets.append(sid)
        block = res.get("title_block") or {}
        for vp in res.get("viewports") or []:
            vid = vp.get("viewport_id")
            if vid in created_vids and vid not in located:
                located[vid] = {
                    "id": vid, "sheet_id": sid, "sheet_number": res.get("sheet_number") or now_sheets[sid]["number"],
                    "view_id": vp.get("view_id"), "view_name": vp.get("view_name") or "", "scale": vp.get("scale"),
                    "off_sheet_ft": _off_sheet(vp, block),
                }
    if created_vids:
        first = [i for i in now_sheets if i not in before_sheets or now_sheets[i]["viewport_count"] != before_sheets[i]["viewport_count"]]
        for sid in first:
            read_sheet(sid)
        if len(located) < len(created_vids):
            for sid in now_sheets:
                if sid not in read_sheets and now_sheets[sid]["viewport_count"] > 0:
                    read_sheet(sid)
                    if len(located) == len(created_vids):
                        break

    issues = []
    def add(sev, typ, eid, msg):
        issues.append({"type": typ, "severity": sev, "element_id": eid, "message": msg, "auto_fixable": False})

    for s in created_sheets:
        if not s["number"] or not s["name"]:
            add("fix", "sheet_blank_number_or_name", s["id"],
                f"New sheet {s['id']} has {'no number' if not s['number'] else 'no name'} (number \"{s['number']}\", name \"{s['name']}\").")
        if s["viewport_count"] == 0 and not s["placeholder"]:
            add("consider", "sheet_without_viewport", s["id"], f"New sheet {s['number']} \"{s['name']}\" has no view on it.")
    for vid in created_vids:
        vp = located.get(vid)
        if not vp:
            add("fix", "viewport_not_on_a_sheet", vid, f"New viewport {vid} was not found on any sheet.")
            continue
        off = vp["off_sheet_ft"]
        if off is not None and off > OFF_SHEET_TOL_FT:
            add("fix", "viewport_off_sheet", vid,
                f"New viewport {vid} (\"{vp['view_name']}\") on sheet {vp['sheet_number']} reaches {off * 12:.1f} in outside the title block outline.")

    def count_check(what, expected, got):
        if expected is not None and expected != got:
            add("fix", "count_mismatch", None, f"The phase says it created {expected} {what}; the model shows {got} created since the snapshot.")
    count_check("sheet(s)", expect_sheets, len(created_sheets))
    count_check("viewport(s)", expect_viewports, len(created_vids))

    # ids the phase wrote that are sheets or viewports in the model now
    covered = sorted(set(must_cover or ()) & (set(now_sheets) | now_v))
    if not created_sheets and not created_vids and not covered and expect_sheets is None and expect_viewports is None:
        add("fix", "nothing_to_name", None,
            "No sheet and no viewport was created since the snapshot, and the phase named none it changed: "
            "the gate has nothing to show for this phase.")

    return {
        "document": now["document"],
        "snapshot_taken_at": snapshot.get("taken_at"),
        "checked_at": now["taken_at"],
        "sheets_before": len(before_sheets), "sheets_now": len(now_sheets),
        "viewports_before": len(before_v), "viewports_now": len(now_v),
        "created_sheets": created_sheets, "removed_sheets": removed_sheets,
        "created_viewports": [located.get(v) or {"id": v, "sheet_id": None} for v in created_vids],
        "removed_viewport_ids": removed_vids,
        "sheets_read_for_viewports": read_sheets,
        "covered_ids": covered,
        "total": len(issues),
        "fix": [i for i in issues if i["severity"] == "fix"],
        "consider": [i for i in issues if i["severity"] == "consider"],
        "fyi": [i for i in issues if i["severity"] == "fyi"],
    }


def print_snapshot(snap, path):
    with_views = sum(1 for s in snap["sheets"] if s["viewport_count"] > 0)
    print(f"Sheet snapshot of \"{snap['document']}\" at {snap['taken_at']}: {len(snap['sheets'])} sheet(s), "
          f"{len(snap['viewport_ids'])} viewport(s) on {with_views} of them")
    print(f"💾 Snapshot saved to {path}")


def print_report(r):
    print("─" * 50)
    print(f"Sheets of \"{r['document']}\" against the snapshot of {r['snapshot_taken_at']}:")
    cs, rs = r["created_sheets"], r["removed_sheets"]
    print(f"  Sheets: {r['sheets_before']} before, {r['sheets_now']} now. Created {len(cs)}"
          + (": " + ", ".join(f"{s['number']} {s['name']} ({s['id']})" for s in cs) if cs else "")
          + f". Removed {len(rs)}" + (": " + ", ".join(f"{s['number']} ({s['id']})" for s in rs) if rs else "") + ".")
    cv = r["created_viewports"]
    on = sorted({v.get("sheet_number") for v in cv if v.get("sheet_number")})
    print(f"  Viewports: {r['viewports_before']} before, {r['viewports_now']} now. Created {len(cv)}"
          + (f" on sheet(s) {', '.join(on)}" if on else "") + f". Removed {len(r['removed_viewport_ids'])}.")
    for v in cv:
        if v.get("sheet_id") is not None:
            print(f"    viewport {v['id']}: \"{v['view_name']}\" on {v['sheet_number']}")
    print(f"Coverage (sheets): {len(cs)} sheet(s) and {len(cv)} viewport(s) created since the snapshot"
          + (f"; {len(r['covered_ids'])} id(s) this phase wrote are sheets or viewports in the model" if r["covered_ids"] else ""))
    if r["total"] == 0:
        print("✅ Sheet QA CLEAN")
    else:
        for sev, sym in (("fix", "🔴"), ("consider", "🟡"), ("fyi", "🔵")):
            for i in r[sev]:
                print(f"  {sym} [{i['type']}] {i['message']}")
    print("─" * 50)
