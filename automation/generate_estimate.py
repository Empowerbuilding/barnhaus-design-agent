#!/usr/bin/env python3
"""
generate_estimate.py — Generate a cost estimate from Frank's takeoffs + unit_costs.

Reads all takeoffs for a project from Frank's Supabase, matches each line item
to Frank's own unit_costs table, and outputs a formatted estimate.

Usage:
    python3 automation/generate_estimate.py <project_id> [--json] [--csv]

Options:
    --json    Also write estimate_<project_id>.json
    --csv     Also write estimate_<project_id>.csv

NOTE: All unit costs are read from Frank's OWN unit_costs table.
      BudgetBuilder is NEVER queried here.
"""

import sys
import json
import csv
import urllib.request
import urllib.parse
from datetime import datetime

# ─── Frank-only Config ───────────────────────────────────────────────────────
FRANK_URL = "https://stlvgflkgqhtxfxuorvf.supabase.co"
FRANK_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0bHZnZmxrZ3FodHhmeHVvcnZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQ0MDExMCwiZXhwIjoyMDkxMDE2MTEwfQ.nZ3Fu0bw36mp1HMyiCdiuKdFJX8koU9jbuYpvj7f0WM"

HEADERS = {
    "apikey": FRANK_KEY,
    "Authorization": f"Bearer {FRANK_KEY}",
}


def frank_get(path):
    url = f"{FRANK_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def load_unit_costs():
    """Load all unit costs from Frank's own table. Never queries BB."""
    rows = frank_get("unit_costs?select=item,category,unit,unit_cost,actual_unit_cost,multiplier&limit=2000")
    cost_map = {}
    for row in rows:
        name = (row.get("item") or "").strip().lower()
        # effective cost = actual_unit_cost if set and > 0, else unit_cost
        effective = row.get("actual_unit_cost") or row.get("unit_cost") or 0
        multiplier = row.get("multiplier") or 1
        if name:
            cost_map[name] = {
                "item": row.get("item", ""),
                "category": row.get("category", ""),
                "unit": row.get("unit", ""),
                "unit_cost": float(effective) * float(multiplier),
                "raw_unit_cost": float(row.get("unit_cost") or 0),
                "actual_unit_cost": float(row.get("actual_unit_cost") or 0),
                "multiplier": float(multiplier),
            }
    return cost_map


def fuzzy_match(item_type: str, cost_map: dict):
    """Try exact match, then keyword substring match."""
    key = item_type.strip().lower()

    # Exact
    if key in cost_map:
        return cost_map[key]

    # Partial: takeoff key contains cost item name
    for cost_key, cost_data in cost_map.items():
        if cost_key in key or key in cost_key:
            return cost_data

    # Word-level: any shared significant word (>4 chars)
    key_words = set(w for w in key.split() if len(w) > 4)
    best = None
    best_score = 0
    for cost_key, cost_data in cost_map.items():
        cost_words = set(w for w in cost_key.split() if len(w) > 4)
        shared = len(key_words & cost_words)
        if shared > best_score:
            best_score = shared
            best = cost_data

    return best if best_score >= 2 else None


def generate_estimate(project_id: str, output_json=False, output_csv=False):
    print(f"\n=== Frank Estimate Generator ===")
    print(f"Project: {project_id}")
    print(f"Source:  Frank's own unit_costs table (BudgetBuilder NOT queried)\n")

    # Load project info
    projects = frank_get(f"projects?id=eq.{project_id}&select=name,address,status&limit=1")
    if projects:
        p = projects[0]
        print(f"📋 {p.get('name', 'Unknown')} — {p.get('address', '')}")
    else:
        print(f"⚠️  Project {project_id} not found in DB — continuing with takeoffs only")

    # Load takeoffs
    takeoffs = frank_get(
        f"takeoffs?project_id=eq.{project_id}&select=category,item_type,quantity,unit,trade,description&limit=2000"
    )
    print(f"📦 {len(takeoffs)} takeoff line items loaded")

    if not takeoffs:
        print("⚠️  No takeoffs found for this project. Run frank_sync.py first.")
        return None

    # Load unit costs from Frank's own table
    cost_map = load_unit_costs()
    print(f"💰 {len(cost_map)} unit costs loaded from Frank's unit_costs table\n")

    # Match and price each line item
    estimate_lines = []
    unmatched = []

    for row in takeoffs:
        item_type = row.get("item_type") or ""
        qty = float(row.get("quantity") or 0)
        category = row.get("category") or ""
        trade = row.get("trade") or ""
        unit = row.get("unit") or ""

        match = fuzzy_match(item_type, cost_map)

        if match:
            unit_cost = match["unit_cost"]
            line_total = qty * unit_cost
            estimate_lines.append({
                "category": category,
                "trade": trade,
                "item_type": item_type,
                "quantity": qty,
                "unit": unit,
                "unit_cost": unit_cost,
                "line_total": line_total,
                "matched_to": match["item"],
                "matched": True,
            })
        else:
            unmatched.append({
                "category": category,
                "trade": trade,
                "item_type": item_type,
                "quantity": qty,
                "unit": unit,
                "unit_cost": 0,
                "line_total": 0,
                "matched_to": "",
                "matched": False,
            })

    # Sort by category then trade
    estimate_lines.sort(key=lambda x: (x["category"], x["trade"]))
    unmatched.sort(key=lambda x: (x["category"], x["trade"]))

    all_lines = estimate_lines + unmatched

    # Subtotals by trade
    by_trade = {}
    for line in estimate_lines:
        t = line["trade"]
        by_trade[t] = by_trade.get(t, 0) + line["line_total"]

    grand_total = sum(line["line_total"] for line in estimate_lines)

    # ── Print report ─────────────────────────────────────────────────────
    current_cat = None
    print(f"{'─'*80}")
    print(f"{'ITEM':<45} {'QTY':>8} {'UNIT':<6} {'$/UNIT':>10} {'TOTAL':>12}")
    print(f"{'─'*80}")

    for line in all_lines:
        if line["category"] != current_cat:
            current_cat = line["category"]
            print(f"\n▸ {current_cat}")

        match_flag = "" if line["matched"] else "  ⚠️ NO MATCH"
        label = line["item_type"][:43]
        print(
            f"  {label:<43} {line['quantity']:>8.1f} {line['unit']:<6} "
            f"{line['unit_cost']:>10.2f} {line['line_total']:>12,.2f}{match_flag}"
        )

    print(f"\n{'─'*80}")
    print(f"{'TRADE SUBTOTALS':}")
    for trade, total in sorted(by_trade.items(), key=lambda x: -x[1]):
        print(f"  {trade:<40} ${total:>12,.2f}")

    print(f"\n{'═'*80}")
    print(f"  GRAND TOTAL (matched items)              ${grand_total:>12,.2f}")
    print(f"{'═'*80}")
    print(f"\n  ✅ Matched: {len(estimate_lines)} / {len(takeoffs)} line items")
    print(f"  ⚠️  Unmatched: {len(unmatched)} line items (need manual pricing)")

    # ── Output files ─────────────────────────────────────────────────────
    result = {
        "project_id": project_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "frank_unit_costs_only",
        "grand_total": grand_total,
        "matched_count": len(estimate_lines),
        "unmatched_count": len(unmatched),
        "by_trade": by_trade,
        "line_items": all_lines,
    }

    if output_json:
        fname = f"estimate_{project_id[:8]}.json"
        with open(fname, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 JSON saved: {fname}")

    if output_csv:
        fname = f"estimate_{project_id[:8]}.csv"
        with open(fname, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["category", "trade", "item_type", "quantity", "unit",
                            "unit_cost", "line_total", "matched_to", "matched"],
            )
            writer.writeheader()
            writer.writerows(all_lines)
        print(f"💾 CSV saved: {fname}")

    return result


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print("Usage: python3 automation/generate_estimate.py <project_id> [--json] [--csv]")
        sys.exit(1)

    project_id = args[0]
    output_json = "--json" in args
    output_csv = "--csv" in args

    generate_estimate(project_id, output_json=output_json, output_csv=output_csv)


if __name__ == "__main__":
    main()
