#!/usr/bin/env python3
"""
barnhaus_planner.py — Pre-Revit design planning tool for Barnhaus Steel Builders.

Validates layouts, solves footprints, assigns rooms to zones,
generates floor plan images, and uploads to Supabase.
"""

import json
import math
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import requests

# ── Room sizing norms (from HOME_LAYOUT.md Section 3) ────────────────────────

ROOM_NORMS = {
    "Master Bedroom":      {"min": 200, "target_lo": 240, "target_hi": 320, "max": 400},
    "Master Bathroom":     {"min": 100, "target_lo": 140, "target_hi": 200, "max": 280},
    "Master Bath":         {"min": 100, "target_lo": 140, "target_hi": 200, "max": 280},
    "His Closet":          {"min": 35,  "target_lo": 60,  "target_hi": 80,  "max": 120},
    "Hers Closet":         {"min": 50,  "target_lo": 80,  "target_hi": 120, "max": 180},
    "Master Closet":       {"min": 40,  "target_lo": 60,  "target_hi": 120, "max": 180},
    "Master Sitting Room": {"min": 80,  "target_lo": 100, "target_hi": 140, "max": 200},
    "Bedroom":             {"min": 110, "target_lo": 130, "target_hi": 180, "max": 220},
    "Bathroom":            {"min": 40,  "target_lo": 90,  "target_hi": 120, "max": 160},
    "Great Room":          {"min": 280, "target_lo": 400, "target_hi": 700, "max": 1400},
    "Kitchen":             {"min": 180, "target_lo": 220, "target_hi": 320, "max": 420},
    "Dining Room":         {"min": 100, "target_lo": 150, "target_hi": 280, "max": 400},
    "Dining":              {"min": 100, "target_lo": 150, "target_hi": 280, "max": 400},
    "Office":              {"min": 120, "target_lo": 160, "target_hi": 220, "max": 300},
    "Bonus Room":          {"min": 150, "target_lo": 180, "target_hi": 280, "max": 380},
    "Butler Pantry":       {"min": 60,  "target_lo": 80,  "target_hi": 120, "max": 160},
    "Pantry":              {"min": 40,  "target_lo": 60,  "target_hi": 120, "max": 160},
    "Mudroom":             {"min": 60,  "target_lo": 80,  "target_hi": 120, "max": 160},
    "Laundry":             {"min": 60,  "target_lo": 80,  "target_hi": 100, "max": 140},
    "Laundry Room":        {"min": 60,  "target_lo": 80,  "target_hi": 100, "max": 140},
    "Foyer":               {"min": 48,  "target_lo": 48,  "target_hi": 100, "max": 150},
    "Garage":              {"min": 240, "target_lo": 280, "target_hi": 560, "max": 840},
    "Outdoor Living":      {"min": 100, "target_lo": 200, "target_hi": 400, "max": 600},
    "Porch":               {"min": 100, "target_lo": 200, "target_hi": 400, "max": 600},
}

# ── Adjacency rules (from HOME_LAYOUT.md Section 4) ──────────────────────────

MUST_TOUCH = {
    "Master Bedroom":  ["Master Bathroom", "Master Bath", "Master Closet",
                        "His Closet", "Hers Closet"],
    "Master Bathroom": ["Master Bedroom"],
    "Master Bath":     ["Master Bedroom"],
    "His Closet":      ["Master Bedroom", "Master Bathroom", "Master Bath"],
    "Hers Closet":     ["Master Bedroom", "Master Bathroom", "Master Bath"],
    "Master Closet":   ["Master Bedroom", "Master Bathroom", "Master Bath"],
    "Great Room":      ["Dining Room", "Dining", "Kitchen"],
    "Kitchen":         ["Dining Room", "Dining", "Pantry", "Butler Pantry"],
    "Butler Pantry":   ["Kitchen"],
    "Mudroom":         ["Garage"],
    "Garage":          ["Mudroom"],
}

MUST_NOT_TOUCH = {
    "Master Bedroom":  ["Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5",
                        "Garage"],
    "Master Bathroom": ["Kitchen", "Garage"],
    "Master Bath":     ["Kitchen", "Garage"],
    "Great Room":      ["Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5"],
    "Kitchen":         ["Master Bathroom", "Master Bath",
                        "Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5"],
    "Garage":          ["Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5",
                        "Master Bedroom", "Master Bathroom", "Master Bath"],
}

# ── Zone classification ───────────────────────────────────────────────────────

ZONE_MAP = {
    "master":  ["Master Bedroom", "Master Bathroom", "Master Bath",
                "Master Closet", "His Closet", "Hers Closet",
                "Master Sitting Room"],
    "living":  ["Great Room", "Kitchen", "Dining Room", "Dining",
                "Foyer", "Office", "Study"],
    "beds":    ["Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5",
                "Bathroom 2", "Bathroom 3", "Bathroom 4", "Bonus Room"],
    "service": ["Garage", "Mudroom", "Laundry", "Laundry Room",
                "Pantry", "Butler Pantry"],
    "porch":   ["Outdoor Living", "Porch", "Covered Porch", "Patio"],
}

ZONE_COLORS = {
    "master":  "#4A90D9",
    "living":  "#E8943A",
    "beds":    "#5CB85C",
    "service": "#AAAAAA",
    "porch":   "#F0D060",
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_zone(room_name: str) -> str:
    """Classify a room name into a zone."""
    for zone, rooms in ZONE_MAP.items():
        if room_name in rooms:
            return zone
    low = room_name.lower()
    if "master" in low:
        return "master"
    if any(kw in low for kw in ("bedroom", "bed ")):
        return "beds"
    if any(kw in low for kw in ("bathroom", "bath ")):
        return "beds"
    if any(kw in low for kw in ("garage", "mudroom", "laundry", "pantry")):
        return "service"
    if any(kw in low for kw in ("porch", "outdoor", "patio", "courtyard")):
        return "porch"
    if any(kw in low for kw in ("great", "kitchen", "dining", "foyer",
                                "office", "entry", "living")):
        return "living"
    return "living"


def _get_norm(room_name: str) -> dict | None:
    """Look up sizing norm for a room, with fuzzy fallback."""
    if room_name in ROOM_NORMS:
        return ROOM_NORMS[room_name]
    low = room_name.lower()
    if "master" in low and "bed" in low:
        return ROOM_NORMS["Master Bedroom"]
    if "master" in low and "bath" in low:
        return ROOM_NORMS["Master Bathroom"]
    if "master" in low and "closet" in low:
        return ROOM_NORMS["Master Closet"]
    if "bedroom" in low or low.startswith("bed "):
        return ROOM_NORMS["Bedroom"]
    if "bathroom" in low or low.startswith("bath "):
        return ROOM_NORMS["Bathroom"]
    for key in ("Garage", "Outdoor Living", "Laundry", "Pantry", "Mudroom",
                "Foyer", "Dining Room", "Kitchen", "Great Room"):
        if key.lower().split()[0] in low:
            return ROOM_NORMS[key]
    return None


def _parse_brief(brief: str) -> dict:
    """Extract structured data from the brief text."""
    info: dict = {}
    m = re.search(r"(\d[\d,]*)\s*SF", brief, re.IGNORECASE)
    if m:
        info["total_sf"] = int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+)\s*bed", brief, re.IGNORECASE)
    if m:
        info["bed_count"] = int(m.group(1))
    for shape in ("h-shape", "u-shape", "l-shape", "rectangle"):
        if shape in brief.lower():
            info["house_shape"] = shape.replace("-", "_")
            break
    if "house_shape" not in info:
        m = re.search(r"Footprint:\s*(\S+)", brief, re.IGNORECASE)
        if m:
            info["house_shape"] = m.group(1).lower().replace("-", "_")
    if any(k in brief.lower() for k in ("two-story", "2-story", "2 story")):
        info["stories"] = 2
    else:
        info["stories"] = 1
    m = re.search(r"(\d)-car", brief, re.IGNORECASE)
    if m:
        info["garage_cars"] = int(m.group(1))
    return info


# ══════════════════════════════════════════════════════════════════════════════
#  1. validate_layout
# ══════════════════════════════════════════════════════════════════════════════

def validate_layout(layout_json: dict, intake_json: dict) -> list[str]:
    """Check layout against Barnhaus design rules.

    Returns a list of human-readable violation strings (empty = pass).
    """
    violations: list[str] = []
    brief_info = _parse_brief(intake_json.get("brief", ""))
    rooms = {r["name"]: r for r in layout_json.get("rooms", [])}

    # ── Required rooms present ──
    bed_count = brief_info.get("bed_count", 0)
    desired = ["Great Room", "Kitchen", "Master Bedroom"]
    for i in range(2, bed_count + 1):
        desired.append(f"Bedroom {i}")
    for d in desired:
        if d not in rooms:
            if not any(d.lower() in rn.lower() for rn in rooms):
                violations.append(f"Missing required room: {d}")

    # ── SF within norms ──
    for rname, rdata in rooms.items():
        norm = _get_norm(rname)
        if norm and "sf" in rdata:
            sf = rdata["sf"]
            if sf < norm["min"]:
                violations.append(
                    f"{rname}: {sf} SF below minimum ({norm['min']} SF)")
            elif sf > norm["max"]:
                violations.append(
                    f"{rname}: {sf} SF exceeds maximum ({norm['max']} SF)")

    # ── Adjacency: must-touch ──
    for rname, rdata in rooms.items():
        adj_list = rdata.get("adjacencies", [])
        if rname in MUST_TOUCH:
            required_any = [r for r in MUST_TOUCH[rname] if r in rooms]
            if required_any and not any(r in adj_list for r in required_any):
                violations.append(
                    f"Adjacency: {rname} must touch one of "
                    f"{[r for r in required_any]}")

    # ── Adjacency: must-not-touch ──
    for rname, rdata in rooms.items():
        adj_list = rdata.get("adjacencies", [])
        if rname in MUST_NOT_TOUCH:
            for forbidden in MUST_NOT_TOUCH[rname]:
                if forbidden in adj_list:
                    violations.append(
                        f"Adjacency: {rname} must NOT touch {forbidden}")

    # ── Master at dead end (no secondary bed adjacency) ──
    if "Master Bedroom" in rooms:
        for adj in rooms["Master Bedroom"].get("adjacencies", []):
            if re.match(r"Bedroom \d", adj):
                violations.append(
                    f"Master must be at dead end — adjacent to {adj}")

    # ── Kitchen must touch dining ──
    if "Kitchen" in rooms:
        k_adj = rooms["Kitchen"].get("adjacencies", [])
        if not any("dining" in a.lower() for a in k_adj):
            violations.append("Kitchen must be adjacent to Dining")

    return violations


# ══════════════════════════════════════════════════════════════════════════════
#  2. solve_footprint
# ══════════════════════════════════════════════════════════════════════════════

def solve_footprint(layout_json: dict, intake_json: dict) -> dict:
    """Given total SF + house_shape, return footprint with polygon perimeter,
    named zones, bumpouts, and overall dimensions.

    Returns:
        {
            "polygon": [{"x": N, "y": N}, ...],   # full exterior perimeter CCW
            "zones": {
                "master": {"x0":N,"y0":N,"x1":N,"y1":N},
                "living_core": {"x0":N,"y0":N,"x1":N,"y1":N},
                "bed_wing": {"x0":N,"y0":N,"x1":N,"y1":N},
                "service": {"x0":N,"y0":N,"x1":N,"y1":N},
                "garage": {"x0":N,"y0":N,"x1":N,"y1":N},
            },
            "bumpouts": [...],
            "total_sf": N,
            "width": N,
            "depth": N,
            # Legacy compat fields
            "shape": str,
            "total_width": N,
            "total_depth": N,
        }
    """
    brief_info = _parse_brief(intake_json.get("brief", ""))
    total_sf = int(intake_json.get("living") or brief_info.get("total_sf", 2500))
    shape = (intake_json.get("house_shape") or brief_info.get("house_shape") or
             layout_json.get("footprint", "rectangle")).lower()
    garage_cars = int(intake_json.get("garage_cars") or brief_info.get("garage_cars", 2))
    master_location = intake_json.get("master_location") or layout_json.get("master_location")

    garage_w = {1: 14, 2: 24, 3: 34}.get(garage_cars, 24)
    garage_d = 24

    solvers = {
        "rectangle": _solve_rectangle,
        "l_shape":   _solve_l_shape,
        "u_shape":   _solve_u_shape,
        "h_shape":   _solve_h_shape,
        "t_shape":   _solve_t_shape,
        "t-shape":   _solve_t_shape,
        "l-shape":   _solve_l_shape,
        "u-shape":   _solve_u_shape,
        "h-shape":   _solve_h_shape,
    }
    solver = solvers.get(shape, _solve_rectangle)
    return solver(total_sf, garage_w, garage_d, master_location=master_location)


def _rect_to_polygon_ccw(x0, y0, x1, y1):
    """Return CCW polygon vertices for a simple rectangle."""
    return [{"x": x0, "y": y0}, {"x": x1, "y": y0},
            {"x": x1, "y": y1}, {"x": x0, "y": y1}]


def _solve_rectangle(living_sf: int, garage_w: int, garage_d: int,
                     master_location=None) -> dict:
    """Rectangle: master|living|beds|service + garage at end + rear porch.
    Adds rear bumpout for master sitting if master_location given."""
    porch_d = 8
    depth = 36
    width = math.ceil(living_sf / depth)
    if width > 100:
        depth = 40
        width = math.ceil(living_sf / depth)
    total_width = width + garage_w
    total_depth = depth + porch_d

    # Zone proportions: master 25%, living 35%, beds 25%, service 15%
    mw = round(width * 0.25)
    lw = round(width * 0.35)
    bw = round(width * 0.25)
    sw = width - mw - lw - bw

    zones = {
        "master":      {"x0": 0,        "y0": porch_d, "x1": mw,        "y1": total_depth},
        "living_core": {"x0": mw,       "y0": porch_d, "x1": mw + lw,   "y1": total_depth},
        "bed_wing":    {"x0": mw + lw,  "y0": porch_d, "x1": mw+lw+bw,  "y1": total_depth},
        "service":     {"x0": mw+lw+bw, "y0": porch_d, "x1": width,     "y1": total_depth},
        "garage":      {"x0": width,    "y0": porch_d, "x1": total_width,
                        "y1": porch_d + garage_d},
        "porch":       {"x0": 0,        "y0": 0,       "x1": width,     "y1": porch_d},
    }
    # Legacy compat
    zones["living"] = zones["living_core"]
    zones["beds"] = zones["bed_wing"]

    # Garage set back 3ft from front face
    garage_setback = 3
    zones["garage"]["y0"] = porch_d + garage_setback

    # Bumpouts
    bumpouts = []
    if master_location:
        # Add rear bumpout for master sitting (8ft wide x 4ft deep)
        bump_x0 = zones["master"]["x0"] + (mw - 8) / 2
        bump_x1 = bump_x0 + 8
        bumpouts.append({
            "face": "N", "offset_start": bump_x0, "offset_end": bump_x1,
            "projection": 4, "purpose": "master_sitting",
        })

    # Build polygon — main rect + bumpouts
    polygon = _rect_to_polygon_ccw(0, porch_d, width, total_depth)
    if bumpouts:
        # Insert bumpout vertices into north face for master sitting
        b = bumpouts[0]
        polygon = [
            {"x": 0,              "y": porch_d},
            {"x": width,          "y": porch_d},
            {"x": width,          "y": total_depth},
            {"x": b["offset_end"],   "y": total_depth},
            {"x": b["offset_end"],   "y": total_depth + b["projection"]},
            {"x": b["offset_start"], "y": total_depth + b["projection"]},
            {"x": b["offset_start"], "y": total_depth},
            {"x": 0,              "y": total_depth},
        ]

    actual_sf = width * depth
    for b in bumpouts:
        actual_sf += (b["offset_end"] - b["offset_start"]) * b["projection"]

    return {
        "shape": "rectangle", "total_width": total_width, "total_depth": total_depth,
        "polygon": polygon, "zones": zones, "bumpouts": bumpouts,
        "total_sf": actual_sf, "width": total_width, "depth": total_depth,
    }


def _solve_l_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None) -> dict:
    """L-shape: main_body + wing. Inner corner has 45° chamfer (4ft) for visual interest."""
    depth = 36
    main_sf = int(living_sf * 0.70)
    wing_sf = living_sf - main_sf
    main_w = math.ceil(main_sf / depth)
    wing_d = 28
    wing_w = math.ceil(wing_sf / wing_d)
    total_width = max(main_w, wing_w + garage_w)
    total_depth = depth + wing_d

    mw = round(main_w * 0.30)
    lw = round(main_w * 0.40)
    bw = main_w - mw - lw

    # Master 2ft deeper than bed wing
    master_extra = 2
    chamfer = 4  # 45° notch at inner corner

    zones = {
        "master":      {"x0": 0,   "y0": 0, "x1": mw,       "y1": depth + master_extra},
        "living_core": {"x0": mw,  "y0": 0, "x1": mw + lw,  "y1": depth},
        "bed_wing":    {"x0": mw + lw, "y0": 0, "x1": main_w, "y1": depth},
        "service":     {"x0": main_w - wing_w, "y0": depth,
                        "x1": main_w, "y1": depth + wing_d},
        "garage":      {"x0": main_w, "y0": depth,
                        "x1": main_w + garage_w, "y1": depth + garage_d},
    }
    zones["living"] = zones["living_core"]
    zones["beds"] = zones["bed_wing"]

    # Polygon: L-shape with chamfer at inner corner (where wing meets main body)
    wing_x0 = main_w - wing_w
    polygon = [
        {"x": 0,        "y": 0},
        {"x": main_w,   "y": 0},
        {"x": main_w,   "y": depth},
        {"x": main_w,   "y": depth + wing_d},
        {"x": wing_x0,  "y": depth + wing_d},
        {"x": wing_x0,  "y": depth + chamfer},       # chamfer start
        {"x": wing_x0 - chamfer, "y": depth},        # chamfer end (45° notch)
        {"x": 0,         "y": depth},
        {"x": 0,         "y": depth + master_extra},  # master extra depth
    ]
    # Fix: master extends north, so adjust polygon
    polygon = [
        {"x": 0,                  "y": 0},
        {"x": main_w,            "y": 0},
        {"x": main_w,            "y": depth + wing_d},
        {"x": wing_x0,           "y": depth + wing_d},
        {"x": wing_x0,           "y": depth + chamfer},
        {"x": wing_x0 - chamfer, "y": depth},
        {"x": 0,                  "y": depth + master_extra},
    ]

    actual_sf = main_w * depth + wing_w * wing_d
    return {
        "shape": "l_shape", "total_width": total_width, "total_depth": total_depth,
        "polygon": polygon, "zones": zones, "bumpouts": [],
        "total_sf": actual_sf, "width": total_width, "depth": total_depth,
    }


def _solve_u_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None) -> dict:
    """U-shape: left_arm + main_body + right_arm with courtyard.
    One wing 3ft deeper than the other for asymmetry."""
    arm_depth = 28
    main_depth = 36
    main_w = 50
    arm_w = math.ceil(
        (living_sf - main_w * main_depth) / (2 * arm_depth))
    arm_w = max(arm_w, 16)
    total_width = arm_w + main_w + arm_w
    # Right wing 3ft deeper for visual interest
    right_extra = 3
    total_depth = arm_depth + main_depth

    zones = {
        "master":      {"x0": 0, "y0": 0,
                        "x1": arm_w, "y1": arm_depth},
        "living_core": {"x0": 0, "y0": arm_depth,
                        "x1": total_width, "y1": total_depth},
        "bed_wing":    {"x0": total_width - arm_w, "y0": 0,
                        "x1": total_width, "y1": arm_depth + right_extra},
        "service":     {"x0": total_width, "y0": arm_depth,
                        "x1": total_width + garage_w,
                        "y1": arm_depth + garage_d},
        "garage":      {"x0": total_width, "y0": arm_depth,
                        "x1": total_width + garage_w,
                        "y1": arm_depth + garage_d},
        "courtyard":   {"x0": arm_w, "y0": 0,
                        "x1": total_width - arm_w, "y1": arm_depth},
        "porch":       {"x0": arm_w, "y0": 0,
                        "x1": total_width - arm_w, "y1": arm_depth},
    }
    zones["living"] = zones["living_core"]
    zones["beds"] = zones["bed_wing"]

    # Polygon: U-shape CCW with right arm 3ft deeper
    polygon = [
        {"x": 0,                   "y": 0},
        {"x": arm_w,              "y": 0},
        {"x": arm_w,              "y": arm_depth},  # courtyard bottom-left
        {"x": total_width - arm_w, "y": arm_depth},  # courtyard bottom-right
        {"x": total_width - arm_w, "y": -right_extra},  # right arm deeper
        {"x": total_width,         "y": -right_extra},
        {"x": total_width,         "y": total_depth},
        {"x": 0,                   "y": total_depth},
        {"x": 0,                   "y": 0},  # close
    ]
    # Remove duplicate close point for clean polygon
    polygon = polygon[:-1]

    actual_sf = arm_w * arm_depth + main_w * main_depth + arm_w * (arm_depth + right_extra)
    return {
        "shape": "u_shape",
        "total_width": total_width + garage_w,
        "total_depth": total_depth,
        "polygon": polygon, "zones": zones, "bumpouts": [],
        "total_sf": actual_sf, "width": total_width + garage_w, "depth": total_depth,
    }


def _solve_h_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None) -> dict:
    """H-shape: left_wing + center_bridge + right_wing, 8ft breezeways."""
    breezeway = 8
    wing_depth = 36
    bridge_depth = 20
    bridge_w = 28
    wing_sf_each = (living_sf - bridge_w * bridge_depth) / 2
    wing_w = math.ceil(wing_sf_each / wing_depth)
    wing_w = max(wing_w, 20)

    total_width = wing_w + breezeway + bridge_w + breezeway + wing_w
    bridge_y0 = (wing_depth - bridge_depth) / 2
    bridge_y1 = bridge_y0 + bridge_depth

    zones = {
        "master":      {"x0": 0, "y0": 0,
                        "x1": wing_w, "y1": wing_depth},
        "living_core": {"x0": wing_w + breezeway, "y0": bridge_y0,
                        "x1": wing_w + breezeway + bridge_w,
                        "y1": bridge_y1},
        "bed_wing":    {"x0": total_width - wing_w, "y0": 0,
                        "x1": total_width, "y1": wing_depth},
        "service":     {"x0": total_width, "y0": 0,
                        "x1": total_width + garage_w, "y1": garage_d},
        "garage":      {"x0": total_width, "y0": 0,
                        "x1": total_width + garage_w, "y1": garage_d},
    }
    zones["living"] = zones["living_core"]
    zones["beds"] = zones["bed_wing"]
    zones["left_wing"] = zones["master"]
    zones["center_bridge"] = zones["living_core"]
    zones["right_wing"] = zones["bed_wing"]

    # H-shape polygon (complex — two wings + bridge)
    bx0 = wing_w + breezeway
    bx1 = bx0 + bridge_w
    polygon = [
        {"x": 0,      "y": 0},
        {"x": wing_w, "y": 0},
        {"x": wing_w, "y": bridge_y0},
        {"x": bx1,    "y": bridge_y0},
        {"x": bx1,    "y": 0},
        {"x": total_width, "y": 0},
        {"x": total_width, "y": wing_depth},
        {"x": bx1,    "y": wing_depth},
        {"x": bx1,    "y": bridge_y1},
        {"x": wing_w, "y": bridge_y1},
        {"x": wing_w, "y": wing_depth},
        {"x": 0,      "y": wing_depth},
    ]

    actual_sf = 2 * wing_w * wing_depth + bridge_w * bridge_depth
    return {
        "shape": "h_shape",
        "total_width": total_width + garage_w,
        "total_depth": wing_depth,
        "polygon": polygon, "zones": zones, "bumpouts": [],
        "total_sf": actual_sf, "width": total_width + garage_w, "depth": wing_depth,
    }


def _solve_t_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None) -> dict:
    """T-shape: wide main body + rear wing centered on back.
    Entry/foyer projects 4ft forward as a distinct volume on front face."""
    porch_d = 8
    front_porch_d = 8

    main_sf = round(living_sf * 0.65)
    wing_sf = living_sf - main_sf

    main_depth = 36
    main_width = max(60, math.ceil(main_sf / main_depth))

    wing_depth = round(wing_sf / (main_width * 0.45))
    wing_depth = max(20, min(wing_depth, 32))
    wing_width = math.ceil(wing_sf / wing_depth)
    wing_width = min(wing_width, round(main_width * 0.45))

    wing_x0 = round((main_width - wing_width) / 2)
    wing_x1 = wing_x0 + wing_width

    total_width = main_width + garage_w
    total_depth = front_porch_d + main_depth + wing_depth

    # Entry foyer projection (4ft forward from front face)
    foyer_projection = 4
    foyer_width = 10
    foyer_x0 = round((main_width - foyer_width) / 2)
    foyer_x1 = foyer_x0 + foyer_width

    front_porch_y0 = 0
    front_porch_y1 = front_porch_d
    main_y0 = front_porch_y1
    main_y1 = main_y0 + main_depth
    wing_y0 = main_y1
    wing_y1 = wing_y0 + wing_depth

    mw = round(main_width * 0.30)
    lw = round(main_width * 0.45)
    sw = main_width - mw - lw

    zones = {
        "master":      {"x0": 0,        "y0": main_y0, "x1": mw,         "y1": main_y1},
        "living_core": {"x0": mw,       "y0": main_y0, "x1": mw + lw,    "y1": main_y1},
        "service":     {"x0": mw + lw,  "y0": main_y0, "x1": main_width, "y1": main_y1},
        "bed_wing":    {"x0": wing_x0,  "y0": wing_y0, "x1": wing_x1,    "y1": wing_y1},
        "garage":      {"x0": main_width, "y0": main_y0 + 3,
                        "x1": total_width, "y1": main_y0 + garage_d + 3},
        "front_porch": {"x0": 0,        "y0": front_porch_y0, "x1": main_width,
                        "y1": front_porch_y1},
        "porch":       {"x0": wing_x0,  "y0": wing_y1, "x1": wing_x1,
                        "y1": wing_y1 + porch_d},
    }
    zones["living"] = zones["living_core"]
    zones["beds"] = zones["bed_wing"]

    # Bumpouts: foyer projection on front face
    bumpouts = [{
        "face": "S", "offset_start": foyer_x0, "offset_end": foyer_x1,
        "projection": foyer_projection, "purpose": "entry_foyer",
    }]

    # T-shape polygon with foyer bump on south face
    polygon = [
        {"x": 0,           "y": main_y0},
        {"x": foyer_x0,   "y": main_y0},
        {"x": foyer_x0,   "y": main_y0 - foyer_projection},
        {"x": foyer_x1,   "y": main_y0 - foyer_projection},
        {"x": foyer_x1,   "y": main_y0},
        {"x": main_width,  "y": main_y0},
        {"x": main_width,  "y": main_y1},
        {"x": wing_x1,    "y": main_y1},
        {"x": wing_x1,    "y": wing_y1},
        {"x": wing_x0,    "y": wing_y1},
        {"x": wing_x0,    "y": main_y1},
        {"x": 0,           "y": main_y1},
    ]

    actual_sf = main_width * main_depth + wing_width * wing_depth
    return {
        "shape": "t_shape", "total_width": total_width, "total_depth": total_depth,
        "polygon": polygon, "zones": zones, "bumpouts": bumpouts,
        "total_sf": actual_sf, "width": total_width, "depth": total_depth,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  3. assign_rooms_to_zones
# ══════════════════════════════════════════════════════════════════════════════

# Maps abstract zone names to possible footprint zone keys (priority order)
_ZONE_KEY_MAP = {
    "master":       ["master", "left_wing", "left_arm"],
    "living":       ["living", "center_bridge", "main_body"],
    "beds":         ["beds", "right_wing", "right_arm", "wing"],
    "service":      ["service"],
    "garage":       ["garage"],
    "porch":        ["porch", "courtyard"],
    "front_porch":  ["front_porch"],
}


def assign_rooms_to_zones(layout_json: dict, zones: dict) -> dict:
    """Place each room into its zone and compute sub-coordinates.

    Returns {room_name: {x0, y0, x1, y1, sf, zone}}.
    """
    rooms = layout_json.get("rooms", [])
    room_coords: dict = {}

    # Group rooms by zone
    by_zone: dict[str, list] = {}
    for r in rooms:
        z = _get_zone(r["name"])
        by_zone.setdefault(z, []).append(r)

    for z_name, z_rooms in by_zone.items():
        # Resolve footprint zone key
        z_key = None
        for candidate in _ZONE_KEY_MAP.get(z_name, [z_name]):
            if candidate in zones:
                z_key = candidate
                break
        if z_key is None:
            z_key = list(zones.keys())[0]

        zone = zones[z_key]
        zx0, zy0 = zone["x0"], zone["y0"]
        zx1, zy1 = zone["x1"], zone["y1"]
        zone_w = zx1 - zx0
        zone_d = zy1 - zy0

        # Sort largest rooms first
        z_rooms.sort(key=lambda r: r.get("sf", 100), reverse=True)
        total_sf = sum(r.get("sf", 100) for r in z_rooms)

        cursor_x = zx0
        cursor_y = zy0
        row_height = 0.0

        for r in z_rooms:
            sf = r.get("sf", 100)
            frac = sf / max(total_sf, 1)
            area = frac * zone_w * zone_d

            # Aim for reasonable aspect ratio
            room_w = math.sqrt(area * (zone_w / max(zone_d, 1)))
            room_w = max(8, min(room_w, zone_w))
            room_d = area / max(room_w, 1)
            room_d = max(8, min(room_d, zone_d))

            # Wrap to next row if needed
            if cursor_x + room_w > zx1 + 0.5:
                cursor_x = zx0
                cursor_y += row_height
                row_height = 0.0

            # Clamp to zone boundaries — never exceed zone extents
            if cursor_y + room_d > zy1:
                room_d = zy1 - cursor_y
            if room_d < 4:
                # Not enough vertical space — repack in leftover column
                cursor_y = zy0
                cursor_x = zx0 + zone_w * 0.8
                room_d = min(zone_d, room_d + 8)
            if cursor_x + room_w > zx1:
                room_w = zx1 - cursor_x
            room_w = max(room_w, 4)
            room_d = max(room_d, 4)

            room_coords[r["name"]] = {
                "x0": round(cursor_x, 1),
                "y0": round(cursor_y, 1),
                "x1": round(cursor_x + room_w, 1),
                "y1": round(cursor_y + room_d, 1),
                "sf": sf,
                "zone": z_name,
            }
            cursor_x += room_w
            row_height = max(row_height, room_d)

    return room_coords


# ══════════════════════════════════════════════════════════════════════════════
#  3b. solve_circulation
# ══════════════════════════════════════════════════════════════════════════════

def solve_circulation(layout_json: dict, footprint_zones: dict, intake_json: dict) -> dict:
    """
    Routes the circulation spine through the layout.

    Circulation rules:
      1. Entry → foyer (min 6x8) → transitions to great room (threshold moment)
      2. Master approach: gallery hall 5-6ft wide, widens to 7ft at master door
      3. Secondary beds: 4ft double-loaded corridor off great room or landing
      4. Service path: garage → mudroom → pantry → kitchen (no crossing master/bed corridors)
      5. 2-story: L2 landing 10x12 min, all L2 rooms door off landing, open railing
      6. Dead ends: master always at dead end — corridor terminates at master door
      7. Width transitions: mark where corridors widen before major spaces

    Returns:
        {
            "spine": [
                {"type": "foyer", "x0":N,"y0":N,"x1":N,"y1":N, "width":N},
                {"type": "gallery", ...},
                {"type": "corridor", ...},
                {"type": "landing", ...},
            ],
            "rules_applied": [...],
            "warnings": [...],
        }
    """
    brief_info = _parse_brief(intake_json.get("brief", ""))
    stories = int(intake_json.get("stories") or brief_info.get("stories", 1))
    rooms = {r["name"]: r for r in layout_json.get("rooms", [])}

    spine = []
    rules_applied = []
    warnings = []

    # ── Locate key zones ─────────────────────────────────────────────────
    master_zone = footprint_zones.get("master")
    living_zone = (footprint_zones.get("living_core") or
                   footprint_zones.get("living") or
                   footprint_zones.get("center_bridge"))
    bed_zone = (footprint_zones.get("bed_wing") or
                footprint_zones.get("beds") or
                footprint_zones.get("right_wing"))
    service_zone = footprint_zones.get("service")
    garage_zone = footprint_zones.get("garage")

    # ── Rule 1: Entry → foyer ────────────────────────────────────────────
    if living_zone:
        lx0, ly0 = living_zone["x0"], living_zone["y0"]
        lx1, ly1 = living_zone["x1"], living_zone["y1"]
        # Foyer at south face of living zone (front of house)
        foyer_w = max(8, min(12, (lx1 - lx0) * 0.2))
        foyer_d = max(6, min(10, 8))
        foyer_cx = (lx0 + lx1) / 2
        foyer = {
            "type": "foyer",
            "x0": round(foyer_cx - foyer_w / 2, 1),
            "y0": round(ly0, 1),
            "x1": round(foyer_cx + foyer_w / 2, 1),
            "y1": round(ly0 + foyer_d, 1),
            "width": foyer_w,
        }
        spine.append(foyer)
        rules_applied.append("R1: Foyer placed at south face of living zone (min 6x8)")

        # Foyer → great room: no wall, just threshold moment
        rules_applied.append("R1: Foyer transitions to great room via threshold (no wall)")

    # ── Rule 2: Master approach gallery ──────────────────────────────────
    if master_zone and living_zone:
        mx0, my0 = master_zone["x0"], master_zone["y0"]
        mx1, my1 = master_zone["x1"], master_zone["y1"]

        # Determine gallery direction (living → master)
        gallery_width = 5.5
        if mx1 <= living_zone["x0"] + 1:
            # Master is west of living — gallery runs E-W
            gallery = {
                "type": "gallery",
                "x0": round(mx1, 1),
                "y0": round((my0 + my1) / 2 - gallery_width / 2, 1),
                "x1": round(living_zone["x0"], 1),
                "y1": round((my0 + my1) / 2 + gallery_width / 2, 1),
                "width": gallery_width,
                "widens_to": 7,
                "widens_at": "master_door",
            }
        elif mx0 >= living_zone["x1"] - 1:
            # Master is east of living
            gallery = {
                "type": "gallery",
                "x0": round(living_zone["x1"], 1),
                "y0": round((my0 + my1) / 2 - gallery_width / 2, 1),
                "x1": round(mx0, 1),
                "y1": round((my0 + my1) / 2 + gallery_width / 2, 1),
                "width": gallery_width,
                "widens_to": 7,
                "widens_at": "master_door",
            }
        else:
            # Master adjacent (same y range) — short gallery along y
            gallery = {
                "type": "gallery",
                "x0": round(mx0, 1),
                "y0": round(max(my0, living_zone["y0"]), 1),
                "x1": round(mx0 + gallery_width, 1),
                "y1": round(min(my1, living_zone["y1"]), 1),
                "width": gallery_width,
                "widens_to": 7,
                "widens_at": "master_door",
            }

        spine.append(gallery)
        rules_applied.append(
            f"R2: Gallery hall {gallery_width}ft wide from great room toward master, "
            "widens to 7ft at master suite door")

    # ── Rule 6: Master dead end ──────────────────────────────────────────
    if master_zone:
        rules_applied.append("R6: Master suite at dead end — corridor terminates at master door")

    # ── Rule 3: Secondary bed corridor ───────────────────────────────────
    if bed_zone:
        bx0, by0 = bed_zone["x0"], bed_zone["y0"]
        bx1, by1 = bed_zone["x1"], bed_zone["y1"]
        corridor_width = 4
        # Corridor runs along the long axis of the bed wing
        bed_dx = bx1 - bx0
        bed_dy = by1 - by0

        if bed_dx >= bed_dy:
            # Long axis E-W: corridor runs E-W at center
            corr_center_y = (by0 + by1) / 2
            corridor = {
                "type": "corridor",
                "x0": round(bx0, 1),
                "y0": round(corr_center_y - corridor_width / 2, 1),
                "x1": round(bx1, 1),
                "y1": round(corr_center_y + corridor_width / 2, 1),
                "width": corridor_width,
                "style": "double-loaded",
            }
        else:
            # Long axis N-S: corridor runs N-S at center
            corr_center_x = (bx0 + bx1) / 2
            corridor = {
                "type": "corridor",
                "x0": round(corr_center_x - corridor_width / 2, 1),
                "y0": round(by0, 1),
                "x1": round(corr_center_x + corridor_width / 2, 1),
                "y1": round(by1, 1),
                "width": corridor_width,
                "style": "double-loaded",
            }

        spine.append(corridor)
        rules_applied.append(
            "R3: 4ft double-loaded corridor for secondary bedrooms off great room")

    # ── Rule 4: Service path ─────────────────────────────────────────────
    if garage_zone and service_zone:
        rules_applied.append(
            "R4: Service path: garage → mudroom → pantry → kitchen "
            "(does not cross master or bed corridors)")
        # Check for crossing violations
        if master_zone and service_zone:
            sx0 = service_zone["x0"]
            mx0 = master_zone["x0"]
            mx1 = master_zone["x1"]
            if sx0 < mx1 and service_zone["x1"] > mx0:
                warnings.append(
                    "Service path may cross master zone — "
                    "verify garage→mudroom→pantry path stays in service zone")

    # ── Rule 5: L2 landing ───────────────────────────────────────────────
    if stories >= 2:
        if living_zone:
            # Landing above service zone or at stair location
            landing_w = 12
            landing_d = 10
            lz_cx = (living_zone["x0"] + living_zone["x1"]) / 2
            lz_cy = (living_zone["y0"] + living_zone["y1"]) / 2
            landing = {
                "type": "landing",
                "x0": round(lz_cx - landing_w / 2, 1),
                "y0": round(lz_cy - landing_d / 2, 1),
                "x1": round(lz_cx + landing_w / 2, 1),
                "y1": round(lz_cy + landing_d / 2, 1),
                "width": landing_w,
                "level": 2,
                "open_railing": True,
            }
            spine.append(landing)
            rules_applied.append(
                "R5: L2 landing 10x12 min, all L2 rooms door off landing, "
                "open railing over great room")
        else:
            warnings.append("L2 plan but no living zone found for landing placement")

    # ── Rule 7: Width transitions ────────────────────────────────────────
    transitions = []
    for i, seg in enumerate(spine):
        if i > 0:
            prev = spine[i - 1]
            if seg.get("width", 4) != prev.get("width", 4):
                transitions.append(
                    f"Width transition: {prev['type']} ({prev.get('width',4)}ft) "
                    f"→ {seg['type']} ({seg.get('width',4)}ft)")
    if transitions:
        rules_applied.append("R7: " + "; ".join(transitions))

    return {
        "spine": spine,
        "rules_applied": rules_applied,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  4. generate_floorplan_image
# ══════════════════════════════════════════════════════════════════════════════

def generate_floorplan_image(
    room_coords: dict,
    submission_id: str,
    output_dir: str = "designs",
) -> str:
    """Render a 2D floor plan PNG with matplotlib. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))

    total_sf = sum(r["sf"] for r in room_coords.values())

    all_x = [c for r in room_coords.values() for c in (r["x0"], r["x1"])]
    all_y = [c for r in room_coords.values() for c in (r["y0"], r["y1"])]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    # Draw rooms
    for rname, rc in room_coords.items():
        color = ZONE_COLORS.get(rc["zone"], "#CCCCCC")
        w = rc["x1"] - rc["x0"]
        h = rc["y1"] - rc["y0"]
        rect = mpatches.FancyBboxPatch(
            (rc["x0"], rc["y0"]), w, h,
            boxstyle="round,pad=0.3",
            facecolor=color, edgecolor="black",
            linewidth=1.2, alpha=0.75,
        )
        ax.add_patch(rect)

        cx = (rc["x0"] + rc["x1"]) / 2
        cy = (rc["y0"] + rc["y1"]) / 2
        fontsize = max(5, min(8, w * 0.6))
        ax.text(
            cx, cy, f"{rname}\n{rc['sf']} SF",
            ha="center", va="center", fontsize=fontsize, fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round,pad=0.1", facecolor="black", alpha=0.4),
        )

    # Dimension annotations
    ax.annotate(
        "", xy=(max_x, min_y - 3), xytext=(min_x, min_y - 3),
        arrowprops=dict(arrowstyle="<->", color="black", lw=1.5))
    ax.text(
        (min_x + max_x) / 2, min_y - 4,
        f"{max_x - min_x:.0f} ft",
        ha="center", va="top", fontsize=9, fontweight="bold")

    ax.annotate(
        "", xy=(max_x + 3, max_y), xytext=(max_x + 3, min_y),
        arrowprops=dict(arrowstyle="<->", color="black", lw=1.5))
    ax.text(
        max_x + 4, (min_y + max_y) / 2,
        f"{max_y - min_y:.0f} ft",
        ha="left", va="center", fontsize=9, fontweight="bold", rotation=90)

    # North arrow
    ax.annotate(
        "N", xy=(min_x - 3, max_y),
        fontsize=14, fontweight="bold", ha="center", va="bottom")
    ax.annotate(
        "", xy=(min_x - 3, max_y), xytext=(min_x - 3, max_y - 5),
        arrowprops=dict(arrowstyle="->", color="black", lw=2))

    # Legend
    legend_patches = [
        mpatches.Patch(color=c, label=z.capitalize())
        for z, c in ZONE_COLORS.items()
    ]
    ax.legend(handles=legend_patches, loc="upper right", fontsize=8)

    # Title
    ax.set_title(
        f"Barnhaus Floor Plan \u2014 {total_sf} SF Total\n"
        f"Submission: {submission_id}",
        fontsize=12, fontweight="bold")

    pad = 5
    ax.set_xlim(min_x - pad - 5, max_x + pad + 6)
    ax.set_ylim(min_y - pad - 5, max_y + pad)
    ax.set_aspect("equal")
    ax.set_xlabel("ft")
    ax.set_ylabel("ft")
    ax.grid(True, alpha=0.2)

    path = os.path.join(output_dir, f"floorplan_{submission_id[:8]}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ══════════════════════════════════════════════════════════════════════════════
#  5. run_planner
# ══════════════════════════════════════════════════════════════════════════════

SUPABASE_URL = "https://hbfjdfxephlczkfgpceg.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiZmpkZnhlcGhsY3prZmdwY2VnIiwi"
    "cm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTMzNzcxMCwiZXhwIjoyMDU0"
    "OTEzNzEwfQ.weXk7CqDqR8XkEpi4kaI_GmHWlkqh6snOMQm-hk48RM"
)


def _upload_to_supabase(file_path: str, submission_id: str) -> str:
    """Upload PNG to Supabase 'temp' bucket. Returns public URL or error."""
    bucket = "temp"
    filename = os.path.basename(file_path)
    storage_path = f"{submission_id}/{filename}"
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"

    with open(file_path, "rb") as f:
        data = f.read()

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "image/png",
    }

    resp = requests.post(url, headers=headers, data=data)
    if resp.status_code == 400:
        # Already exists — upsert
        resp = requests.put(url, headers=headers, data=data)

    if resp.status_code in (200, 201):
        return (f"{SUPABASE_URL}/storage/v1/object/public/"
                f"{bucket}/{storage_path}")
    return f"Upload failed ({resp.status_code}): {resp.text}"


def run_planner(
    submission_id: str,
    layout_json: dict,
    intake_json: dict,
) -> dict:
    """Full pipeline: validate -> solve -> assign -> render -> upload."""
    violations = validate_layout(layout_json, intake_json)
    footprint = solve_footprint(layout_json, intake_json)
    room_coords = assign_rooms_to_zones(layout_json, footprint["zones"])
    image_path = generate_floorplan_image(room_coords, submission_id)
    floorplan_url = _upload_to_supabase(image_path, submission_id)

    return {
        "violations": violations,
        "footprint": footprint,
        "room_coords": room_coords,
        "floorplan_url": floorplan_url,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    design_path = "designs/design_a3fe564b.json"
    with open(design_path) as f:
        data = json.load(f)

    submission_id = data["submission_id"]
    layout_json = data["layout"]
    intake_json = data

    result = run_planner(submission_id, layout_json, intake_json)

    print("=" * 60)
    print("BARNHAUS PLANNER RESULTS")
    print("=" * 60)
    print(f"\nViolations ({len(result['violations'])}):")
    for v in result["violations"]:
        print(f"  - {v}")

    fp = result["footprint"]
    print(f"\nFootprint: {fp['shape']}")
    print(f"  Total: {fp['total_width']}ft x {fp['total_depth']}ft")
    print(f"  Zones:")
    for zn, zd in fp["zones"].items():
        w = zd["x1"] - zd["x0"]
        d = zd["y1"] - zd["y0"]
        print(f"    {zn:16s}  ({zd['x0']},{zd['y0']})->"
              f"({zd['x1']},{zd['y1']})  {w}x{d}={w*d} SF")

    print(f"\nRoom Assignments ({len(result['room_coords'])}):")
    for rname, rc in result["room_coords"].items():
        print(f"  {rname:20s}  zone={rc['zone']:8s}  "
              f"({rc['x0']:.0f},{rc['y0']:.0f})->({rc['x1']:.0f},"
              f"{rc['y1']:.0f})  {rc['sf']} SF")

    print(f"\nFloor plan: {result['floorplan_url']}")
