#!/usr/bin/env python3
"""
seed_unit_costs.py — One-time seeder for Frank's unit_costs table.

Pulls all items from BudgetBuilder (READ-ONLY, one-time use), deduplicates
by item name (keeping highest actual_unit_cost), resolves category names,
and inserts into Frank's own unit_costs table.

Usage:
    python3 automation/seed_unit_costs.py [--clear]

Options:
    --clear    Truncate unit_costs before seeding (for a clean reseed)

After seeding, Frank operates entirely from his own unit_costs table.
This script is the ONLY permitted use of BB credentials.
"""

import json
import sys
import urllib.request
import urllib.error

# ─── Config ───────────────────────────────────────────────────────────────────
FRANK_URL = "https://stlvgflkgqhtxfxuorvf.supabase.co"
FRANK_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0bHZnZmxrZ3FodHhmeHVvcnZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQ0MDExMCwiZXhwIjoyMDkxMDE2MTEwfQ.nZ3Fu0bw36mp1HMyiCdiuKdFJX8koU9jbuYpvj7f0WM"

BB_URL = "https://hbfjdfxephlczkfgpceg.supabase.co"
BB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiZmpkZnhlcGhsY3prZmdwY2VnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTMzNzcxMCwiZXhwIjoyMDU0OTEzNzEwfQ.weXk7CqDqR8XkEpi4kaI_GmHWlkqh6snOMQm-hk48RM"

BATCH_SIZE = 100
ITEM_LIMIT_PER_PAGE = 1000


def bb_get(path, key):
    """GET from BudgetBuilder with pagination."""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    results = []
    offset = 0
    while True:
        url = f"{BB_URL}/rest/v1/{path}&limit={ITEM_LIMIT_PER_PAGE}&offset={offset}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            page = json.loads(resp.read().decode())
        if not page:
            break
        results.extend(page)
        if len(page) < ITEM_LIMIT_PER_PAGE:
            break
        offset += ITEM_LIMIT_PER_PAGE
    return results


def frank_post(path, data, key, method="POST"):
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    req = urllib.request.Request(
        f"{FRANK_URL}/rest/v1/{path}",
        data=json.dumps(data).encode(),
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main():
    clear = "--clear" in sys.argv

    print("=== Frank unit_costs seeder ===")
    print("⚠️  Using BudgetBuilder READ-ONLY for seeding. Never use BB in live ops.\n")

    # 1. Pull categories from BB
    print("Fetching BB categories...")
    cats_raw = bb_get("budget_builder_categories?select=id,category_name", BB_KEY)
    cat_map = {c["id"]: c.get("category_name", "").strip() for c in cats_raw}
    print(f"  {len(cat_map)} categories loaded")

    # 2. Pull all items from BB
    print("Fetching BB items (all pages)...")
    items_raw = bb_get(
        "budget_builder_items?select=item,unit,unit_cost,actual_unit_cost,multiplier,code,category_id",
        BB_KEY,
    )
    print(f"  {len(items_raw)} raw items fetched")

    # 3. Deduplicate: keep highest actual_unit_cost (or unit_cost) per item name
    deduped = {}
    for item in items_raw:
        name = (item.get("item") or "").strip()
        if not name:
            continue
        cost = item.get("actual_unit_cost") or item.get("unit_cost") or 0
        existing = deduped.get(name)
        if existing is None:
            deduped[name] = item
        else:
            existing_cost = existing.get("actual_unit_cost") or existing.get("unit_cost") or 0
            if cost > existing_cost:
                deduped[name] = item

    print(f"  {len(deduped)} unique items after deduplication")

    # 4. Enrich with category names
    enriched = []
    for name, item in deduped.items():
        cat_id = item.get("category_id")
        enriched.append({
            "item": name,
            "category": cat_map.get(cat_id, "") if cat_id else "",
            "unit": item.get("unit") or "",
            "unit_cost": item.get("unit_cost"),
            "actual_unit_cost": item.get("actual_unit_cost"),
            "multiplier": item.get("multiplier") or 1,
            "code": item.get("code") or "",
            "source": "budget_builder",
        })

    # 5. Optionally clear existing rows
    if clear:
        print("\nClearing existing unit_costs rows...")
        headers = {
            "apikey": FRANK_KEY,
            "Authorization": f"Bearer {FRANK_KEY}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            f"{FRANK_URL}/rest/v1/unit_costs?id=neq.00000000-0000-0000-0000-000000000000",
            headers=headers,
            method="DELETE",
        )
        with urllib.request.urlopen(req) as resp:
            print(f"  Cleared (status {resp.status})")

    # 6. Batch insert into Frank's unit_costs
    print(f"\nSeeding {len(enriched)} items into Frank's unit_costs (batches of {BATCH_SIZE})...")
    total = 0
    errors = []
    for i in range(0, len(enriched), BATCH_SIZE):
        batch = enriched[i : i + BATCH_SIZE]
        try:
            status = frank_post("unit_costs", batch, FRANK_KEY)
            total += len(batch)
            print(f"  Batch {i//BATCH_SIZE + 1}: {len(batch)} rows — status {status}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            errors.append(f"Batch {i//BATCH_SIZE + 1}: {e.code} — {body[:300]}")
            print(f"  ERROR batch {i//BATCH_SIZE + 1}: {e.code} — {body[:200]}")

    print(f"\n✅ Seeded {total} rows into Frank's unit_costs table")
    if errors:
        print(f"⚠️  {len(errors)} batch error(s):")
        for err in errors:
            print(f"   {err}")
    else:
        print("No errors.")

    print("\nDone. Frank is now independent from BudgetBuilder.")


if __name__ == "__main__":
    main()
