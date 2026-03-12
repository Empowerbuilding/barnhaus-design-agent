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
    "mech":        "Laundry Room", # HVAC/utility — won't trigger validation error
    "mud_room":    "Mudroom",
    "garage":      "Garage",
    "hallway1":    "Foyer",
    "hallway2":    "Foyer",
}

# ── Zone mapping ──────────────────────────────────────────────────────────────
# Carter zone integers → Barnhaus zone strings
ZONE_MAP = {
    0: "master",
    1: "beds",
    2: "living",
    3: "service",
    4: "service",  # garage
}


# ── Adapter ───────────────────────────────────────────────────────────────────

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


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys
    if len(sys.argv) < 2:
        print("Usage: python3 carter_adapter.py <carter_export.json> [living_sf]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        export = json.load(f)

    sf = int(sys.argv[2]) if len(sys.argv) > 2 else CARTER_LIVING_SF
    scale = get_scale(export, sf)
    print(f"Scale: {scale:.4f} px/ft")

    coords = carter_to_room_coords(export, sf)
    print(f"\nRoom coords ({len(coords)} rooms):")
    for name, rc in coords.items():
        print(f"  {name:20s}  ({rc['x0']:.1f},{rc['y0']:.1f})->({rc['x1']:.1f},{rc['y1']:.1f})  {rc['sf']} SF  zone={rc['zone']}")
