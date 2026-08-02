#!/usr/bin/env python3
"""
import_subs_from_bb.py — One-time importer for subcontractor records.

Pulls subcontractor/vendor data from BudgetBuilder into Frank's subcontractors
table. This is a seed script — run it ONCE during initial setup.

After seeding, manage subs directly in Frank's Supabase. Never depend on BB
for live operations.

Usage:
    python3 automation/import_subs_from_bb.py [--dry-run]

Options:
    --dry-run    Print what would be imported without writing to Frank's DB.
"""

import json
import sys
import urllib.request
import urllib.error

# ─── Frank-only Config ───────────────────────────────────────────────────────
FRANK_URL = "https://stlvgflkgqhtxfxuorvf.supabase.co"
FRANK_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0bHZnZmxrZ3FodHhmeHVvcnZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQ0MDExMCwiZXhwIjoyMDkxMDE2MTEwfQ.nZ3Fu0bw36mp1HMyiCdiuKdFJX8koU9jbuYpvj7f0WM"

# BudgetBuilder — READ-ONLY, used for initial seed ONLY
BB_URL = "https://hbfjdfxephlczkfgpceg.supabase.co"
BB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiZmpkZnhlcGhsY3prZmdwY2VnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTMzNzcxMCwiZXhwIjoyMDU0OTEzNzEwfQ.weXk7CqDqR8XkEpi4kaI_GmHWlkqh6snOMQm-hk48RM"


def bb_get(path):
    url = f"{BB_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        "apikey": BB_KEY,
        "Authorization": f"Bearer {BB_KEY}",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def frank_post(data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{FRANK_URL}/rest/v1/subcontractors",
        data=body,
        headers={
            "apikey": FRANK_KEY,
            "Authorization": f"Bearer {FRANK_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def frank_get_existing():
    url = f"{FRANK_URL}/rest/v1/subcontractors?select=email&limit=2000"
    req = urllib.request.Request(url, headers={
        "apikey": FRANK_KEY,
        "Authorization": f"Bearer {FRANK_KEY}",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        rows = json.loads(resp.read().decode())
    return {(r.get("email") or "").lower() for r in rows if r.get("email")}


def main():
    dry_run = "--dry-run" in sys.argv

    print("=== Frank subcontractor importer (one-time seed) ===")
    print("⚠️  Using BudgetBuilder READ-ONLY. This script is for initial setup only.\n")

    if dry_run:
        print("DRY RUN — no data will be written to Frank's DB.\n")

    # Pull from BB — try common table names
    subs_raw = []
    for table in ["subcontractors", "vendors", "contractors"]:
        try:
            result = bb_get(f"{table}?limit=1000")
            if isinstance(result, list) and result:
                print(f"  Found {len(result)} records in BB.{table}")
                subs_raw = result
                break
        except Exception as e:
            # Table doesn't exist or no access
            pass

    if not subs_raw:
        print("⚠️  No subcontractor data found in BudgetBuilder.")
        print("    BB may not have a subs table, or table name differs.")
        print("    Skipping import — Frank's subcontractors table is clean.")
        return

    # Map BB fields to Frank schema
    existing_emails = frank_get_existing() if not dry_run else set()
    to_insert = []
    skipped = 0

    for s in subs_raw:
        email = (s.get("email") or "").strip().lower()
        company = (s.get("company_name") or s.get("name") or s.get("company") or "").strip()
        if not company:
            continue

        if email and email in existing_emails:
            skipped += 1
            continue

        record = {
            "company_name": company,
            "trade": (s.get("trade") or s.get("specialty") or "").strip(),
            "email": email or None,
            "phone": (s.get("phone") or "").strip() or None,
            "contact_name": (s.get("contact_name") or s.get("contact") or "").strip() or None,
            "city": (s.get("city") or "").strip() or None,
            "notes": f"Imported from BudgetBuilder — original ID: {s.get('id', 'unknown')}",
            "active": True,
            "source": "budget_builder_import",
        }
        to_insert.append(record)

    print(f"  Ready to import: {len(to_insert)} subs ({skipped} already exist)\n")

    if dry_run:
        for r in to_insert[:10]:
            print(f"  Would insert: {r['company_name']} / {r['trade']} / {r['email']}")
        if len(to_insert) > 10:
            print(f"  ... and {len(to_insert)-10} more")
        print("\n[DRY RUN complete — nothing written]")
        return

    # Batch insert
    batch_size = 50
    inserted = 0
    for i in range(0, len(to_insert), batch_size):
        batch = to_insert[i:i+batch_size]
        try:
            status = frank_post(batch)
            inserted += len(batch)
            print(f"  Batch {i//batch_size+1}: {len(batch)} inserted (status {status})")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  ERROR batch {i//batch_size+1}: {e.code} — {body[:200]}")

    print(f"\n✅ Imported {inserted} subcontractors into Frank's DB")
    print("Done. From here, manage subs in Frank's Supabase directly.")


if __name__ == "__main__":
    main()
