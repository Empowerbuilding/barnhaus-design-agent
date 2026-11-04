#!/usr/bin/env python3
"""Post a card to an Agent Portal channel MID-TASK (ack / result / status cards).

This exists so work is never silent: an agent turn only delivers its final
message at turn END, which means results can sit un-communicated for many
minutes while post-completion QA runs. This helper posts immediately.

Usage:
  python3 automation/post_portal_card.py <channel_id> "<message text>"
  python3 automation/post_portal_card.py <channel_id> --file <path>

Reads Supabase URL + service key from ~/.openclaw/openclaw.json (channels.portal).
Exit code 0 + "posted" on success.
"""
import json
import os
import sys
import urllib.request


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    channel = args[0]
    if args[1] == "--file":
        if len(args) < 3:
            print("error: --file needs a path")
            sys.exit(1)
        with open(args[2]) as f:
            text = f.read()
    else:
        text = args[1]
    if not text.strip():
        print("error: empty message")
        sys.exit(1)

    cfg_path = os.path.expanduser("~/.openclaw/openclaw.json")
    with open(cfg_path) as f:
        cfg = json.load(f)
    portal = cfg["channels"]["portal"]
    url = portal["supabaseUrl"].rstrip("/") + "/rest/v1/portal_messages"
    key = portal["supabaseKey"]

    body = json.dumps({
        "channel_id": channel,
        "org_id": portal.get("orgId", "1c466ccb-ef35-4ba4-bf00-5fcabf20edec"),
        "sender_type": "agent",
        "sender_name": "Blueprint",
        "content": text,
        "processed": True,
    }).encode()

    req = urllib.request.Request(url, data=body, headers={
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status in (200, 201):
                print("posted")
            else:
                print("unexpected status:", r.status)
                sys.exit(1)
    except Exception as e:
        print("post failed:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
