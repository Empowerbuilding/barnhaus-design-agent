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


def extract_section_lines(carter_export: dict, scale: float) -> list:
    """Extract section lines from Carter export and convert px → ft."""
    lines = []
    for sl in carter_export.get("sections", []):
        sid = sl.get("id", "")
        axis = sl.get("axis", "NS")
        entry = {"id": sid, "axis": axis}
        if axis == "NS":
            entry["x"] = round(sl.get("x", 0) / scale, 1)
        else:
            entry["y"] = round(sl.get("y", 0) / scale, 1)
        lines.append(entry)
    return lines


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
    "hallway2":    "Hallway 2",
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
    if h1 and isinstance(h1, dict):
        if not h1.get("id"):
            h1 = {**h1, "id": "hallway1"}
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

    # Overlap nudge: if two rooms overlap, shrink the smaller one to eliminate shared area
    names = list(room_coords.keys())
    for i, a in enumerate(names):
        for b in names[i+1:]:
            ra, rb = room_coords[a], room_coords[b]
            ox0 = max(ra["x0"], rb["x0"])
            ox1 = min(ra["x1"], rb["x1"])
            oy0 = max(ra["y0"], rb["y0"])
            oy1 = min(ra["y1"], rb["y1"])
            if ox1 > ox0 and oy1 > oy0:
                # Overlap exists — nudge smaller room
                smaller = a if room_coords[a]["sf"] <= room_coords[b]["sf"] else b
                larger = b if smaller == a else a
                rs, rl = room_coords[smaller], room_coords[larger]
                # Push smaller room away on the axis with least overlap
                x_overlap = ox1 - ox0
                y_overlap = oy1 - oy0
                if x_overlap <= y_overlap:
                    if rs["x0"] < rl["x0"]:
                        room_coords[smaller]["x1"] = rl["x0"]
                    else:
                        room_coords[smaller]["x0"] = rl["x1"]
                else:
                    if rs["y0"] < rl["y0"]:
                        room_coords[smaller]["y1"] = rl["y0"]
                    else:
                        room_coords[smaller]["y0"] = rl["y1"]

    # Compute adjacencies geometrically — rooms are adjacent if edges within 1.5ft
    names = list(room_coords.keys())
    for name in names:
        room_coords[name]["adjacencies"] = []
    EDGE_THRESHOLD = 2.0  # ft — rooms within this distance count as adjacent
    for i, a in enumerate(names):
        for b in names[i+1:]:
            ra, rb = room_coords[a], room_coords[b]
            h_overlap = ra["x0"] < rb["x1"] and ra["x1"] > rb["x0"]
            v_overlap = ra["y0"] < rb["y1"] and ra["y1"] > rb["y0"]
            v_edge = min(abs(ra["y1"] - rb["y0"]), abs(rb["y1"] - ra["y0"])) < EDGE_THRESHOLD
            h_edge = min(abs(ra["x1"] - rb["x0"]), abs(rb["x1"] - ra["x0"])) < EDGE_THRESHOLD
            # Containment check: if one room is fully inside the other, treat as adjacent
            a_inside_b = (rb["x0"] <= ra["x0"] and ra["x1"] <= rb["x1"] and
                          rb["y0"] <= ra["y0"] and ra["y1"] <= rb["y1"])
            b_inside_a = (ra["x0"] <= rb["x0"] and rb["x1"] <= ra["x1"] and
                          ra["y0"] <= rb["y0"] and rb["y1"] <= ra["y1"])
            if (h_overlap and v_edge) or (v_overlap and h_edge) or a_inside_b or b_inside_a:
                room_coords[a]["adjacencies"].append(b)
                room_coords[b]["adjacencies"].append(a)

    # GR sub-room splitter: if Kitchen/Dining/Living missing, derive positions
    # Prefer gr_labels from Carter export (accurate drag positions) over proportional split
    if "Great Room" in room_coords and "Kitchen" not in room_coords:
        gr = room_coords["Great Room"]
        gx0, gy0, gx1, gy1 = gr["x0"], gr["y0"], gr["x1"], gr["y1"]
        gw = gx1 - gx0
        gh = gy1 - gy0
        gr_labels = carter_export.get("gr_labels", [])
        label_map = {l["id"]: l for l in gr_labels}
        if label_map:
            # Use cx/cy as position guides to proportionally partition the GR box
            # Bubble radius is spatial intent, not dimension — partition by centroid position
            GR_LABEL_NAMES = {"kitchen": "Kitchen", "dining": "Dining Room", "living": "Living Room"}
            # Determine split axes from centroids relative to GR box (in px)
            # Strategy: find median cx to split left/right, median cy to split top/bottom
            labels_present = {lid: label_map[lid] for lid in GR_LABEL_NAMES if lid in label_map}
            if labels_present:
                # Get GR box in px
                gr_px_x0 = gr["x0"] * scale
                gr_px_y0 = gr["y0"] * scale
                gr_px_x1 = gr["x1"] * scale
                gr_px_y1 = gr["y1"] * scale
                gr_pw = gr_px_x1 - gr_px_x0
                gr_ph = gr_px_y1 - gr_px_y0
                # Sort labels by cx to find left/right split
                sorted_by_x = sorted(labels_present.values(), key=lambda l: l["cx"])
                # If 3 labels: living=left, kitchen=upper-right, dining=lower-right
                # Use cx of rightmost label group vs leftmost as split
                if len(sorted_by_x) >= 2:
                    split_x_px = (sorted_by_x[0]["cx"] + sorted_by_x[1]["cx"]) / 2
                    split_x = round(split_x_px / scale, 1)
                else:
                    split_x = round(gr["x0"] + (gr["x1"] - gr["x0"]) * 0.5, 1)
                # For kitchen/dining vertical split: use their cy midpoint
                k = labels_present.get("kitchen")
                d = labels_present.get("dining")
                if k and d:
                    split_y = round(((k["cy"] + d["cy"]) / 2) / scale, 1)
                else:
                    split_y = round(gr["y0"] + (gr["y1"] - gr["y0"]) * 0.45, 1)
                # Assign boxes: living = left half, kitchen = upper-right, dining = lower-right
                if "living" in labels_present:
                    room_coords["Living Room"] = {
                        "x0": gr["x0"], "y0": gr["y0"], "x1": split_x, "y1": gr["y1"],
                        "sf": round((split_x - gr["x0"]) * (gr["y1"] - gr["y0"])),
                        "zone": "living", "adjacencies": ["Great Room", "Kitchen", "Dining Room"]
                    }
                if "kitchen" in labels_present:
                    room_coords["Kitchen"] = {
                        "x0": split_x, "y0": gr["y0"], "x1": gr["x1"], "y1": split_y,
                        "sf": round((gr["x1"] - split_x) * (split_y - gr["y0"])),
                        "zone": "living", "adjacencies": ["Great Room", "Dining Room", "Living Room"]
                    }
                if "dining" in labels_present:
                    room_coords["Dining Room"] = {
                        "x0": split_x, "y0": split_y, "x1": gr["x1"], "y1": gr["y1"],
                        "sf": round((gr["x1"] - split_x) * (gr["y1"] - split_y)),
                        "zone": "living", "adjacencies": ["Great Room", "Kitchen", "Living Room"]
                    }
                room_coords["Great Room"].setdefault("adjacencies", [])
                room_coords["Great Room"]["adjacencies"] += [
                    n for lid, n in GR_LABEL_NAMES.items() if lid in label_map
                ]
                # Shrink GR to left portion only (living zone)
                room_coords["Great Room"]["x1"] = split_x
                room_coords["Great Room"]["sf"] = round((split_x - gr["x0"]) * (gr["y1"] - gr["y0"]))
        else:
            # Fallback: proportional split from GR box
            mid_x = round(gx0 + gw * 0.5, 1)
            mid_y = round(gy0 + gh * 0.45, 1)
            room_coords["Kitchen"] = {
                "x0": mid_x, "y0": gy0, "x1": gx1, "y1": mid_y,
                "sf": round((gx1 - mid_x) * (mid_y - gy0)), "zone": "living",
                "adjacencies": ["Great Room", "Dining Room"]
            }
            room_coords["Dining Room"] = {
                "x0": mid_x, "y0": mid_y, "x1": gx1, "y1": gy1,
                "sf": round((gx1 - mid_x) * (gy1 - mid_y)), "zone": "living",
                "adjacencies": ["Great Room", "Kitchen"]
            }
            room_coords["Great Room"].setdefault("adjacencies", [])
            room_coords["Great Room"]["adjacencies"] += ["Kitchen", "Dining Room"]
            room_coords["Great Room"]["x1"] = mid_x
            room_coords["Great Room"]["sf"] = round((mid_x - gx0) * gh)

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
    return _coords_with_scale(carter_export, scale)


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
