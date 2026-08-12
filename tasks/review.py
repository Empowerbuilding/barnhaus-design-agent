"""
review.py — One-shot drafter-submission audit. THE core Blueprint command.

    python3 run.py review [--visual] [--no-scan] [--upload]

Runs: scan → rule QA → type-mark QA → electrical QA → dims QA →
completeness gate → (optional) visual QA → suppression filter →
diff vs last review → consolidated scorecard + drafter punch list.

Outputs:
    review_report.json    — full structured report
    review_punchlist.md   — numbered, drafter-ready punch list
    snapshots/<slug>/     — snapshot for next review's diff
"""

import json
import os
import time

from core.project_state import scan_project, load_state
from core.revit_client import health_check
from core import snapshots
from qa import suppressions

# severity → bucket mapping per source
#   blocker    = must fix before the set goes anywhere
#   should_fix = real drafting errors, fix this revision
#   nitpick    = polish / fyi
def _bucket(issue: dict) -> str:
    src = issue.get("source", "qa")
    sev = issue.get("severity", "")
    if src == "qa":
        return {"fix": "blocker", "consider": "should_fix"}.get(sev, "nitpick")
    if src == "marks":
        return {"error": "should_fix"}.get(sev, "nitpick")
    if src == "electrical":
        return "should_fix"
    if src == "dims":
        return {"warning": "should_fix"}.get(sev, "nitpick")
    if src == "completeness":
        return {"error": "blocker", "warning": "should_fix"}.get(sev, "nitpick")
    if src == "visual":
        return {"error": "should_fix"}.get(sev, "nitpick")
    return "nitpick"


def _msg(issue: dict) -> str:
    return issue.get("message") or issue.get("description") or str(issue)


def run_review(visual: bool = False, no_scan: bool = False,
               upload: bool = False) -> dict:
    t0 = time.time()
    print("\n📋 REVIEW — full drafter-submission audit\n" + "─" * 50)

    # 0. Bridge gate — offline mode runs state-based checks only
    bridge_ok = health_check()
    if not bridge_ok:
        print("   ⚠️  Bridge offline — running state-based checks only "
              "(electrical/dims/visual skipped)")

    # 1. Model state
    if no_scan or not bridge_ok:
        try:
            state = load_state()
            if not bridge_ok:
                print("   Using cached project_state.json (bridge offline)")
            else:
                print("   Using cached project_state.json (--no-scan)")
        except FileNotFoundError:
            if not bridge_ok:
                print("❌ No cached state and no bridge — cannot review.")
                return {"error": "no state, no bridge"}
            state = scan_project()
    else:
        state = scan_project()
    slug = snapshots.doc_slug(state)
    doc = (state.get("document") or {}).get("title", "?")

    issues = []

    # 2. Rule-based QA (rooms/doors/cabinets/integrity/warnings)
    print("\n── Rule QA ──")
    from qa.qa_runner import run_qa
    qa_rep = run_qa(state)
    for sev_group in ("fix", "consider", "fyi"):
        for i in qa_rep.get(sev_group, []):
            i["source"] = "qa"
            issues.append(i)

    # 3. Type-mark QA (state-based)
    print("\n── Type Mark QA ──")
    try:
        from qa.opening_marks_qa import run_opening_marks_qa
        for i in run_opening_marks_qa(state):
            i["source"] = "marks"
            issues.append(i)
    except Exception as e:
        print(f"   ⚠️  marks QA skipped: {e}")

    # 4. Electrical QA (live bridge)
    if bridge_ok:
        print("\n── Electrical QA ──")
        try:
            from qa.electrical_qa import run_electrical_qa
            for i in run_electrical_qa():
                i["source"] = "electrical"
                issues.append(i)
        except Exception as e:
            print(f"   ⚠️  electrical QA skipped: {e}")

    # 5. Dimension consistency QA (live bridge)
    if bridge_ok:
        print("\n── Dimension QA ──")
        try:
            from qa.dims_qa import run as dims_run
            for i in dims_run():
                i["source"] = "dims"
                issues.append(i)
        except Exception as e:
            print(f"   ⚠️  dims QA skipped: {e}")

    # 6. Completeness gate (state-based)
    print("\n── Completeness ──")
    from qa.completeness import check_completeness
    comp = check_completeness(state)
    issues += comp
    print(f"   {len(comp)} completeness issue(s)")

    # 7. Visual QA — heavy; only with --visual, else reuse last report
    print("\n── Visual QA ──")
    vqa_findings = []
    if visual and not bridge_ok:
        print("   ⚠️  --visual requires the bridge — skipped")
        visual = False
    if visual:
        from qa.visual_qa import run_visual_qa
        vrep = run_visual_qa()
        for sh in vrep.get("sheets", []):
            for f in sh.get("findings", []):
                f["sheet"] = sh.get("sheet")
                vqa_findings.append(f)
    elif os.path.exists("visual_qa_report.json"):
        try:
            vrep = json.load(open("visual_qa_report.json"))
            for sh in vrep.get("sheets", []):
                for f in sh.get("findings", []):
                    f["sheet"] = sh.get("sheet")
                    vqa_findings.append(f)
            print(f"   Reusing existing visual_qa_report.json "
                  f"({len(vqa_findings)} findings) — pass --visual to re-run")
        except (json.JSONDecodeError, OSError):
            pass
    else:
        print("   No visual report — pass --visual to run sheet vision QA")
    for f in vqa_findings:
        f["source"] = "visual"
        issues.append(f)

    # 8. Suppression baseline
    visible, suppressed = suppressions.filter_issues(slug, issues)

    # 9. Buckets
    buckets = {"blocker": [], "should_fix": [], "nitpick": []}
    for i in visible:
        buckets[_bucket(i)].append(i)

    # 10. Diff vs last review
    issue_keys = [i["key"] for i in visible]
    prev = snapshots.load_previous(slug)
    snap = snapshots.build_snapshot(state, issue_keys)
    diff = snapshots.diff_snapshots(prev, snap) if prev else None

    # 11. Optional crop upload for punch list embedding
    if upload:
        try:
            from qa.annotate import upload_findings_crops
            n = upload_findings_crops(visible, slug)
            if n:
                print(f"\n   ☁️  {n} finding crop(s) uploaded")
        except Exception as e:
            print(f"   ⚠️  crop upload skipped: {e}")

    # 12. Report + punch list + snapshot
    report = {
        "document": doc, "slug": slug,
        "reviewed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_s": round(time.time() - t0, 1),
        "counts": {b: len(v) for b, v in buckets.items()},
        "suppressed": len(suppressed),
        "blockers": buckets["blocker"],
        "should_fix": buckets["should_fix"],
        "nitpicks": buckets["nitpick"],
        "diff": diff,
    }
    with open("review_report.json", "w") as f:
        json.dump(report, f, indent=1, default=str)
    _write_punchlist(report)
    snapshots.save_snapshot(snap, slug)

    # 13. Scorecard to console
    print("\n" + "═" * 50)
    print(f"📋 REVIEW SCORECARD — {doc}")
    print(f"   🔴 Blockers:   {len(buckets['blocker'])}")
    print(f"   🟠 Should fix: {len(buckets['should_fix'])}")
    print(f"   🟡 Nitpicks:   {len(buckets['nitpick'])}")
    if suppressed:
        print(f"   🔇 Suppressed: {len(suppressed)}")
    if diff:
        print()
        print(snapshots.format_diff(diff))
    else:
        print("   (first review of this document — no diff)")
    for b, icon in (("blocker", "🔴"), ("should_fix", "🟠")):
        for i in buckets[b][:15]:
            print(f"   {icon} [{i['key']}] {_msg(i)[:100]}")
    print(f"\n   💾 review_report.json + review_punchlist.md saved "
          f"({report['duration_s']}s)")
    print("   To suppress a finding: python3 run.py suppress <key> [reason]")
    return report


def _write_punchlist(report: dict):
    """Drafter-ready numbered punch list, forwardable verbatim."""
    lines = [f"# Punch List — {report['document']}",
             f"_Review date: {report['reviewed_at']}_", ""]
    n = 0
    sections = [("Must fix before this set moves forward", report["blockers"]),
                ("Fix in this revision", report["should_fix"]),
                ("Polish (non-blocking)", report["nitpicks"])]
    for title, items in sections:
        if not items:
            continue
        lines.append(f"## {title}")
        for i in items:
            n += 1
            loc = ""
            if i.get("sheet"):
                loc = f" _(sheet {i['sheet']})_"
            elif i.get("element_id"):
                loc = f" _(element {i['element_id']})_"
            lines.append(f"{n}. {_msg(i)}{loc}")
            if i.get("crop_url"):
                lines.append(f"   ![finding {n}]({i['crop_url']})")
            elif i.get("crop_path"):
                lines.append(f"   _(image: {i['crop_path']})_")
        lines.append("")
    if n == 0:
        lines.append("✅ No open findings — set is clean.")
    with open("review_punchlist.md", "w") as f:
        f.write("\n".join(lines))
