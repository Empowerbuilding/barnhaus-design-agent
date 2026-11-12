"""
report_stamp.py - says what a QA report was taken on (Blueprint, 2026-11-12, M3 prep A3 part 6: the P12 checker).

The model gate (run.py qa-model) and the marks check (run.py qa-marks) print their result and, for the gate, save
model_qa_report.json. Neither file said which document it was about or when it was taken, so a later check
(automation/checks_final.py, the gate final.qa_clean) could not tell a report of this model from an old one of another.
This module adds that, and nothing else: it never changes a finding, a count or an exit code.

    stamp_model_report(report, full, flags)   -> the same report with "document", "at", "full" and "flags"
    marks_report(state, issues)               -> what run.py qa-marks saves as marks_qa_report.json

A title that cannot be read is written as null, never guessed: the reader treats a report without a document as not
usable. No function here raises.
"""
import time

MARKS_REPORT_FILE = "marks_qa_report.json"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def open_title(call=None):
    """Title of the document open in Revit, or None when the bridge does not give one. One read-only call."""
    try:
        if call is None:
            from core.revit_client import call as call  # noqa: PLW0127
        r = call("revit.get_document_info", {})
        if not isinstance(r, dict) or not r.get("success"):
            return None
        res = r.get("result")
        title = res.get("title") if isinstance(res, dict) else None
        return str(title).strip() if title and str(title).strip() else None
    except Exception:
        return None


def stamp_model_report(report: dict, full: bool, flags=None, call=None) -> dict:
    """full = the gate looked at the whole model: no --since-mins, no --must-cover, no sheet-only call."""
    try:
        report["document"] = open_title(call)
        report["at"] = now_iso()
        report["full"] = bool(full) and not report.get("not_run")
        report["flags"] = [str(f) for f in (flags or [])]
    except Exception:
        pass
    return report


def marks_report(state: dict, issues: list) -> dict:
    """The marks check as a file: the document it read, where the data came from, how much it looked at, what it found."""
    state = state if isinstance(state, dict) else {}
    issues = issues if isinstance(issues, list) else []
    title = (state.get("document") or {}).get("title") if isinstance(state.get("document"), dict) else None
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    sev = lambda s: [i for i in issues if isinstance(i, dict) and i.get("severity") == s]
    return {
        "document": str(title).strip() if title and str(title).strip() else None,
        "at": now_iso(),
        "source": source.get("kind"),
        "doors": len(state.get("doors") or []),
        "windows": len(state.get("windows") or []),
        "errors": sev("error"),
        "warnings": sev("warning"),
        "other": [i for i in issues if not (isinstance(i, dict) and i.get("severity") in ("error", "warning"))],
    }
