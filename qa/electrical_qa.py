"""
electrical_qa.py — Electrical fixture label QA.

Fetches all electrical-family elements in the model and verifies each one's
Type Mark is properly labeled (not blank). Flags blanks per category.

Categories checked:
  Electrical Fixtures, Electrical Equipment, Lighting Fixtures,
  Lighting Devices (switches), Communication Devices

Usage:
    from qa.electrical_qa import run_electrical_qa
    issues = run_electrical_qa()          # queries the live model
"""

from core import revit_client as rc

ELECTRICAL_CATEGORIES = [
    "Electrical Fixtures",
    "Electrical Equipment",
    "Lighting Fixtures",
    "Lighting Devices",
    "Communication Devices",
]


def run_electrical_qa() -> list:
    """Check Type Marks on all electrical items in the live model."""
    print("\n⚡ Electrical Label QA")
    issues = []
    total = 0
    type_mark_cache = {}  # type_name+family -> mark (avoid re-fetching same type)

    for category in ELECTRICAL_CATEGORIES:
        elements = rc.list_elements_by_category(category)
        if not elements:
            print(f"   {category}: 0 elements")
            continue

        blanks = []
        for e in elements:
            total += 1
            cache_key = f"{e.get('name','')}|{e.get('type','')}"
            if cache_key in type_mark_cache:
                mark = type_mark_cache[cache_key]
            else:
                params = rc.get_type_param_map(e.get("id"))
                mark = (params.get("Type Mark") or "").strip()
                type_mark_cache[cache_key] = mark

            if not mark:
                blanks.append(e)
                issues.append({
                    "check":      "electrical_type_mark_blank",
                    "severity":   "warning",
                    "category":   category,
                    "element_id": e.get("id"),
                    "message":    (f"{category} {e.get('id')} "
                                   f"({e.get('name','?')} / {e.get('type','?')}): Type Mark is BLANK"),
                })

        status = f"⚠️  {len(blanks)} blank marks" if blanks else "✅ all labeled"
        print(f"   {category}: {len(elements)} elements — {status}")

    print(f"\n   Checked {total} electrical items — {len(issues)} blank Type Marks")
    for i in issues:
        print(f"   ⚠️  {i['message']}")
    return issues
