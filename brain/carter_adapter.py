#!/usr/bin/env python3
"""
carter_adapter.py — Convert Carter Canvas export JSON to Barnhaus room_coords format.

Usage:
    from carter_adapter import carter_to_room_coords
    room_coords = carter_to_room_coords(carter_export, living_sf=2823)
    # Then pipe into validate_layout() + generate_floorplan_image()
"""

import math

# ── Scale ─────────────────────────────────────────────────────────────────────
# Empirically derived from Carter V4 reference positions
# 348945 px² total living area / 2823 SF = 11.12 px/ft
CARTER_LIVING_SF = 2823
CARTER_LIVING_PX2 = 348945  # sum of all non-garage box areas at V4


def get_scale(carter_export: dict, living_sf: int = CARTER_LIVING_SF) -> float:
    """Compute px/ft scale dynamically from a Carter export."""
    living_px2 = sum(
        b["w"] * b["h"] for b in carter_export.get("boxes", [])
        if b.get("id") != "garage"
    )
    if living_px2 == 0:
        return math.sqrt(CARTER_LIVING_PX2 / living_sf)
    return math.sqrt(living_px2 / living_sf)


# ── Room name mapping ─────────────────────────────────────────────────────────
# Carter snake_case IDs → Barnhaus display names (must match validate_layout())
CARTER_TO_BARNHAUS = {
    "master_bed":  "Master Bedroom",
    "m_bath":      "Master Bathroom",
    "his_closet":  "His Closet",
    "hers_closet": "Hers Closet",
    "bed1":        "Bedroom 2",
    "bed2":        "Bedroom 3",
    "bath1":       "Bathroom 2",
    "bath2":       "Bathroom 3",
    "wic1":        "WIC 1",        # unknown to validate_layout — skipped
    "wic2":        "WIC 2",        # unknown to validate_layout — skipped
    "half_bath":   "Half Bath",    # unknown to validate_layout — skipped
    "great_room":  "Great Room",
    "office":      "Office",
    "pantry":      "Pantry",
    # "mech" intentionally omitted — HVAC/utility has no Barnhaus equivalent
    "mud_room":    "Mudroom",
    "garage":      "Garage",
    "hallway1":    "Foyer",
    # hallway2 intentionally omitted — secondary hallway, derived from circulation not passed as room
}

# ── Zone mapping ──────────────────────────────────────────────────────────────
# Carter zone integers → Barnhaus zone strings
ZONE_MAP = {
    0: "master",
    1: "beds",
    2: "living",
    3: "service",
    4: "service",  # garage — kept as service so Barnhaus zone logic handles it
}

# Override zones for specific rooms regardless of bubble zone
ROOM_ZONE_OVERRIDES = {
    "Garage": "service",
    "Mudroom": "service",
}


# ── Adapter ───────────────────────────────────────────────────────────────────

def _build_bubble_zone_map(carter_export: dict) -> dict:
    """Build id → zone string lookup from bubbles (zone lives on bubbles, not boxes)."""
    result = {}
    for b in carter_export.get("bubbles", []):
        bid = b.get("id")
        zone_int = b.get("zone", 2)
        if bid:
            result[bid] = ZONE_MAP.get(zone_int, "living")
    return result


def _coords_with_scale(carter_export: dict, scale: float) -> dict:
    """Internal: convert Carter export using a pre-computed scale."""
    bubble_zones = _build_bubble_zone_map(carter_export)
    room_coords = {}
    boxes = carter_export.get("boxes", [])
    h1 = carter_export.get("hallway1")
    if h1 and isinstance(h1, dict) and h1.get("id"):
        boxes = boxes + [h1]
    for box in boxes:
        bid = box.get("id")
        if not bid:
            continue
        name = CARTER_TO_BARNHAUS.get(bid)
        if name is None:
            continue  # omit unmapped rooms (e.g. mech)
        zone = ROOM_ZONE_OVERRIDES.get(name) or bubble_zones.get(bid) or ZONE_MAP.get(box.get("zone", 2), "living")
        room_coords[name] = {
            "x0": round(box["x"] / scale, 1),
            "y0": round(box["y"] / scale, 1),
            "x1": round((box["x"] + box["w"]) / scale, 1),
            "y1": round((box["y"] + box["h"]) / scale, 1),
            "sf": round((box["w"] / scale) * (box["h"] / scale)),
            "zone": zone,
        }

    # Sub-room correction: subtract Office SF from Great Room if both present
    # (Office is a sub-bubble inside GR on Carter canvas)
    SUB_ROOMS = {"Office": "Great Room"}
    for sub, parent in SUB_ROOMS.items():
        if sub in room_coords and parent in room_coords:
            room_coords[parent]["sf"] = max(
                0, room_coords[parent]["sf"] - room_coords[sub]["sf"]
            )

    return room_coords


def carter_to_room_coords(carter_export: dict, living_sf: int = CARTER_LIVING_SF) -> dict:
    """Convert Carter Canvas export to Barnhaus room_coords dict.

    Args:
        carter_export: dict from Carter export JSON (must have "boxes" key)
        living_sf: actual living SF for scale calibration (default: Carter = 2823)

    Returns:
        room_coords dict compatible with validate_layout() + generate_floorplan_image()
    """
    scale = get_scale(carter_export, living_sf)

    room_coords = {}

    # Main boxes
    boxes = carter_export.get("boxes", [])

    # Also include hallway1 if present at top level
    h1 = carter_export.get("hallway1")
    if h1 and isinstance(h1, dict) and h1.get("id"):
        boxes = boxes + [h1]

    for box in boxes:
        if not box.get("id"):
            continue

        name = CARTER_TO_BARNHAUS.get(box["id"], box["id"])
        x0 = round(box["x"] / scale, 1)
        y0 = round(box["y"] / scale, 1)
        x1 = round((box["x"] + box["w"]) / scale, 1)
        y1 = round((box["y"] + box["h"]) / scale, 1)
        sf = round((box["w"] / scale) * (box["h"] / scale))
        zone = ZONE_MAP.get(box.get("zone", 2), "living")

        room_coords[name] = {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "sf": sf,
            "zone": zone,
        }

    return room_coords


# ── CLI ───────────────────────────────────────────────────────────────────────

def measure_scale(pairs: list[tuple[float, float]]) -> float:
    """Compute scale from (pixels, feet) measurement pairs.

    Prints each measurement and warns if spread > 0.15 px/ft.
    Returns average scale.
    """
    scales = []
    for px, ft in pairs:
        s = px / ft
        scales.append(s)
        print(f"  {px:.0f}px / {ft:.1f}ft = {s:.4f} px/ft")
    avg = sum(scales) / len(scales)
    spread = max(scales) - min(scales)
    print(f"  Average: {avg:.4f} px/ft  |  Spread: {spread:.4f} px/ft", end="")
    if spread > 0.15:
        print("  ⚠️  spread > 0.15 — check measurements or mixed-scale sheets")
    else:
        print("  ✅ locked")
    return avg


if __name__ == "__main__":
    import json, sys

    args = sys.argv[1:]

    # Mode 1: --measure px1 ft1 px2 ft2 ...
    if "--measure" in args:
        idx = args.index("--measure")
        pairs_flat = args[idx + 1:]
        if len(pairs_flat) % 2 != 0 or len(pairs_flat) < 2:
            print("Usage: --measure px1 ft1 px2 ft2 ...")
            sys.exit(1)
        pairs = [(float(pairs_flat[i]), float(pairs_flat[i+1]))
                 for i in range(0, len(pairs_flat), 2)]
        print("Scale measurement:")
        scale = measure_scale(pairs)
        sys.exit(0)

    if not args:
        print("Usage:")
        print("  python3 carter_adapter.py carter_export.json [--scale 11.13]")
        print("  python3 carter_adapter.py carter_export.json 2823")
        print("  python3 carter_adapter.py --measure 578 52 356 32 267 24")
        sys.exit(1)

    with open(args[0]) as f:
        export = json.load(f)

    # Mode 2: --scale override
    if "--scale" in args:
        scale = float(args[args.index("--scale") + 1])
        print(f"Scale (manual): {scale:.4f} px/ft")
        coords = _coords_with_scale(export, scale)
    else:
        # Mode 3: SF derivation
        sf = int(args[1]) if len(args) > 1 else CARTER_LIVING_SF
        scale = get_scale(export, sf)
        print(f"Scale (SF-derived, {sf} SF): {scale:.4f} px/ft")
        coords = carter_to_room_coords(export, sf)

    print(f"\nRoom coords ({len(coords)} rooms):")
    for name, rc in coords.items():
        print(f"  {name:20s}  ({rc['x0']:.1f},{rc['y0']:.1f})->({rc['x1']:.1f},{rc['y1']:.1f})  {rc['sf']} SF  zone={rc['zone']}")
