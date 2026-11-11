"""
opening_marks_qa.py — Window & Door Type Mark QA.

Checks that every door/window Type Mark accurately describes the element:
  1. BLANK      — Type Mark is empty
  2. MISMATCH   — mark encodes a size (e.g. 2880 = 2'-8" x 8'-0") that doesn't
                  match the actual Width/Height type parameters
  3. INCONSISTENT — same mark used by types with different actual dimensions

Size-code convention (residential standard):
  4-digit mark WWHH → WW = feet+inches wide, HH = feet+inches tall
  e.g. 2880 → 2'-8" wide x 8'-0" tall;  3050 → 3'-0" x 5'-0"
  Trailing letters ignored (2880R → 2880). Non-dimensional marks
  (D1, W3, etc.) are only checked for blank/consistency.

The check reports on the OPEN document only (flag 54, 2026-11-11). By default the
doors and windows are read live from the open model (no project scan). A cached
scan (project_state.json) is used only on request (--cached) and only when it
names the same document as the one open and is recent; otherwise it is refused
and the open model is read live. A read that fails raises OpenModelReadError:
the caller exits non-zero and never prints a clean result.

Usage:
    from qa.opening_marks_qa import state_for_open_document, run_opening_marks_qa
    state = state_for_open_document()          # live read of the open model
    issues = run_opening_marks_qa(state)
"""

import json
import os
import re
import time

from core import revit_client as rc

STATE_FILE = "project_state.json"
CACHE_MAX_AGE_MIN = 10   # a cached scan older than this is never used
INFO_CHUNK = 400         # ids per get_elements_info call


class OpenModelReadError(Exception):
    """The open model could not be read. Exit non-zero; never print a clean result."""


# ─────────────────────────────────────────────
# READING THE OPEN DOCUMENT
# ─────────────────────────────────────────────

def _ok(tool: str, payload: dict, what: str):
    """One bridge call that must succeed. Returns the result; raises OpenModelReadError."""
    r = rc.call(tool, payload)
    if not isinstance(r, dict) or not r.get("success"):
        err = (r or {}).get("error") if isinstance(r, dict) else None
        raise OpenModelReadError(f"{what} failed: {err or 'no answer from the bridge'}")
    return r.get("result")


def open_document_title() -> str:
    """Title of the document open in Revit, read from the bridge."""
    res = _ok("revit.get_document_info", {}, "reading the open document")
    title = res.get("title") if isinstance(res, dict) else None
    if not title or not str(title).strip():
        raise OpenModelReadError("the bridge named no open document")
    return str(title).strip()


def _list_instances(category: str) -> list:
    res = _ok("revit.list_elements_by_category", {"category": category}, f"listing {category}")
    if isinstance(res, dict):
        els = res.get("elements") or []
    elif isinstance(res, list):
        els = res
    else:
        raise OpenModelReadError(f"listing {category} gave no element list")
    out = []
    for e in els:
        if not isinstance(e, dict) or e.get("id") is None:
            raise OpenModelReadError(f"listing {category} gave an element with no id")
        out.append(e)
    return out


def _type_fields(element_id: int) -> dict:
    """Family, type, Type Mark, Width and Height of the element's type (feet)."""
    res = _ok("revit.get_type_parameters", {"element_id": element_id},
              f"reading the type of element {element_id}")
    params = res.get("parameters") if isinstance(res, dict) else None
    if not isinstance(params, list):
        raise OpenModelReadError(f"reading the type of element {element_id} gave no parameters")
    out = {"family_name": None, "type_name": None, "type_mark": None,
           "width_ft": 0.0, "height_ft": 0.0}
    for p in params:
        name, value = p.get("name", ""), p.get("value")
        if name == "Family Name" and value:
            out["family_name"] = value
        elif name == "Type Name" and value:
            out["type_name"] = value
        elif name == "Type Mark":
            out["type_mark"] = value or ""
        elif name in ("Width", "Height"):
            try:
                out["width_ft" if name == "Width" else "height_ft"] = round(float(value), 3)
            except (TypeError, ValueError):
                pass
    return out


def _info_param(item: dict, name: str):
    v = (item.get("params") or {}).get(name)
    if isinstance(v, dict):
        v = v.get("display") if v.get("display") is not None else v.get("value")
    return None if v is None else str(v)


def read_openings_live() -> dict:
    """
    Read the doors and windows of the OPEN model, with the fields the marks check
    needs (family, type, Type Mark, type Width and Height). No project scan, no
    write. Per category: one list call, one bulk info call per 400 instances, one
    type read per distinct type. Raises OpenModelReadError when any read fails or
    the open document changes during the read.
    """
    calls = {"n": 0}

    def counted(fn, *a):
        calls["n"] += 1
        return fn(*a)

    title = counted(open_document_title)
    state = {"document": {"title": title},
             "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "doors": [], "windows": []}

    for category, key in (("Doors", "doors"), ("Windows", "windows")):
        listed = counted(_list_instances, category)
        ids = [int(e["id"]) for e in listed]

        # Bulk read of type id + Type Mark. An old DLL without the command: every
        # instance is read on its own below (slower, same fields).
        info = {}
        for i in range(0, len(ids), INFO_CHUNK):
            calls["n"] += 1
            r = rc.call("revit.get_elements_info", {
                "element_ids": ids[i:i + INFO_CHUNK], "parameters": ["Type Mark"],
                "include_bbox": False, "include_location": False})
            if not isinstance(r, dict) or not r.get("success"):
                info = {}
                break
            for it in ((r.get("result") or {}).get("elements") or []):
                if isinstance(it, dict) and it.get("id") is not None:
                    info[int(it["id"])] = it

        by_type = {}
        for e in listed:
            eid = int(e["id"])
            it = info.get(eid) or {}
            tkey = it.get("type_id")
            if tkey is None:
                tkey = ("instance", eid)          # type not known: read this instance itself
            if tkey not in by_type:
                by_type[tkey] = counted(_type_fields, eid)
            tf = by_type[tkey]
            mark = tf["type_mark"]
            if mark is None:                      # the type read carried no Type Mark row
                mark = _info_param(it, "Type Mark") or ""
            state[key].append({
                "id":          eid,
                "family_name": tf["family_name"] or it.get("family") or e.get("name", ""),
                "type_name":   tf["type_name"] or it.get("type") or e.get("type", ""),
                "type_mark":   mark,
                "width_ft":    tf["width_ft"],
                "height_ft":   tf["height_ft"],
                "width_in":    round(tf["width_ft"] * 12, 1),
                "height_in":   round(tf["height_ft"] * 12, 1),
            })

    after = counted(open_document_title)
    if after != title:
        raise OpenModelReadError(
            f'the open document changed during the read ("{title}" then "{after}")')
    state["source"] = {"kind": "live", "bridge_calls": calls["n"]}
    return state


def cached_state_for(title: str, max_age_min: float = CACHE_MAX_AGE_MIN,
                     path: str = STATE_FILE, now: float = None):
    """
    The cached scan, only when it is a scan of the document named by `title` and
    was taken in the last max_age_min minutes. Returns (state, None) or
    (None, reason it was refused).
    """
    if not os.path.exists(path):
        return None, f"no {path} in this folder"
    try:
        with open(path) as f:
            state = json.load(f)
    except (OSError, ValueError) as e:
        return None, f"{path} could not be read ({e})"
    if not isinstance(state, dict):
        return None, f"{path} is not a scan"
    cached_title = str((state.get("document") or {}).get("title") or "").strip()
    if not cached_title:
        return None, f"{path} does not name its document"
    if cached_title != title:
        return None, f'{path} is a scan of another document ("{cached_title}")'
    stamp = state.get("scanned_at") or ""
    try:
        scanned = time.mktime(time.strptime(str(stamp)[:19], "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None, f"{path} has no readable scan time"
    age_min = ((time.time() if now is None else now) - scanned) / 60.0
    if age_min < -1 or age_min > max_age_min:
        return None, (f"{path} was scanned {stamp} ({age_min:.0f} min ago; "
                      f"the limit is {max_age_min:g} min)")
    openings = (state.get("doors") or []) + (state.get("windows") or [])
    if any("type_mark" not in o for o in openings):
        return None, f"{path} was scanned before type marks were captured"
    state["source"] = {"kind": "cache", "path": path, "scanned_at": stamp,
                       "age_min": round(max(age_min, 0.0), 1)}
    return state, None


def state_for_open_document(use_cache: bool = False,
                            max_age_min: float = CACHE_MAX_AGE_MIN) -> dict:
    """
    Doors and windows of the OPEN document, for run_opening_marks_qa.
    Default: live read. use_cache: the cached scan when it is the same document
    and recent; refused (with the reason printed) and read live otherwise.
    Raises OpenModelReadError when the open model cannot be read.
    """
    if use_cache:
        title = open_document_title()
        state, why = cached_state_for(title, max_age_min)
        if state is not None:
            return state
        print(f"   Cached scan NOT used: {why}. Reading the open model live.")
    return read_openings_live()


# ─────────────────────────────────────────────
# THE CHECK
# ─────────────────────────────────────────────

TOLERANCE_IN = 1.0  # allow 1" slop between mark code and actual dims


def parse_size_code(mark: str):
    """
    Parse a size-coded type mark → (width_in, height_in) or None.
    '2880' → (32.0, 96.0). '3050' → (36.0, 60.0). '2880R' → (32.0, 96.0).
    """
    if not mark:
        return None
    m = re.match(r"^(\d{4})[A-Za-z]*$", mark.strip())
    if not m:
        return None
    code = m.group(1)
    w_ft, w_in = int(code[0]), int(code[1])
    h_ft, h_in = int(code[2]), int(code[3])
    # Sanity: inches digit must be 0-9 (always true), feet 0-9
    return (w_ft * 12 + w_in, h_ft * 12 + h_in)


def _check_elements(elements: list, kind: str) -> list:
    issues = []
    marks_seen = {}  # mark -> (width_in, height_in, type_name)

    for e in elements:
        mark   = (e.get("type_mark") or "").strip()
        w_in   = e.get("width_in", 0)
        h_in   = e.get("height_in", 0)
        label  = f"{kind} {e.get('id')} ({e.get('family_name','')} {e.get('type_name','')})"

        if not mark:
            issues.append({
                "check":   "type_mark_blank",
                "severity": "warning",
                "element_id": e.get("id"),
                "kind":    kind,
                "message": f"{label}: Type Mark is BLANK",
            })
            continue

        # Size-coded mark → compare against actual dims
        expected = parse_size_code(mark)
        if expected and w_in and h_in:
            exp_w, exp_h = expected
            if abs(exp_w - w_in) > TOLERANCE_IN or abs(exp_h - h_in) > TOLERANCE_IN:
                issues.append({
                    "check":   "type_mark_mismatch",
                    "severity": "error",
                    "element_id": e.get("id"),
                    "kind":    kind,
                    "message": (f"{label}: mark '{mark}' says {exp_w:.0f}\"x{exp_h:.0f}\" "
                                f"but actual is {w_in:.0f}\"x{h_in:.0f}\""),
                })

        # Consistency: same mark must always mean the same size
        key = mark
        if key in marks_seen:
            pw, ph, ptype = marks_seen[key]
            if (w_in and ph and (abs(pw - w_in) > TOLERANCE_IN or abs(ph - h_in) > TOLERANCE_IN)):
                issues.append({
                    "check":   "type_mark_inconsistent",
                    "severity": "error",
                    "element_id": e.get("id"),
                    "kind":    kind,
                    "message": (f"{label}: mark '{mark}' is {w_in:.0f}\"x{h_in:.0f}\" here but "
                                f"{pw:.0f}\"x{ph:.0f}\" on type '{ptype}' — same mark, different size"),
                })
        else:
            marks_seen[key] = (w_in, h_in, e.get("type_name", ""))

    return issues


def _marks_line(kind: str, elements: list, limit: int = 40) -> str:
    """One line: the type marks read on these instances, with instance counts."""
    counts = {}
    for e in elements:
        mark = (e.get("type_mark") or "").strip() or "(blank)"
        counts[mark] = counts.get(mark, 0) + 1
    if not counts:
        return f"   {kind} type marks read: none (0 instances)"
    parts = [f"{m} x{n}" for m, n in sorted(counts.items())]
    more = len(parts) - limit
    return (f"   {kind} type marks read: " + ", ".join(parts[:limit])
            + (f", and {more} more" if more > 0 else ""))


def run_opening_marks_qa(state: dict) -> list:
    """
    Run type-mark QA on the doors + windows in `state` (from state_for_open_document).
    Prints the document checked, where the data came from, and how many door and
    window instances were looked at. Returns the issue list. Zero instances is
    reported as NOTHING CHECKED, never as a clean result.
    """
    doors   = state.get("doors", [])
    windows = state.get("windows", [])
    title   = (state.get("document") or {}).get("title") or "unknown (the state names no document)"
    source  = state.get("source") or {}

    print("\n🏷️  Opening Type Mark QA")
    print(f'   Document checked: "{title}"')
    if source.get("kind") == "live":
        print(f"   Source: live read of the open model ({source.get('bridge_calls')} bridge call(s))")
    elif source.get("kind") == "cache":
        print(f"   Source: CACHED scan {source.get('path')} of the same document, "
              f"scanned {source.get('scanned_at')} ({source.get('age_min')} min ago). "
              "Changes made since then are not in it.")
    else:
        print("   Source: a state passed in by the caller (not verified against the open model)")
    print(f"   Looked at: {len(doors)} door instance(s), {len(windows)} window instance(s)")

    if any("type_mark" not in o for o in doors + windows):
        print("   ⚠️  State was scanned before type_mark support — run a fresh scan first.")
        return [{"check": "stale_state", "severity": "error",
                 "message": "project_state.json predates type_mark capture. Re-run: python3 run.py scan"}]

    if not doors and not windows:
        print("   NOTHING CHECKED: the document has no door or window instances. "
              "This is not a clean result.")
        return []

    no_size = sum(1 for o in doors + windows if not (o.get("width_in") and o.get("height_in")))
    if no_size:
        print(f"   Size not readable on {no_size} instance(s) (no Width / Height on the type): "
              "their marks are checked for blank and same-mark use only.")

    print(_marks_line("Door", doors))
    print(_marks_line("Window", windows))

    issues = _check_elements(doors, "Door") + _check_elements(windows, "Window")

    errors   = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    print(f"   {len(errors)} errors, {len(warnings)} warnings")
    for i in issues:
        icon = "❌" if i["severity"] == "error" else "⚠️ "
        print(f"   {icon} {i['message']}")
    if not issues:
        print(f"   ✅ Type marks check out on the {len(doors)} door and {len(windows)} window "
              f'instance(s) of "{title}"')
    return issues
