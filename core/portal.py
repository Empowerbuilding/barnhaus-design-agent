"""
portal.py — Portal Supabase REST helpers (design intent items + agent messaging).

Used by:
    intent_queries.run_verify()  — fetch/update design_intent_items
    run.py gate --post           — post the gate report to a portal channel

Key loading follows the frank_sync.py convention — never hardcoded:
    1. PORTAL_SUPABASE_KEY environment variable (preferred)
    2. .portal_keys.json in the Blueprint workspace or repo root:
       {"portal_supabase_key": "..."}

⚠️ UNTESTED AGAINST LIVE BRIDGE/PORTAL — see DEV_NOTES.md on this branch.
"""

import json
import os
import urllib.request
import urllib.parse

PORTAL_URL    = "https://xqvnpcxyyxxxydescfzw.supabase.co"
PORTAL_ORG_ID = "1c466ccb-ef35-4ba4-bf00-5fcabf20edec"

_KEYS_PATHS = [
    "/home/node/.openclaw/workspace/.portal_keys.json",
    "/home/node/.openclaw/workspace/barnhaus-design-agent/.portal_keys.json",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 ".portal_keys.json"),
]

_cached_key = None


def _load_portal_key() -> str:
    """Service-role key for the portal Supabase project. Lazy + cached."""
    global _cached_key
    if _cached_key:
        return _cached_key
    if os.environ.get("PORTAL_SUPABASE_KEY"):
        _cached_key = os.environ["PORTAL_SUPABASE_KEY"]
        return _cached_key
    for kp in _KEYS_PATHS:
        if os.path.exists(kp):
            with open(kp) as f:
                _cached_key = json.load(f)["portal_supabase_key"]
                return _cached_key
    raise RuntimeError(
        "PORTAL_SUPABASE_KEY not set and no .portal_keys.json found. "
        "Provision the portal service-role key (Tony has it) before running verify/gate --post."
    )


def _headers(prefer: str = "return=representation") -> dict:
    key = _load_portal_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _request(method: str, path: str, params: dict = None, data: dict = None,
             prefer: str = "return=representation"):
    url = f"{PORTAL_URL}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=_headers(prefer))
    req.get_method = lambda: method
    raw = urllib.request.urlopen(req, timeout=20).read()
    return json.loads(raw) if raw else None


# ─────────────────────────────────────────────
# DESIGN INTENT ITEMS
# ─────────────────────────────────────────────

def fetch_intent_items(project_name: str) -> list:
    """
    All design_intent_items for a project. Case-insensitive substring match
    on project_name so 'McGee' finds 'McGee Residence' rows.
    """
    return _request("GET", "design_intent_items", params={
        "project_name": f"ilike.*{project_name}*",
        "order": "created_at.asc",
    }) or []


def update_intent_item(item_id: str, status: str, details: dict) -> bool:
    """PATCH one row's status + details. Returns True on success."""
    try:
        _request("PATCH", "design_intent_items",
                 params={"id": f"eq.{item_id}"},
                 data={"status": status, "details": details},
                 prefer="return=minimal")
        return True
    except Exception as e:
        print(f"  ⚠️  Portal update failed for item {item_id}: {e}")
        return False


# ─────────────────────────────────────────────
# PORTAL MESSAGES
# ─────────────────────────────────────────────

def post_message(channel_id: str, content: str,
                 sender_name: str = "Blueprint") -> bool:
    """Insert a message into a portal channel. Returns True on success."""
    try:
        _request("POST", "portal_messages", data={
            "channel_id":  channel_id,
            "org_id":      PORTAL_ORG_ID,
            "sender_type": "user",
            "sender_name": sender_name,
            "content":     content,
            "processed":   False,
        }, prefer="return=minimal")
        return True
    except Exception as e:
        print(f"  ⚠️  Portal post failed ({channel_id}): {e}")
        return False
