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

Usage:
    from qa.opening_marks_qa import run_opening_marks_qa
    issues = run_opening_marks_qa(state)
"""

import re

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


def run_opening_marks_qa(state: dict) -> list:
    """Run type-mark QA on doors + windows from a scanned state. Returns issue list."""
    doors   = state.get("doors", [])
    windows = state.get("windows", [])

    print("\n🏷️  Opening Type Mark QA")
    print(f"   Checking {len(doors)} doors, {len(windows)} windows...")

    if doors and "type_mark" not in doors[0]:
        print("   ⚠️  State was scanned before type_mark support — run a fresh scan first.")
        return [{"check": "stale_state", "severity": "error",
                 "message": "project_state.json predates type_mark capture. Re-run: python3 run.py scan"}]

    issues = _check_elements(doors, "Door") + _check_elements(windows, "Window")

    errors   = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    print(f"   {len(errors)} errors, {len(warnings)} warnings")
    for i in issues:
        icon = "❌" if i["severity"] == "error" else "⚠️ "
        print(f"   {icon} {i['message']}")
    if not issues:
        print("   ✅ All door/window type marks check out")
    return issues
