"""
gate.py — Drafter-submission QA gate (ROADMAP Priority 3).

    python3 run.py gate [project_name] [--post]

One command after a drafter submission: standards rules (standards.yaml) +
intent verify (portal design_intent_items) + the existing rule QA suite,
combined into a single report with a final GATE: PASS / FAIL verdict.

The verdict doubles as the fixed-price acceptance criteria — milestone paid
when the gate passes.

GATE PASS requires: 0 standards fails, 0 verify fails, 0 QA "fix" issues.
NEEDS-HUMAN verify items and skipped standards sections are listed but do
not fail the gate (they're not automated evidence either way).

--post posts the combined report to the portal channel `juanito-production`.

⚠️ UNTESTED AGAINST LIVE BRIDGE — see DEV_NOTES.md on this branch.
"""

import time

GATE_CHANNEL = "juanito-production"


def run_gate(project_name: str = None, post: bool = False) -> dict:
    from standards_runner import run_standards
    from intent_queries import run_verify
    from core.project_state import scan_project, load_state
    from core import revit_client as rc
    from qa.qa_runner import run_qa

    print("\n🚧 GATE — full submission check\n" + "─" * 50)

    # Project name for the intent lookup: explicit arg, else document title
    if not project_name:
        doc = rc.call("revit.get_document_info", {})
        if doc.get("success"):
            project_name = (doc.get("result") or {}).get("title", "")
        if project_name:
            print(f"  (no project given — using open document title '{project_name}')")

    # ── 1. Standards ─────────────────────────────────────────────────────
    std = run_standards()

    # ── 2. Intent verify ─────────────────────────────────────────────────
    if project_name:
        ver = run_verify(project_name)
    else:
        print("\n⏭️  Verify skipped — no project name and no document title.")
        ver = {"passed": 0, "failed": 0, "needs_human": 0, "lines": []}

    # ── 3. Existing QA suite ─────────────────────────────────────────────
    print("\n" + "─" * 50)
    try:
        state = load_state()
    except FileNotFoundError:
        state = scan_project()
    qa_report = run_qa(state, auto_fix=False)
    qa_fix = len(qa_report.get("fix", []))
    qa_consider = len(qa_report.get("consider", []))

    # ── Verdict ──────────────────────────────────────────────────────────
    gate_pass = (std["failed"] == 0 and ver["failed"] == 0 and qa_fix == 0)
    verdict = "PASS" if gate_pass else "FAIL"

    summary_lines = [
        f"GATE REPORT — {project_name or 'unnamed project'} — "
        f"{time.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Standards: {std['passed']} pass / {std['failed']} fail / {std['skipped']} skipped",
        f"Intent verify: {ver['passed']} pass / {ver['failed']} fail / "
        f"{ver['needs_human']} needs-human",
        f"QA: {qa_fix} fix / {qa_consider} consider / {len(qa_report.get('fyi', []))} fyi",
        "",
    ]
    summary_lines += std["lines"]
    summary_lines += ver["lines"]
    if qa_fix:
        summary_lines.append("")
        summary_lines += [f"❌ QA FIX: {i.get('message')}" for i in qa_report["fix"]]
    summary_lines += ["", f"GATE: {verdict}"]

    print("\n" + "═" * 50)
    print(f"  Standards: {std['passed']}✅ {std['failed']}❌ {std['skipped']}⏭️")
    print(f"  Verify:    {ver['passed']}✅ {ver['failed']}❌ {ver['needs_human']}🖐️")
    print(f"  QA:        {qa_fix} fix, {qa_consider} consider")
    print("═" * 50)
    print(f"\n{'✅' if gate_pass else '❌'} GATE: {verdict}\n")

    if post:
        from core.portal import post_message
        report_text = "\n".join(summary_lines)
        if post_message(GATE_CHANNEL, report_text):
            print(f"📨 Report posted to portal channel '{GATE_CHANNEL}'")
        else:
            print(f"⚠️  Could not post report to '{GATE_CHANNEL}' — see error above")

    return {"gate": verdict, "standards": std, "verify": ver,
            "qa_fix": qa_fix, "report_lines": summary_lines}
