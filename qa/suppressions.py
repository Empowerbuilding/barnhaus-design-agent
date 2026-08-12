"""
suppressions.py — Per-project accepted-finding baseline.

A finding Mitch marks "accepted" gets a stable 8-char key and is suppressed
from every future review of that document. False positives in a punch list
erode trust — suppress once, never see it again.

Files: suppressions/<doc-slug>.json  →  {key: {reason, added, summary}}
"""

import hashlib
import json
import os
import time

SUPP_DIR = "suppressions"


def issue_key(issue: dict) -> str:
    """Stable identity for a finding across runs."""
    src = issue.get("source", "qa")
    typ = issue.get("type") or issue.get("check") or ""
    ident = (issue.get("element_id") or issue.get("dim_id")
             or issue.get("sheet") or issue.get("room") or "")
    msg = (issue.get("message") or issue.get("description") or "")[:48].lower().strip()
    raw = f"{src}|{typ}|{ident}|{msg}"
    return hashlib.sha1(raw.encode()).hexdigest()[:8]


def _path(slug: str) -> str:
    return os.path.join(SUPP_DIR, f"{slug}.json")


def load(slug: str) -> dict:
    p = _path(slug)
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(slug: str, data: dict):
    os.makedirs(SUPP_DIR, exist_ok=True)
    tmp = _path(slug) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _path(slug))


def add(slug: str, key: str, reason: str = "", summary: str = ""):
    data = load(slug)
    data[key] = {"reason": reason, "summary": summary,
                 "added": time.strftime("%Y-%m-%d %H:%M")}
    _save(slug, data)
    print(f"🔇 Suppressed [{key}] on '{slug}'" + (f" — {reason}" if reason else ""))


def remove(slug: str, key: str):
    data = load(slug)
    if key in data:
        del data[key]
        _save(slug, data)
        print(f"🔊 Unsuppressed [{key}] on '{slug}'")
    else:
        print(f"   Key [{key}] not found in suppressions for '{slug}'")


def show(slug: str):
    data = load(slug)
    if not data:
        print(f"   No suppressions for '{slug}'")
        return
    print(f"🔇 {len(data)} suppression(s) on '{slug}':")
    for k, v in data.items():
        print(f"   [{k}] {v.get('summary','')[:70]} — {v.get('reason','')} ({v.get('added')})")


def filter_issues(slug: str, issues: list) -> tuple:
    """Split issues into (visible, suppressed) using the project baseline."""
    baseline = load(slug)
    visible, suppressed = [], []
    for i in issues:
        k = issue_key(i)
        i["key"] = k
        (suppressed if k in baseline else visible).append(i)
    return visible, suppressed
