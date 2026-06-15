"""
qa_runner.py — Runs all QA checks and outputs a consolidated report.

Usage:
    from core.project_state import scan_project
    from qa.qa_runner import run_qa

    state = scan_project()
    report = run_qa(state)
"""

import json
from qa.door_qa        import check_all_doors
from qa.room_qa        import check_all_rooms
from qa.cabinet_qa     import check_all_cabinets
from qa.model_integrity import check_model_integrity


SEVERITY_ORDER = {"fix": 0, "consider": 1, "fyi": 2}


def run_qa(state: dict, auto_fix: bool = False) -> dict:
    """
    Run all QA checks against the project state.
    Returns report dict with issues grouped by severity.

    auto_fix=True will attempt to auto-fix issues marked auto_fixable=True.
    """
    print("\n🔎 Running QA checks...")

    all_issues = []
    all_issues += _check_revit_warnings(state)
    all_issues += check_model_integrity(state)
    all_issues += check_all_rooms(state)
    all_issues += check_all_doors(state)
    all_issues += check_all_cabinets(state)

    # Sort by severity
    all_issues.sort(key=lambda x: SEVERITY_ORDER.get(x.get("severity", "fyi"), 99))

    fix_issues      = [i for i in all_issues if i["severity"] == "fix"]
    consider_issues = [i for i in all_issues if i["severity"] == "consider"]
    fyi_issues      = [i for i in all_issues if i["severity"] == "fyi"]

    report = {
        "total":     len(all_issues),
        "fix":       fix_issues,
        "consider":  consider_issues,
        "fyi":       fyi_issues,
        "auto_fixed": [],
    }

    _print_report(report)

    if auto_fix:
        report["auto_fixed"] = _apply_auto_fixes(fix_issues + consider_issues)

    return report


def _check_revit_warnings(state: dict) -> list:
    """Surface Revit's own warnings directly into the QA report."""
    issues = []
    for w in state.get("warnings", []):
        desc = w.get("description", "")
        elements = w.get("failing_elements", [])
        desc_lower = desc.lower()

        if "insert" in desc_lower and "overlap" in desc_lower:
            severity = "fix"   # overlapping doors/windows — actual problem
        elif "miss" in desc_lower and "target" in desc_lower:
            severity = "fix"   # wall missing its attachment target
        elif "stair" in desc_lower:
            severity = "fix"   # stair code/geometry issues
        elif "overlap" in desc_lower and "wall" in desc_lower:
            severity = "fyi"   # often intentional (corner conditions, stacked walls)
        elif "off axis" in desc_lower:
            severity = "consider"
        elif "duplicate" in desc_lower:
            severity = "fyi"
        else:
            severity = "fyi"

        issues.append({
            "type": "revit_warning",
            "severity": severity,
            "element_id": elements[0] if elements else None,
            "room": None,
            "message": f"[Revit Warning] {desc} (elements: {', '.join(str(e) for e in elements[:3])})",
            "auto_fixable": False,
        })
    return issues


def _print_report(report: dict):
    total = report["total"]
    if total == 0:
        print("✅ No QA issues found. Model looks clean.")
        return

    print(f"\n{'─'*50}")
    print(f"QA REPORT — {total} issue{'s' if total != 1 else ''} found")
    print(f"{'─'*50}")

    if report["fix"]:
        print(f"\n🔴 FIX ({len(report['fix'])}) — must address:")
        for issue in report["fix"]:
            room = f" [{issue['room']}]" if issue.get("room") else ""
            fix  = " ⚡auto-fixable" if issue.get("auto_fixable") else ""
            print(f"  • {issue['message']}{room}{fix}")

    if report["consider"]:
        print(f"\n🟡 CONSIDER ({len(report['consider'])}) — worth reviewing:")
        for issue in report["consider"]:
            room = f" [{issue['room']}]" if issue.get("room") else ""
            fix  = " ⚡auto-fixable" if issue.get("auto_fixable") else ""
            print(f"  • {issue['message']}{room}{fix}")

    if report["fyi"]:
        print(f"\n🔵 FYI ({len(report['fyi'])}):")
        for issue in report["fyi"]:
            room = f" [{issue['room']}]" if issue.get("room") else ""
            print(f"  • {issue['message']}{room}")

    auto_fixable = sum(1 for i in report["fix"] + report["consider"] if i.get("auto_fixable"))
    if auto_fixable:
        print(f"\n⚡ {auto_fixable} issues can be auto-fixed. Run with auto_fix=True to apply.")
    print(f"{'─'*50}\n")


def _apply_auto_fixes(issues: list) -> list:
    """Attempt to auto-fix issues that are marked auto_fixable."""
    from core import revit_client as rc
    fixed = []

    for issue in issues:
        if not issue.get("auto_fixable"):
            continue
        action     = issue.get("fix_action")
        element_id = issue.get("element_id")

        if action == "flip_door_swing" and element_id:
            result = rc.call("revit.flip_door", {"door_id": element_id})
            if result.get("success"):
                print(f"  ⚡ Auto-fixed: flipped door {element_id} ({issue['room']})")
                fixed.append({"issue": issue, "action": action, "element_id": element_id})

        elif action == "snap_wall_to_axis" and element_id:
            result = rc.call("revit.snap_wall_to_axis", {"wall_id": element_id})
            if result.get("success"):
                print(f"  ⚡ Auto-fixed: snapped wall {element_id} to axis")
                fixed.append({"issue": issue, "action": action, "element_id": element_id})

        elif action == "nudge_element" and element_id:
            # Nudge is context-specific — skip for now, needs more geometry info
            pass

    return fixed


def save_report(report: dict, path: str = "qa_report.json"):
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"💾 QA report saved to {path}")
