"""
takeoffs.py — Pull a full material and quantity takeoff from the open Revit model.

Matches the Camp takeoff format:
  Area Schedule, Floors, Walls, Roof, Ceilings, Gypsum, Stucco/Stone/Tile,
  Doors, Windows, Cabinets, Countertops, Plumbing, Electrical, Equipment

Usage:
    python3 run.py takeoffs
"""

import json
import os
from core import revit_client as rc

SQFT_PER_SQFT  = 1.0
SQFT_PER_CY    = 27.0      # cu ft / cy
CF_TO_SF_GYPSUM = 1 / (0.5 / 12)    # 1/2" drywall
CF_TO_SF_STUCCO = 1 / (0.875 / 12)  # 7/8" stucco
CF_TO_SF_TILE   = 1 / (0.375 / 12)  # 3/8" tile/mortar bed


def _call(tool, payload):
    r = rc.call(tool, payload)
    if not r.get("success"):
        return None
    return r.get("result", {})


def _list_elements(category):
    r = _call("revit.list_elements_by_category", {"category": category})
    if r is None:
        return []
    return r.get("elements", r.get("rooms", r.get("items", [])))


def _get_param(element_id, param_name):
    r = _call("revit.get_parameter_value", {"element_id": element_id, "parameter_name": param_name})
    if r is None:
        return None
    return r.get("value")


def _material_quantities(category):
    """Returns {material_name: volume_cf}"""
    r = _call("revit.calculate_material_quantities", {"category": category})
    if r is None:
        return {}
    return {t["material"]: t["volume_cf"] for t in r.get("totals", [])}


def _count_by_family(elements):
    """Count elements grouped by family + type."""
    counts = {}
    for e in elements:
        key = e.get("family_name", e.get("type", "Unknown"))
        type_name = e.get("type_name", e.get("type", ""))
        label = f"{key} — {type_name}" if type_name and type_name != key else key
        counts[label] = counts.get(label, 0) + 1
    return counts


def run_takeoffs():
    print("\n📋 Running full takeoff — this may take 30–60 seconds...\n")

    sections = []

    # ── 1. AREA SCHEDULE ────────────────────────────────────────────────────
    print("  [1/10] Room areas...")
    rooms = _list_elements("Rooms")
    area_by_type = {}
    for room in rooms:
        name = room.get("name", "")
        area = room.get("area_sf", 0) or 0
        if area < 5:
            continue
        # Group by room type
        rtype = room.get("room_type") or name.split(" ")[0] if name else "Other"
        area_by_type[rtype] = area_by_type.get(rtype, 0) + area

    area_lines = [f"  {k}: {v:,.0f} SF" for k, v in sorted(area_by_type.items())]
    total_area = sum(area_by_type.values())
    area_lines.append(f"  TOTAL: {total_area:,.0f} SF")
    sections.append(("AREA SCHEDULE", area_lines))

    # ── 2. FLOORS ───────────────────────────────────────────────────────────
    print("  [2/10] Floor areas...")
    floor_mats = _material_quantities("Floors")
    floor_lines = []
    floor_total = 0
    for mat, vol in sorted(floor_mats.items(), key=lambda x: -x[1]):
        # Estimate SF from volume — floors are typically 4" thick (0.333 ft)
        sf = vol / 0.333
        floor_total += sf
        floor_lines.append(f"  {mat}: {sf:,.0f} SF")
    if floor_lines:
        floor_lines.append(f"  TOTAL: {floor_total:,.0f} SF")
    else:
        floor_lines = ["  (no floor material data found)"]
    sections.append(("FLOOR SCHEDULE", floor_lines))

    # ── 3. WALLS ────────────────────────────────────────────────────────────
    print("  [3/10] Walls...")
    walls = _list_elements("Walls")
    wall_by_type = {}
    for w in walls:
        wtype = w.get("type", w.get("wall_type", "Unknown"))
        length = w.get("length_ft", 0) or 0
        wall_by_type[wtype] = wall_by_type.get(wtype, 0) + length
    wall_lines = [f"  {k}: {v:,.1f} LF" for k, v in sorted(wall_by_type.items())]
    sections.append(("WALL SCHEDULE", wall_lines))

    # ── 4. ROOF ─────────────────────────────────────────────────────────────
    print("  [4/10] Roof...")
    roof_mats = _material_quantities("Roofs")
    roof_total_cf = sum(roof_mats.values())
    # Roofs are typically 1.5" metal deck + insulation — use 6" avg = 0.5 ft
    roof_sf = roof_total_cf / 0.5 if roof_total_cf > 0 else 0
    # Fallback: count roof elements
    roofs = _list_elements("Roofs")
    roof_lines = []
    if roof_sf > 100:
        roof_lines.append(f"  Roof Area (est): {roof_sf:,.0f} SF")
    roof_lines.append(f"  Roof Elements: {len(roofs)}")
    for mat, vol in sorted(roof_mats.items(), key=lambda x: -x[1]):
        roof_lines.append(f"  {mat}: {vol:,.1f} CF material")
    sections.append(("ROOF SCHEDULE", roof_lines))

    # ── 5. CEILINGS ─────────────────────────────────────────────────────────
    print("  [5/10] Ceilings...")
    ceiling_mats = _material_quantities("Ceilings")
    ceiling_lines = []
    ceiling_total = 0
    for mat, vol in sorted(ceiling_mats.items(), key=lambda x: -x[1]):
        sf = vol / (0.625 / 12)  # 5/8" ceiling drywall
        ceiling_total += sf
        ceiling_lines.append(f"  {mat}: {sf:,.0f} SF")
    if ceiling_lines:
        ceiling_lines.append(f"  TOTAL: {ceiling_total:,.0f} SF")
    else:
        ceilings = _list_elements("Ceilings")
        ceiling_lines = [f"  Ceiling Elements: {len(ceilings)}"]
    sections.append(("CEILING SCHEDULE", ceiling_lines))

    # ── 6. GYPSUM / STUCCO / STONE ──────────────────────────────────────────
    print("  [6/10] Wall materials (gypsum, stucco, stone)...")
    wall_mats = _material_quantities("Walls")
    gyp_lines = []
    stucco_lines = []
    stone_lines = []

    for mat, vol in sorted(wall_mats.items(), key=lambda x: -x[1]):
        mat_lower = mat.lower()
        if any(k in mat_lower for k in ["gypsum", "drywall", "gwb", "gyp board"]):
            sf = vol * CF_TO_SF_GYPSUM
            gyp_lines.append(f"  {mat}: {sf:,.0f} SF")
        elif any(k in mat_lower for k in ["stucco", "plaster", "eifs"]):
            sf = vol * CF_TO_SF_STUCCO
            stucco_lines.append(f"  {mat}: {sf:,.0f} SF")
        elif any(k in mat_lower for k in ["stone", "brick", "veneer", "masonry"]):
            sf = vol / (0.333)  # ~4" stone
            stone_lines.append(f"  {mat}: {sf:,.0f} SF")

    if not gyp_lines:
        gyp_lines = ["  (no gypsum materials found — check wall material assignments)"]
    if not stucco_lines:
        stucco_lines = ["  (no stucco materials found)"]

    sections.append(("GYPSUM (WALLS)", gyp_lines))
    sections.append(("STUCCO / EXTERIOR FINISH (WALLS)", stucco_lines))
    if stone_lines:
        sections.append(("STONE / MASONRY (WALLS)", stone_lines))

    # ── 7. DOORS ────────────────────────────────────────────────────────────
    print("  [7/10] Doors...")
    doors = _list_elements("Doors")
    door_counts = _count_by_family(doors)
    door_lines = [f"  {k}: {v}" for k, v in sorted(door_counts.items())]
    door_lines.append(f"  TOTAL: {len(doors)}")
    sections.append(("DOOR SCHEDULE", door_lines))

    # ── 8. WINDOWS ──────────────────────────────────────────────────────────
    print("  [8/10] Windows...")
    windows = _list_elements("Windows")
    win_counts = _count_by_family(windows)
    win_lines = [f"  {k}: {v}" for k, v in sorted(win_counts.items())]
    win_lines.append(f"  TOTAL: {len(windows)}")
    sections.append(("WINDOW SCHEDULE", win_lines))

    # ── 9. CASEWORK / CABINETS ──────────────────────────────────────────────
    print("  [9/10] Casework, plumbing, electrical...")
    casework = _list_elements("Casework")
    cab_counts = _count_by_family(casework)
    cab_lines = [f"  {k}: {v}" for k, v in sorted(cab_counts.items())]
    cab_lines.append(f"  TOTAL: {len(casework)}")
    sections.append(("CABINET SCHEDULE", cab_lines))

    # ── 10. PLUMBING ────────────────────────────────────────────────────────
    plumbing = _list_elements("Plumbing Fixtures")
    plumb_counts = _count_by_family(plumbing)
    plumb_lines = [f"  {k}: {v}" for k, v in sorted(plumb_counts.items())]
    plumb_lines.append(f"  TOTAL: {len(plumbing)}")
    sections.append(("PLUMBING FIXTURE SCHEDULE", plumb_lines))

    # ── ELECTRICAL ──────────────────────────────────────────────────────────
    elec = _list_elements("Electrical Fixtures")
    elec_counts = _count_by_family(elec)
    elec_lines = [f"  {k}: {v}" for k, v in sorted(elec_counts.items())]
    elec_lines.append(f"  TOTAL: {len(elec)}")
    sections.append(("ELECTRICAL FIXTURE SCHEDULE", elec_lines))

    # ── EQUIPMENT / APPLIANCES ──────────────────────────────────────────────
    equip = _list_elements("Specialty Equipment")
    if not equip:
        equip = _list_elements("Mechanical Equipment")
    equip_counts = _count_by_family(equip)
    if equip_counts:
        equip_lines = [f"  {k}: {v}" for k, v in sorted(equip_counts.items())]
        equip_lines.append(f"  TOTAL: {len(equip)}")
        sections.append(("EQUIPMENT SCHEDULE", equip_lines))

    # ── FORMAT OUTPUT ────────────────────────────────────────────────────────
    print("\n" + "═" * 55)
    print("  TAKEOFF REPORT")
    print("═" * 55)
    for title, lines in sections:
        print(f"\n▸ {title}")
        for line in lines:
            print(line)
    print("\n" + "═" * 55)

    # Save to JSON
    result = {section: lines for section, lines in sections}
    with open("takeoff_report.json", "w") as f:
        json.dump(result, f, indent=2)
    print("💾 Saved to takeoff_report.json")

    return result
