"""
snapshots.py — Per-document review snapshots + submission diffing.

Each `review` run saves a compact snapshot of the model + issue set under
snapshots/<doc-slug>/. The next review of the same document diffs against
the previous snapshot: elements added/removed/changed, issues fixed/new.

This is what turns Blueprint from "re-review everything" into
"review only what the drafter changed".
"""

import json
import os
import re
import time

SNAP_DIR = "snapshots"


def doc_slug(state: dict) -> str:
    title = (state.get("document") or {}).get("title") or "unknown"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "unknown"


def _flatten_views(views) -> list:
    out = []
    if isinstance(views, dict):
        for group in views.values():
            out.extend(group or [])
    elif isinstance(views, list):
        out = views
    return out


def _flatten_walls(walls) -> list:
    out = []
    if isinstance(walls, dict):
        for group in walls.values():
            out.extend(group or [])
    elif isinstance(walls, list):
        out = walls
    return out


def build_snapshot(state: dict, issue_keys: list = None) -> dict:
    """Compact, diff-friendly capture of the model + current issue keys."""
    sheets = state.get("sheets") or {}
    if isinstance(sheets, list):
        sheets = {s.get("number", str(s.get("id"))): s for s in sheets}

    return {
        "taken_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "document": (state.get("document") or {}).get("title"),
        "rooms": {str(r["id"]): {"name": r.get("name"), "area_sf": round(r.get("area_sf") or 0, 1),
                                 "level": r.get("level")}
                  for r in (state.get("rooms") or [])},
        "doors": {str(d["id"]): {"type": d.get("type_name"),
                                 "w": d.get("width_in"), "h": d.get("height_in")}
                  for d in (state.get("doors") or [])},
        "windows": {str(w["id"]): {"type": w.get("type_name"),
                                   "w": w.get("width_in"), "h": w.get("height_in")}
                    for w in (state.get("windows") or [])},
        "walls": {str(w["id"]): {"type": w.get("type"), "len": round(w.get("length_ft") or 0, 1)}
                  for w in _flatten_walls(state.get("walls"))},
        "views": {str(v["id"]): v.get("name") for v in _flatten_views(state.get("views"))},
        "sheets": {num: {"name": s.get("name"), "viewports": s.get("viewport_count", 0)}
                   for num, s in sheets.items()},
        "warning_count": len(state.get("warnings") or []),
        "issue_keys": sorted(issue_keys or []),
    }


def save_snapshot(snap: dict, slug: str) -> str:
    d = os.path.join(SNAP_DIR, slug)
    os.makedirs(d, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = os.path.join(d, f"{ts}.json")
    with open(path, "w") as f:
        json.dump(snap, f, indent=1)
    latest = os.path.join(d, "latest.json")
    with open(latest + ".tmp", "w") as f:
        json.dump(snap, f, indent=1)
    os.replace(latest + ".tmp", latest)
    return path


def load_previous(slug: str) -> dict | None:
    path = os.path.join(SNAP_DIR, slug, "latest.json")
    if not os.path.exists(path):
        return None
    try:
        return json.load(open(path))
    except (json.JSONDecodeError, OSError):
        return None


def _diff_ids(prev: dict, curr: dict, label_fn) -> dict:
    added   = [label_fn(i, curr[i]) for i in curr if i not in prev]
    removed = [label_fn(i, prev[i]) for i in prev if i not in curr]
    return {"added": added, "removed": removed}


def diff_snapshots(prev: dict, curr: dict) -> dict:
    """Human-meaningful diff between two snapshots of the same document."""
    d = {"since": prev.get("taken_at"), "changes": [], "elements": {},
         "issues": {"fixed": [], "new": [], "persisting": 0}}

    # Element add/remove per category
    for cat, label_fn in [
        ("rooms",   lambda i, v: f"{v.get('name')} ({i})"),
        ("doors",   lambda i, v: f"{v.get('type')} ({i})"),
        ("windows", lambda i, v: f"{v.get('type')} ({i})"),
        ("walls",   lambda i, v: f"{v.get('type')} {v.get('len')}ft ({i})"),
        ("views",   lambda i, v: f"{v} ({i})"),
    ]:
        res = _diff_ids(prev.get(cat) or {}, curr.get(cat) or {}, label_fn)
        if res["added"] or res["removed"]:
            d["elements"][cat] = res

    # Room renames + area changes
    prev_rooms, curr_rooms = prev.get("rooms") or {}, curr.get("rooms") or {}
    for rid, cr in curr_rooms.items():
        pr = prev_rooms.get(rid)
        if not pr:
            continue
        if pr.get("name") != cr.get("name"):
            d["changes"].append(f"Room {rid} renamed: '{pr.get('name')}' → '{cr.get('name')}'")
        pa, ca = pr.get("area_sf") or 0, cr.get("area_sf") or 0
        if abs(pa - ca) > 1.0:
            d["changes"].append(f"Room '{cr.get('name')}' ({rid}) area: {pa} → {ca} SF")

    # Door/window type swaps
    for cat in ("doors", "windows"):
        pm, cm = prev.get(cat) or {}, curr.get(cat) or {}
        for eid, cv in cm.items():
            pv = pm.get(eid)
            if pv and pv.get("type") != cv.get("type"):
                d["changes"].append(f"{cat[:-1].title()} {eid} type: '{pv.get('type')}' → '{cv.get('type')}'")

    # Sheets
    ps, cs = prev.get("sheets") or {}, curr.get("sheets") or {}
    for num in cs:
        if num not in ps:
            d["changes"].append(f"Sheet {num} added ({cs[num].get('name')})")
        elif ps[num].get("viewports") != cs[num].get("viewports"):
            d["changes"].append(f"Sheet {num} viewports: {ps[num].get('viewports')} → {cs[num].get('viewports')}")
    for num in ps:
        if num not in cs:
            d["changes"].append(f"Sheet {num} removed ({ps[num].get('name')})")

    # Warning count trend
    pw, cw = prev.get("warning_count", 0), curr.get("warning_count", 0)
    if pw != cw:
        d["changes"].append(f"Revit warnings: {pw} → {cw}")

    # Issue diff by key
    pk, ck = set(prev.get("issue_keys") or []), set(curr.get("issue_keys") or [])
    d["issues"]["fixed"] = sorted(pk - ck)
    d["issues"]["new"] = sorted(ck - pk)
    d["issues"]["persisting"] = len(pk & ck)

    d["is_first_review"] = False
    return d


def format_diff(d: dict) -> str:
    lines = [f"Δ Since last review ({d.get('since')}):"]
    fixed, new, persist = d["issues"]["fixed"], d["issues"]["new"], d["issues"]["persisting"]
    lines.append(f"  Issues: {len(fixed)} fixed ✅ · {len(new)} new ❗ · {persist} persisting")
    for cat, res in (d.get("elements") or {}).items():
        if res["added"]:
            lines.append(f"  {cat.title()} added: " + ", ".join(res["added"][:8])
                         + (f" (+{len(res['added'])-8} more)" if len(res["added"]) > 8 else ""))
        if res["removed"]:
            lines.append(f"  {cat.title()} removed: " + ", ".join(res["removed"][:8])
                         + (f" (+{len(res['removed'])-8} more)" if len(res["removed"]) > 8 else ""))
    for c in (d.get("changes") or [])[:20]:
        lines.append(f"  · {c}")
    extra = len(d.get("changes") or []) - 20
    if extra > 0:
        lines.append(f"  · (+{extra} more changes)")
    return "\n".join(lines)
