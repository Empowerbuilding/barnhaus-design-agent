"""
standards_runner.py — Data-driven standards checks (ROADMAP Priority 4).

Loads standards.yaml and executes each section against the open model via
bridge queries. One ✅ PASS / ❌ FAIL line per rule; sections still carrying
"TODO" placeholders are ⏭️ SKIPPED (Michael hasn't authored them yet).

Sections:
    sheet_order    — sheets must appear in the canonical relative order
    sheet_naming   — every sheet number matches an allowed regex
    required_views — each keyword must match an existing view name
    titleblock     — every placed titleblock is the standard family

Wired to `python3 run.py standards` and `python3 run.py gate`.

⚠️ UNTESTED AGAINST LIVE BRIDGE — see DEV_NOTES.md on this branch. Known
dependency: list_sheets returns no number/name (bridge gotcha) — we read
"Sheet Number"/"Sheet Name" per sheet via get_parameter_value.
"""

import os
import re
from core import revit_client as rc

STANDARDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "standards.yaml")


# ─────────────────────────────────────────────
# YAML LOADING (PyYAML if present, mini-parser fallback)
# ─────────────────────────────────────────────

def load_standards(path: str = STANDARDS_FILE) -> dict:
    with open(path) as f:
        text = f.read()
    try:
        import yaml  # PyYAML may not be installed in Blueprint's container
        return yaml.safe_load(text) or {}
    except ImportError:
        return _mini_yaml(text)


def _mini_yaml(text: str) -> dict:
    """
    Fallback parser for the SUBSET of YAML standards.yaml uses:
    top-level keys, one nesting level, string lists, scalar strings, comments.
    Not a general YAML parser — install PyYAML for anything fancier.
    """
    root = {}
    pending_key = None   # top-level key whose container type isn't known yet
    current = None       # active container (list or dict) receiving lines

    def _scalar(v):
        v = v.strip()
        if v[:1] in ('"', "'"):
            q = v[0]
            i = 1
            while i < len(v):
                if q == '"' and v[i] == "\\":
                    i += 2
                    continue
                if v[i] == q:
                    break
                i += 1
            inner = v[1:i]
            if q == '"':  # unescape double-quoted YAML: \\ → \, \" → "
                inner = (inner.replace("\\\\", "\x00")
                              .replace('\\"', '"')
                              .replace("\x00", "\\"))
            return inner
        if "#" in v:
            v = v.split("#", 1)[0].strip()
        return v

    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        if line.startswith("- "):
            if pending_key is not None:      # container turns out to be a list
                root[pending_key] = []
                current = root[pending_key]
                pending_key = None
            if isinstance(current, list):
                current.append(_scalar(line[2:]))
            continue

        if ":" in line:
            key, _, rest = line.partition(":")
            key, rest = key.strip(), rest.strip()
            if indent == 0:
                if pending_key is not None:  # previous container stayed empty
                    root[pending_key] = []
                pending_key, current = None, None
                if rest:
                    root[key] = _scalar(rest)
                else:
                    pending_key = key
            else:
                if pending_key is not None:  # container turns out to be a dict
                    root[pending_key] = {}
                    current = root[pending_key]
                    pending_key = None
                if isinstance(current, dict):
                    if rest:
                        current[key] = _scalar(rest)
                    else:
                        current[key] = []
                        current = current[key]

    if pending_key is not None:
        root[pending_key] = []
    return root


def _has_todo(value) -> bool:
    """Section still carries authoring placeholders → skip, don't enforce."""
    if isinstance(value, str):
        return "todo" in value.lower()
    if isinstance(value, list):
        return any(_has_todo(v) for v in value)
    if isinstance(value, dict):
        return any(_has_todo(v) for v in value.values())
    return False


# ─────────────────────────────────────────────
# MODEL READS
# ─────────────────────────────────────────────

def _fetch_sheets() -> list:
    """
    Sheets with real number/name. Bridge gotcha: list_sheets returns no
    number/name — read "Sheet Number"/"Sheet Name" per sheet.
    """
    sheets = []
    for s in rc.list_sheets():
        sid = s.get("id")
        number = s.get("number") or rc.get_parameter_value(sid, "Sheet Number") or ""
        name = s.get("name") or rc.get_parameter_value(sid, "Sheet Name") or ""
        sheets.append({"id": sid, "number": str(number), "name": str(name)})
    # Revit sorts sheets by number for the browser — mirror that for order checks
    sheets.sort(key=lambda s: s["number"])
    return sheets


# ─────────────────────────────────────────────
# RULES
# ─────────────────────────────────────────────

def _check_sheet_order(order: list, sheets: list, lines: list) -> int:
    """Sheets present must follow the canonical relative order. Returns fails."""
    def _rank(number):
        # longest matching prefix wins (A101.2 → "A101" unless "A101.2" listed)
        best = -1
        for i, prefix in enumerate(order):
            if number.startswith(prefix) and (best < 0 or len(prefix) > len(order[best])):
                best = i
        return best

    ranked = [(s, _rank(s["number"])) for s in sheets if _rank(s["number"]) >= 0]
    unknown = [s["number"] for s in sheets if _rank(s["number"]) < 0]
    fails = 0

    last_rank, last_number = -1, ""
    out_of_order = []
    for s, r in ranked:
        if r < last_rank:
            out_of_order.append(f"{s['number']} after {last_number}")
        last_rank, last_number = max(last_rank, r), s["number"]

    if out_of_order:
        fails += 1
        lines.append(f"❌ FAIL  sheet_order — out of sequence: {'; '.join(out_of_order)}")
    else:
        lines.append(f"✅ PASS  sheet_order — {len(ranked)} sheets follow the canonical order")
    if unknown:
        lines.append(f"🖐️ NOTE  sheet_order — {len(unknown)} sheets not in the canonical "
                     f"list (add to standards.yaml or renumber): {', '.join(unknown[:10])}")
    return fails


def _check_sheet_naming(patterns: list, sheets: list, lines: list) -> int:
    compiled = [re.compile(p) for p in patterns]
    bad = [s for s in sheets
           if not any(rx.match(s["number"]) for rx in compiled)]
    if bad:
        lines.append(f"❌ FAIL  sheet_naming — {len(bad)} sheet numbers break the "
                     f"pattern: {', '.join(s['number'] or '(blank)' for s in bad[:10])}")
        return 1
    lines.append(f"✅ PASS  sheet_naming — all {len(sheets)} sheet numbers match")
    return 0


def _check_required_views(keywords: list, lines: list) -> int:
    views = rc.list_views()
    names = [str(v.get("name", "")) for v in views]
    fails = 0
    for kw in keywords:
        hits = [n for n in names if kw.lower() in n.lower()]
        if hits:
            lines.append(f"✅ PASS  required_view '{kw}' — {len(hits)} match "
                         f"({hits[0]}{'…' if len(hits) > 1 else ''})")
        else:
            lines.append(f"❌ FAIL  required_view '{kw}' — no view name contains it")
            fails += 1
    return fails


def _check_titleblock(expected: str, lines: list) -> int:
    tbs = rc.list_elements_by_category("Title Blocks")
    if not tbs:
        lines.append("🖐️ NOTE  titleblock — bridge returned no 'Title Blocks' "
                     "elements (no sheets, or category mapping needs DLL check)")
        return 0
    wrong = []
    for tb in tbs:
        fam = (tb.get("family") or tb.get("family_name") or
               tb.get("type") or tb.get("name") or "")
        if expected.lower() not in str(fam).lower():
            wrong.append(f"id {tb.get('id')} ({fam})")
    if wrong:
        lines.append(f"❌ FAIL  titleblock — {len(wrong)} placed titleblocks are not "
                     f"'{expected}': {'; '.join(wrong[:5])}")
        return 1
    lines.append(f"✅ PASS  titleblock — all {len(tbs)} placed titleblocks are '{expected}'")
    return 0


# ─────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────

def run_standards(path: str = STANDARDS_FILE) -> dict:
    """
    Execute standards.yaml against the open model.
    Returns {passed, failed, skipped, lines} for the gate.
    """
    print("\n📋 Standards check (standards.yaml)")
    try:
        std = load_standards(path)
    except FileNotFoundError:
        print(f"❌ {path} not found")
        return {"passed": 0, "failed": 1, "skipped": 0,
                "lines": [f"❌ FAIL  standards.yaml missing at {path}"]}

    lines, failed, skipped = [], 0, 0
    sheets = None

    def _sheets():
        nonlocal sheets
        if sheets is None:
            sheets = _fetch_sheets()
        return sheets

    # sheet_order
    order = std.get("sheet_order") or []
    if not order or _has_todo(order):
        lines.append("⏭️ SKIP  sheet_order — still placeholder (Michael must author "
                     "the canonical order in standards.yaml)")
        skipped += 1
    else:
        failed += _check_sheet_order([str(o) for o in order], _sheets(), lines)

    # sheet_naming
    naming = (std.get("sheet_naming") or {})
    patterns = naming.get("patterns") if isinstance(naming, dict) else None
    if not patterns or _has_todo(patterns):
        lines.append("⏭️ SKIP  sheet_naming — no patterns authored yet")
        skipped += 1
    else:
        failed += _check_sheet_naming([str(p) for p in patterns], _sheets(), lines)

    # required_views
    req = std.get("required_views") or []
    if not req or _has_todo(req):
        lines.append("⏭️ SKIP  required_views — still placeholder")
        skipped += 1
    else:
        failed += _check_required_views([str(k) for k in req], lines)

    # titleblock
    tb = (std.get("titleblock") or {})
    tb_name = tb.get("name", "") if isinstance(tb, dict) else str(tb)
    if not tb_name or _has_todo(tb_name):
        lines.append("⏭️ SKIP  titleblock — family name not authored yet")
        skipped += 1
    else:
        failed += _check_titleblock(tb_name, lines)

    passed = sum(1 for l in lines if l.startswith("✅"))
    for l in lines:
        print(f"  {l}")
    print(f"\n  Standards summary: {passed} pass, {failed} fail, {skipped} skipped")
    return {"passed": passed, "failed": failed, "skipped": skipped, "lines": lines}
