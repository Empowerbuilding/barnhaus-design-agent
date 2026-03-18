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
    "His Closet":          {"min": 40,  "target_lo": 60,  "target_hi": 80,  "max": 120},
    "Hers Closet":         {"min": 50,  "target_lo": 80,  "target_hi": 120, "max": 180},
    "Master Closet":       {"min": 40,  "target_lo": 60,  "target_hi": 120, "max": 180},
    "Master Sitting Room": {"min": 80,  "target_lo": 100, "target_hi": 140, "max": 200},
    "Bedroom":             {"min": 110, "target_lo": 130, "target_hi": 180, "max": 220},
    "Bathroom":            {"min": 70,  "target_lo": 90,  "target_hi": 120, "max": 160},
    "Great Room":          {"min": 280, "target_lo": 380, "target_hi": 520, "max": 700},
    "Kitchen":             {"min": 88,  "target_lo": 180, "target_hi": 320, "max": 420},
    "Dining Room":         {"min": 100, "target_lo": 130, "target_hi": 180, "max": 240},
    "Dining":              {"min": 100, "target_lo": 130, "target_hi": 180, "max": 240},
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
    if any(kw in low for kw in ("garage", "mudroom", "laundry", "pantry", "utility", "mechanical", "storage")):
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

    # ── Spatial intent from intake form ─────────────────────────────────────
    # master_location: far_left | far_right | rear_center | front_center
    # garage_attachment: attached_left | attached_right | detached
    # street_facing: N | S | E | W  (which side faces the street / entry)
    master_location = (
        intake_json.get("master_location") or
        intake_json.get("master_suite", {}).get("location") if isinstance(intake_json.get("master_suite"), dict) else None or
        layout_json.get("master_location")
    )
    garage_attachment = intake_json.get("garage_attachment", "attached_right")
    street_facing = intake_json.get("street_facing", "S")  # default: entry from south

    # Normalize master_location
    if not master_location:
        master_location = "far_left"  # Barnhaus default

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
    vid = (intake_json.get("id") or intake_json.get("submission_id") or "")[:12]
    result = solver(total_sf, garage_w, garage_d,
                    master_location=master_location,
                    garage_attachment=garage_attachment,
                    _vid=vid)

    # ── Flip zones if master should be on right ───────────────────────────
    # Default solvers always put master on the left (x=0 side).
    # If intake says far_right, mirror all zone x coords.
    if master_location in ("far_right",) and result.get("total_width"):
        tw = result["total_width"]
        def _flip_x(v): return tw - v

        def _flip_zone(z):
            return {"x0": _flip_x(z["x1"]), "y0": z["y0"],
                    "x1": _flip_x(z["x0"]), "y1": z["y1"]}

        result["zones"] = {k: _flip_zone(v) for k, v in result["zones"].items()}
        result["polygon"] = [{"x": _flip_x(p["x"]), "y": p["y"]}
                              for p in result["polygon"]]
        # Swap master ↔ bed_wing zone names after flip
        z = result["zones"]
        z["master"], z["bed_wing"] = z.get("bed_wing", z.get("master")), z.get("master")
        if "left_wing" in z and "right_wing" in z:
            z["left_wing"], z["right_wing"] = z["right_wing"], z["left_wing"]

    result["master_location"] = master_location
    result["garage_attachment"] = garage_attachment
    result["street_facing"] = street_facing
    return result


def _rect_to_polygon_ccw(x0, y0, x1, y1):
    """Return CCW polygon vertices for a simple rectangle."""
    return [{"x": x0, "y": y0}, {"x": x1, "y": y0},
            {"x": x1, "y": y1}, {"x": x0, "y": y1}]


def _variation(submission_id: str, key: str, lo: float, hi: float) -> float:
    """Deterministic variation seeded by submission_id + key.
    Always returns same value for same inputs — reproducible per project."""
    import hashlib
    seed = int(hashlib.md5(f"{submission_id or 'default'}{key}".encode()).hexdigest(), 16)
    t = (seed % 1000) / 1000.0  # 0.0 → 1.0
    return round(lo + t * (hi - lo), 1)


def _solve_rectangle(living_sf: int, garage_w: int, garage_d: int,
                     master_location=None, garage_attachment="attached_right",
                     _vid: str = "", **_) -> dict:
    """
    Rectangle plan with real articulation:
    - Great room steps BACK from house face (compression/release effect)
    - Master wing is DEEPER than bed wing (more rooms stacked)
    - Garage face set back 6-10ft from main house face
    - Rear bumpout on master side (sitting room / master bath bump)
    - Front covered porch full width
    """
    # Varied depths per zone — master deeper, beds shallower, great room pushed back
    master_d   = _variation(_vid, "rect_master_d",   34, 42)   # deeper = more private rooms
    great_d    = _variation(_vid, "rect_great_d",    30, 38)   # great room depth
    bed_d      = _variation(_vid, "rect_bed_d",      28, 36)   # shallower than master
    service_d  = _variation(_vid, "rect_service_d",  26, 32)   # service narrowest

    # Great room steps back from front face (creates entry compression)
    gr_stepback = _variation(_vid, "rect_gr_stepback", 2, 6)

    # Overall depth = master (it's the deepest)
    house_depth = master_d
    porch_d = _variation(_vid, "rect_porch_d", 10, 16)

    # Width: solve from SF using average zone depth
    avg_d = (master_d * 0.28 + great_d * 0.38 + bed_d * 0.24 + service_d * 0.10)
    width = max(48, math.ceil(living_sf / avg_d))
    if width > 110:
        # Too wide — increase depth
        master_d += 4; great_d += 4; bed_d += 4
        avg_d = (master_d*0.28 + great_d*0.38 + bed_d*0.24 + service_d*0.10)
        width = math.ceil(living_sf / avg_d)

    # Zone widths — NOT equal. Great room is widest, service narrowest
    mw = round(width * _variation(_vid, "rect_mw_frac", 0.22, 0.30))
    lw = round(width * _variation(_vid, "rect_lw_frac", 0.34, 0.42))
    sw = round(width * _variation(_vid, "rect_sw_frac", 0.08, 0.14))
    bw = width - mw - lw - sw

    total_width = width + garage_w

    # Y positions (south to north = 0 to +)
    y0_front = porch_d
    y0_house = porch_d

    # Each zone has its own depth — rear wall is NOT a straight line
    zones = {
        "master":      {"x0": 0,        "y0": y0_house, "x1": mw,        "y1": y0_house + master_d},
        "living_core": {"x0": mw,       "y0": y0_house + gr_stepback,
                        "x1": mw + lw,  "y1": y0_house + gr_stepback + great_d},
        "bed_wing":    {"x0": mw + lw,  "y0": y0_house, "x1": mw+lw+bw,  "y1": y0_house + bed_d},
        "service":     {"x0": mw+lw+bw, "y0": y0_house, "x1": width,     "y1": y0_house + service_d},
        "porch":       {"x0": 0,        "y0": 0,         "x1": width,     "y1": porch_d},
    }
    zones["living"] = zones["living_core"]
    zones["beds"] = zones["bed_wing"]

    # Garage — set back from front face, NOT flush
    garage_setback = _variation(_vid, "rect_garage_setback", 5, 10)
    zones["garage"] = {
        "x0": width, "y0": y0_house + garage_setback,
        "x1": width + garage_w, "y1": y0_house + garage_setback + garage_d
    }

    # Master rear bumpout (sitting room or his/her bath extension)
    bump_w = _variation(_vid, "rect_bump_w", 10, 16)
    bump_d = _variation(_vid, "rect_bump_d", 4, 8)
    bump_x0 = zones["master"]["x0"] + (mw - bump_w) / 2
    bump_x1 = bump_x0 + bump_w
    master_rear = zones["master"]["y1"]

    bumpouts = [{
        "face": "N", "offset_start": bump_x0, "offset_end": bump_x1,
        "projection": bump_d, "purpose": "master_sitting_or_bath",
    }]

    # Great room rear bumpout (view wall push)
    gr_bump_w = _variation(_vid, "rect_gr_bump_w", 14, 22)
    gr_bump_d = _variation(_vid, "rect_gr_bump_d", 3, 6)
    gr_rear = zones["living_core"]["y1"]
    gr_cx = (zones["living_core"]["x0"] + zones["living_core"]["x1"]) / 2
    gr_bump_x0 = gr_cx - gr_bump_w / 2
    gr_bump_x1 = gr_cx + gr_bump_w / 2
    bumpouts.append({
        "face": "N", "offset_start": gr_bump_x0, "offset_end": gr_bump_x1,
        "projection": gr_bump_d, "purpose": "great_room_view_wall_push",
    })

    # Build articulated polygon tracing the actual stepped rear wall
    # South face: straight across at y0_house (front of house behind porch)
    # Rear face: steps per zone depth
    polygon = [
        # South face (front of house, west to east)
        {"x": 0,     "y": y0_house},
        {"x": width, "y": y0_house},
        # East face down to service rear, then step to bed rear
        {"x": width, "y": y0_house + service_d},
        {"x": mw+lw+bw, "y": y0_house + service_d},
        {"x": mw+lw+bw, "y": y0_house + bed_d},
        # Bed rear → great room rear step
        {"x": mw+lw, "y": y0_house + bed_d},
        {"x": mw+lw, "y": gr_rear},
        # Great room rear bumpout
        {"x": gr_bump_x1, "y": gr_rear},
        {"x": gr_bump_x1, "y": gr_rear + gr_bump_d},
        {"x": gr_bump_x0, "y": gr_rear + gr_bump_d},
        {"x": gr_bump_x0, "y": gr_rear},
        # Great room → master step
        {"x": mw,   "y": gr_rear},
        {"x": mw,   "y": master_rear},
        # Master rear bumpout
        {"x": bump_x1, "y": master_rear},
        {"x": bump_x1, "y": master_rear + bump_d},
        {"x": bump_x0, "y": master_rear + bump_d},
        {"x": bump_x0, "y": master_rear},
        # West face back to start
        {"x": 0,    "y": master_rear},
    ]

    actual_sf = mw*master_d + lw*great_d + bw*bed_d + sw*service_d
    for b in bumpouts:
        actual_sf += (b["offset_end"] - b["offset_start"]) * b["projection"]

    max_depth = max(master_rear + bump_d, gr_rear + gr_bump_d, y0_house + bed_d)

    return {
        "shape": "rectangle", "total_width": total_width,
        "total_depth": max_depth + porch_d,
        "polygon": polygon, "zones": zones, "bumpouts": bumpouts,
        "total_sf": actual_sf, "width": total_width, "depth": max_depth + porch_d,
        "ceiling_heights": {
            "master": 11, "living_core": 16, "bed_wing": 10, "service": 9,
        },
    }


def _solve_l_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None, garage_attachment="attached_right",
                   _vid: str = "") -> dict:
    """
    L-shape with real asymmetry and articulation:
    - Main bar WIDER than it is deep — long horizontal spine
    - Wing much NARROWER and deeper than the bar — creates strong L
    - Inner corner has real notch/step, not just chamfer
    - Wing offset: NOT flush with bar end — steps in 4-6ft
    - Covered breezeway along inner corner (outdoor covered connection)
    - Garage set into the crook of the L, face set back
    """
    # Main bar: wider, shallower (great room + master along front)
    bar_depth  = _variation(_vid, "l_bar_depth",  32, 42)
    bar_frac   = _variation(_vid, "l_bar_frac",   0.62, 0.72)  # % of SF in bar
    bar_sf     = int(living_sf * bar_frac)
    wing_sf    = living_sf - bar_sf

    # Wing: narrower, deeper (bed wing + secondary bath)
    wing_depth = _variation(_vid, "l_wing_depth", 28, 38)
    wing_w     = max(18, math.ceil(wing_sf / wing_depth))
    wing_w     = min(wing_w, 36)  # wings never wider than 36ft

    bar_w      = max(wing_w + 20, math.ceil(bar_sf / bar_depth))

    # Wing steps IN from bar end (creates pocket / notch in plan)
    wing_step_in = _variation(_vid, "l_wing_step", 3, 8)
    wing_x0    = bar_w - wing_w - wing_step_in
    wing_x1    = wing_x0 + wing_w

    # Covered breezeway in inner corner (outdoor space in the notch)
    breeze_d   = _variation(_vid, "l_breeze_d", 8, 14)

    # Zone widths in bar: master left, great room center, service right
    mw = round(bar_w * _variation(_vid, "l_mw_frac", 0.24, 0.32))
    lw = round(bar_w * _variation(_vid, "l_lw_frac", 0.38, 0.46))
    sw = bar_w - mw - lw  # service

    # Master is deeper than bed side of bar
    master_extra_d = _variation(_vid, "l_master_extra", 3, 7)

    bar_y0 = 0
    bar_y1 = bar_depth
    wing_y0 = bar_y1
    wing_y1 = bar_y1 + wing_depth

    zones = {
        "master":      {"x0": 0,     "y0": bar_y0, "x1": mw,      "y1": bar_y1 + master_extra_d},
        "living_core": {"x0": mw,    "y0": bar_y0, "x1": mw + lw, "y1": bar_y1},
        "service":     {"x0": mw+lw, "y0": bar_y0, "x1": bar_w,   "y1": bar_y1},
        "bed_wing":    {"x0": wing_x0, "y0": wing_y0, "x1": wing_x1, "y1": wing_y1},
        "breezeway":   {"x0": wing_x1, "y0": wing_y0, "x1": bar_w,   "y1": wing_y0 + breeze_d},
        "porch":       {"x0": 0,     "y0": -10,    "x1": bar_w,   "y1": 0},
    }

    # Garage sits OUTSIDE the L crook — set back from bar face
    garage_setback = _variation(_vid, "l_garage_setback", 4, 8)
    if garage_attachment == "attached_left":
        zones["garage"] = {
            "x0": -garage_w, "y0": bar_y0 + garage_setback,
            "x1": 0,         "y1": bar_y0 + garage_setback + garage_d
        }
    else:
        zones["garage"] = {
            "x0": bar_w,            "y0": wing_y0 + garage_setback,
            "x1": bar_w + garage_w, "y1": wing_y0 + garage_setback + garage_d
        }

    zones["living"] = zones["living_core"]
    zones["beds"]   = zones["bed_wing"]

    # Articulated L polygon — traces actual building perimeter
    polygon = [
        # Start SW corner, go clockwise
        {"x": 0,       "y": bar_y0},
        {"x": bar_w,   "y": bar_y0},
        {"x": bar_w,   "y": wing_y0},             # east face of bar drops to wing top
        {"x": wing_x1 + wing_step_in, "y": wing_y0},   # step at inner corner
        {"x": wing_x1 + wing_step_in, "y": wing_y0 + breeze_d},  # breezeway pocket
        {"x": wing_x1, "y": wing_y0 + breeze_d},
        {"x": wing_x1, "y": wing_y1},             # south face of wing
        {"x": wing_x0, "y": wing_y1},
        {"x": wing_x0, "y": wing_y0},             # back up wing west face
        {"x": 0,       "y": wing_y0},
        # West face back up (master side is deeper)
        {"x": 0,       "y": bar_y1 + master_extra_d},
    ]

    actual_sf = bar_w * bar_depth + wing_w * wing_depth + mw * master_extra_d

    return {
        "shape": "l_shape",
        "total_width": bar_w + garage_w,
        "total_depth": wing_y1,
        "polygon": polygon, "zones": zones, "bumpouts": [],
        "total_sf": actual_sf, "width": bar_w + garage_w, "depth": wing_y1,
        "ceiling_heights": {
            "master": 11, "living_core": 16, "bed_wing": 10, "service": 9,
        },
    }


def _solve_u_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None, garage_attachment="attached_right",
                   _vid: str = "") -> dict:
    """
    U-shape with real asymmetry:
    - Arms are DIFFERENT widths (master arm wider and deeper than bed arm)
    - Courtyard is NOT centered — offset toward the view side
    - Main bar steps back from arm faces (compression through courtyard, release into bar)
    - Bar deeper than arms
    - Covered porch fills courtyard opening (front outdoor living)
    """
    # Arms: master arm wider and deeper, bed arm narrower
    master_arm_w = _variation(_vid, "u_master_arm_w", 20, 30)
    bed_arm_w    = _variation(_vid, "u_bed_arm_w",    16, 24)
    master_arm_d = _variation(_vid, "u_master_arm_d", 28, 36)
    bed_arm_d    = _variation(_vid, "u_bed_arm_d",    24, 32)

    # Main bar: deeper than arms
    bar_depth    = _variation(_vid, "u_bar_depth",    32, 42)
    bar_step     = _variation(_vid, "u_bar_step",     4, 8)   # bar face steps back from arm face

    # Courtyard offset — NOT centered, shifted toward bed arm side
    courtyard_offset = _variation(_vid, "u_court_offset", 2, 6)

    # Total width
    total_w = master_arm_w + _variation(_vid, "u_court_w", 28, 44) + bed_arm_w

    arm_y0   = 0
    court_d  = max(master_arm_d, bed_arm_d)
    bar_y0   = court_d + bar_step
    bar_y1   = bar_y0 + bar_depth

    # Bar spans full width — arms project forward
    bar_x0 = 0
    bar_x1 = total_w

    zones = {
        "master":      {"x0": 0,                    "y0": arm_y0,
                        "x1": master_arm_w,          "y1": master_arm_d},
        "living_core": {"x0": bar_x0,               "y0": bar_y0,
                        "x1": bar_x1,                "y1": bar_y1},
        "bed_wing":    {"x0": total_w - bed_arm_w,  "y0": arm_y0,
                        "x1": total_w,               "y1": bed_arm_d},
        "service":     {"x0": bar_x0,               "y0": court_d,
                        "x1": master_arm_w + 8,      "y1": bar_y0},   # service strip between arm and bar
        "courtyard":   {"x0": master_arm_w,          "y0": arm_y0,
                        "x1": total_w - bed_arm_w,   "y1": court_d},
        "porch":       {"x0": master_arm_w,          "y0": arm_y0,
                        "x1": total_w - bed_arm_w,   "y1": court_d},
    }

    # Garage at rear of bar or off bed arm end
    garage_setback = _variation(_vid, "u_garage_setback", 3, 7)
    zones["garage"] = {
        "x0": total_w,             "y0": bar_y0 + garage_setback,
        "x1": total_w + garage_w,  "y1": bar_y0 + garage_setback + garage_d
    }
    zones["living"] = zones["living_core"]
    zones["beds"]   = zones["bed_wing"]

    # U polygon — two arms + bar, with step at bar face
    polygon = [
        # Master arm (NW): south face at y=0
        {"x": 0,           "y": arm_y0},
        {"x": master_arm_w,"y": arm_y0},
        # Master arm east face drops to courtyard level then steps into bar
        {"x": master_arm_w,"y": master_arm_d},
        {"x": 0,           "y": master_arm_d},         # back up west face of master arm?
        # No — continue east along courtyard front edge
    ]
    # Cleaner approach: trace perimeter
    polygon = [
        {"x": 0,                   "y": arm_y0},
        {"x": master_arm_w,        "y": arm_y0},
        {"x": master_arm_w,        "y": master_arm_d},
        {"x": bar_x0,              "y": court_d},       # step to bar face
        {"x": bar_x0,              "y": bar_y1},        # bar north face
        {"x": bar_x1,              "y": bar_y1},
        {"x": bar_x1,              "y": court_d},
        {"x": total_w - bed_arm_w, "y": bed_arm_d},
        {"x": total_w - bed_arm_w, "y": arm_y0},
        {"x": total_w,             "y": arm_y0},
        {"x": total_w,             "y": bed_arm_d},
        {"x": total_w,             "y": bar_y1},
        # Back west along bar top already covered — close west
        {"x": 0,                   "y": bar_y1},
        {"x": 0,                   "y": master_arm_d},
        {"x": 0,                   "y": arm_y0},
    ]
    # Deduplicate consecutive identical points
    seen = []
    for p in polygon:
        if not seen or seen[-1] != p:
            seen.append(p)
    polygon = seen

    actual_sf = (master_arm_w * master_arm_d + bed_arm_w * bed_arm_d +
                 total_w * bar_depth)

    return {
        "shape": "u_shape",
        "total_width": total_w + garage_w,
        "total_depth": bar_y1,
        "polygon": polygon, "zones": zones, "bumpouts": [],
        "total_sf": actual_sf, "width": total_w + garage_w, "depth": bar_y1,
        "ceiling_heights": {
            "master": 11, "living_core": 16, "bed_wing": 10, "service": 9,
        },
    }


def _solve_h_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None, garage_attachment="attached_right",
                   _vid: str = "") -> dict:
    """
    H-shape with real variation:
    - Left wing (master) WIDER and DEEPER than right wing (beds)
    - Bridge (great room/kitchen) offset — NOT centered between wings
    - Breezeways DIFFERENT widths (master side open, bed side tighter)
    - Bridge pushed toward master side for asymmetry
    - Each wing has distinct depth variation
    """
    # Wing dimensions — master wider and deeper
    lw_w = _variation(_vid, "h_left_w",  20, 32)   # master wing width
    rw_w = _variation(_vid, "h_right_w", 18, 28)   # bed wing width
    lw_d = _variation(_vid, "h_left_d",  34, 44)   # master wing depth
    rw_d = _variation(_vid, "h_right_d", 28, 38)   # bed wing depth (shallower)

    # Breezeways — different widths
    lw_breeze = _variation(_vid, "h_lbreeze", 6, 10)   # master side breezeway
    rw_breeze = _variation(_vid, "h_rbreeze", 7, 12)   # bed side breezeway

    # Bridge — sized from remaining SF
    bridge_d  = _variation(_vid, "h_bridge_d", 18, 28)
    bridge_sf = living_sf - lw_w * lw_d - rw_w * rw_d
    bridge_w  = max(24, math.ceil(bridge_sf / bridge_d))
    bridge_w  = min(bridge_w, 44)

    # Total width
    total_w = lw_w + lw_breeze + bridge_w + rw_breeze + rw_w

    # Bridge positioned — NOT centered between wings. Offset toward master.
    bridge_offset = _variation(_vid, "h_bridge_offset", -4, 4)  # negative = toward master
    bridge_x0 = lw_w + lw_breeze + bridge_offset
    bridge_x1 = bridge_x0 + bridge_w

    # Wing Y extents — different depths, bridge sits between them
    wing_y0   = 0
    max_wing_d = max(lw_d, rw_d)
    # Bridge vertically centered between its shorter dimension
    bridge_y0 = (max_wing_d - bridge_d) / 2
    bridge_y1 = bridge_y0 + bridge_d

    zones = {
        "master":       {"x0": 0,         "y0": wing_y0, "x1": lw_w,        "y1": lw_d},
        "living_core":  {"x0": bridge_x0, "y0": bridge_y0, "x1": bridge_x1, "y1": bridge_y1},
        "bed_wing":     {"x0": total_w - rw_w, "y0": wing_y0, "x1": total_w, "y1": rw_d},
        "service":      {"x0": total_w,   "y0": wing_y0, "x1": total_w + garage_w, "y1": garage_d},
        "garage":       {"x0": total_w,   "y0": wing_y0 + 4,
                         "x1": total_w + garage_w, "y1": wing_y0 + 4 + garage_d},
    }
    zones["living"]       = zones["living_core"]
    zones["beds"]         = zones["bed_wing"]
    zones["left_wing"]    = zones["master"]
    zones["center_bridge"]= zones["living_core"]
    zones["right_wing"]   = zones["bed_wing"]

    # H polygon — trace left wing, bridge, right wing
    bx0 = bridge_x0
    bx1 = bridge_x1
    polygon = [
        # Left wing south face
        {"x": 0,    "y": wing_y0},
        {"x": lw_w, "y": wing_y0},
        # Left wing east face up to bridge
        {"x": lw_w, "y": bridge_y0},
        # Bridge south face
        {"x": bx0,  "y": bridge_y0},
        # Nudge: left breezeway pocket (slight notch)
        {"x": bx0,  "y": wing_y0},
        {"x": bx1,  "y": wing_y0},
        # Right breezeway and wing south
        {"x": bx1,  "y": bridge_y0},
        {"x": total_w - rw_w, "y": bridge_y0},
        {"x": total_w - rw_w, "y": wing_y0},
        {"x": total_w, "y": wing_y0},
        # Right wing north face
        {"x": total_w, "y": rw_d},
        {"x": total_w - rw_w, "y": rw_d},
        # Right wing west face down to bridge north
        {"x": total_w - rw_w, "y": bridge_y1},
        {"x": bx1,  "y": bridge_y1},
        {"x": bx1,  "y": max_wing_d},
        {"x": bx0,  "y": max_wing_d},
        {"x": bx0,  "y": bridge_y1},
        # Left wing east face down from bridge north
        {"x": lw_w, "y": bridge_y1},
        {"x": lw_w, "y": lw_d},
        # Left wing north face back to west
        {"x": 0,    "y": lw_d},
    ]

    actual_sf = lw_w * lw_d + bridge_w * bridge_d + rw_w * rw_d

    return {
        "shape": "h_shape",
        "total_width": total_w + garage_w,
        "total_depth": max_wing_d,
        "polygon": polygon, "zones": zones, "bumpouts": [],
        "total_sf": actual_sf, "width": total_w + garage_w, "depth": max_wing_d,
        "ceiling_heights": {
            "master": 11, "living_core": 16, "bed_wing": 10, "service": 9,
        },
    }


def _solve_t_shape(living_sf: int, garage_w: int, garage_d: int,
                   master_location=None, garage_attachment="attached_right",
                   _vid: str = "") -> dict:
    """
    T-shape with real articulation:
    - Main bar wider, with master LEFT and service/garage RIGHT
    - Rear wing is NOT centered — offset toward master or bed side
    - Wing width varies (not always 45% of bar)
    - Entry foyer PROJECTS forward as distinct volume with roof break
    - Great room steps BACK from bar face (view wall bumpout at rear)
    - Garage face set back from bar face, angled slightly (toe-in)
    """
    # Main bar dimensions
    bar_depth  = _variation(_vid, "t_bar_depth",  32, 42)
    bar_frac   = _variation(_vid, "t_bar_frac",   0.60, 0.72)  # % SF in bar
    bar_sf     = int(living_sf * bar_frac)
    bar_w      = max(56, math.ceil(bar_sf / bar_depth))

    # Rear wing — offset from center
    wing_frac  = _variation(_vid, "t_wing_frac",  0.36, 0.48)  # wing width as % of bar
    wing_w     = round(bar_w * wing_frac)
    wing_sf    = living_sf - bar_sf
    wing_depth = max(20, math.ceil(wing_sf / wing_w))
    wing_depth = min(wing_depth, 36)

    # Wing offset from bar center — toward master or bed side
    wing_bias  = _variation(_vid, "t_wing_bias", -8, 6)  # negative = toward master (left)
    wing_x0    = round((bar_w - wing_w) / 2 + wing_bias)
    wing_x0    = max(4, min(wing_x0, bar_w - wing_w - 4))
    wing_x1    = wing_x0 + wing_w

    # Covered front porch
    porch_d    = _variation(_vid, "t_porch_d", 10, 16)

    # Foyer projection (entry bump on south face)
    foyer_w    = _variation(_vid, "t_foyer_w", 8, 14)
    foyer_proj = _variation(_vid, "t_foyer_proj", 3, 6)
    foyer_bias = _variation(_vid, "t_foyer_bias", -6, 6)  # offset from center
    foyer_x0   = round(bar_w / 2 - foyer_w / 2 + foyer_bias)
    foyer_x0   = max(mw := round(bar_w * _variation(_vid, "t_mw", 0.24, 0.32)), foyer_x0)
    foyer_x1   = foyer_x0 + foyer_w

    # Zone widths in bar
    lw_frac    = _variation(_vid, "t_lw_frac", 0.36, 0.46)
    lw         = round(bar_w * lw_frac)   # great room width
    sw         = bar_w - mw - lw          # service width

    bar_y0     = porch_d
    bar_y1     = bar_y0 + bar_depth
    wing_y0    = bar_y1
    wing_y1    = wing_y0 + wing_depth
    porch_y0   = wing_y1
    rear_porch_d = _variation(_vid, "t_rear_porch_d", 10, 18)
    porch_y1   = porch_y0 + rear_porch_d

    # Great room view wall bumpout
    gr_bump_w  = _variation(_vid, "t_gr_bump_w", 16, 24)
    gr_bump_d  = _variation(_vid, "t_gr_bump_d", 3, 6)
    gr_cx      = mw + lw / 2
    gr_bump_x0 = gr_cx - gr_bump_w / 2
    gr_bump_x1 = gr_cx + gr_bump_w / 2

    zones = {
        "master":      {"x0": 0,         "y0": bar_y0, "x1": mw,        "y1": bar_y1},
        "living_core": {"x0": mw,        "y0": bar_y0, "x1": mw + lw,   "y1": bar_y1},
        "service":     {"x0": mw + lw,   "y0": bar_y0, "x1": bar_w,     "y1": bar_y1},
        "bed_wing":    {"x0": wing_x0,   "y0": wing_y0, "x1": wing_x1,  "y1": wing_y1},
        "porch":       {"x0": wing_x0,   "y0": porch_y0, "x1": wing_x1, "y1": porch_y1},
        "front_porch": {"x0": 0,         "y0": 0,       "x1": bar_w,    "y1": porch_d},
        "garage":      {
            "x0": bar_w, "y0": bar_y0 + _variation(_vid, "t_g_setback", 4, 9),
            "x1": bar_w + garage_w,
            "y1": bar_y0 + _variation(_vid, "t_g_setback", 4, 9) + garage_d
        },
    }
    zones["living"] = zones["living_core"]
    zones["beds"]   = zones["bed_wing"]

    bumpouts = [
        {"face": "S", "offset_start": foyer_x0, "offset_end": foyer_x1,
         "projection": foyer_proj, "purpose": "entry_foyer"},
        {"face": "N", "offset_start": gr_bump_x0, "offset_end": gr_bump_x1,
         "projection": gr_bump_d, "purpose": "great_room_view_wall"},
    ]

    # Articulated polygon
    polygon = [
        # South face with foyer projection
        {"x": 0,         "y": bar_y0},
        {"x": foyer_x0,  "y": bar_y0},
        {"x": foyer_x0,  "y": bar_y0 - foyer_proj},
        {"x": foyer_x1,  "y": bar_y0 - foyer_proj},
        {"x": foyer_x1,  "y": bar_y0},
        {"x": bar_w,     "y": bar_y0},
        # East face down bar
        {"x": bar_w,     "y": bar_y1},
        # North face of bar with great room bumpout
        {"x": gr_bump_x1, "y": bar_y1},
        {"x": gr_bump_x1, "y": bar_y1 + gr_bump_d},
        {"x": gr_bump_x0, "y": bar_y1 + gr_bump_d},
        {"x": gr_bump_x0, "y": bar_y1},
        # Bar north → wing
        {"x": wing_x1,  "y": bar_y1},
        {"x": wing_x1,  "y": wing_y1},
        {"x": wing_x0,  "y": wing_y1},
        {"x": wing_x0,  "y": bar_y1},
        # Bar north west of wing
        {"x": 0,        "y": bar_y1},
    ]

    actual_sf = bar_w * bar_depth + wing_w * wing_depth
    for b in bumpouts:
        actual_sf += (b["offset_end"] - b["offset_start"]) * b["projection"]

    return {
        "shape": "t_shape",
        "total_width": bar_w + garage_w,
        "total_depth": max(wing_y1, bar_y1 + gr_bump_d),
        "polygon": polygon, "zones": zones, "bumpouts": bumpouts,
        "total_sf": actual_sf, "width": bar_w + garage_w,
        "depth": max(wing_y1, bar_y1 + gr_bump_d),
        "ceiling_heights": {
            "master": 11, "living_core": 16, "bed_wing": 10, "service": 9,
        },
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




def _expand_circulation_to_rects(spine: list) -> list:
    """Convert circulation spine segments to rect dicts {x0,y0,x1,y1,type}.
    Handles both area segments (x0≠x1) and centerline segments (x0==x1 or y0==y1).
    """
    rects = []
    for seg in spine:
        seg_type = seg.get("type", "corridor")
        x0, y0 = seg.get("x0", 0), seg.get("y0", 0)
        x1, y1 = seg.get("x1", x0), seg.get("y1", y0)
        w = float(seg.get("width", 4))
        hw = w / 2

        # Already a proper rect
        if abs(x1 - x0) > 1 and abs(y1 - y0) > 1:
            rects.append({"x0": min(x0,x1), "y0": min(y0,y1),
                          "x1": max(x0,x1), "y1": max(y0,y1),
                          "type": seg_type, "width": w})
        # Vertical centerline (x0==x1, runs N-S)
        elif abs(x1 - x0) < 0.5:
            cx = (x0 + x1) / 2
            rects.append({"x0": cx - hw, "y0": min(y0,y1),
                          "x1": cx + hw, "y1": max(y0,y1),
                          "type": seg_type, "width": w})
        # Horizontal centerline (y0==y1, runs E-W)
        elif abs(y1 - y0) < 0.5:
            cy = (y0 + y1) / 2
            rects.append({"x0": min(x0,x1), "y0": cy - hw,
                          "x1": max(x0,x1), "y1": cy + hw,
                          "type": seg_type, "width": w})
    return rects

def assign_rooms_to_zones(layout_json: dict, zones: dict, circulation_spine: list = None) -> dict:
    """Place each room into its zone with architectural logic.

    Special placement rules:
    - Front Porch → south face of footprint (entry side, min Y)
    - Back Porch  → north face of footprint (rear/view side, max Y)
    - Garage      → garage zone, full rect
    - Butler Pantry / Mudroom → service zone, adjacent to kitchen side (not garage)
    - Master rooms → master zone, master bed largest and deepest
    - Corridor    → carved from bed zone before placing secondary beds
    """
    rooms = layout_json.get("rooms", [])
    room_coords: dict = {}

    # ── Footprint extents ─────────────────────────────────────────────────
    all_x = [v for z in zones.values() for v in (z["x0"], z["x1"])]
    all_y = [v for z in zones.values() for v in (z["y0"], z["y1"])]
    fp_x0, fp_x1 = min(all_x), max(all_x)
    fp_y0, fp_y1 = min(all_y), max(all_y)  # y0=south(entry), y1=north(rear)

    # ── Carve hallway corridors from zones ────────────────────────────────
    hall_rects = []
    if circulation_spine:
        hall_rects = _expand_circulation_to_rects(circulation_spine)

    def _carve_zone(zx0, zy0, zx1, zy1):
        """Split zone into packing regions around hallways.
        Only carves L1 circulation (foyer, gallery, corridor).
        Skips landings (L2) and foyers that are subsets of living zone.
        """
        # Only carve actual corridors — not landings (L2) or foyers (part of living)
        CARVE_TYPES = {"corridor", "gallery"}
        pack_regions = [{"x0": zx0, "y0": zy0, "x1": zx1, "y1": zy1}]
        for hr in [h for h in hall_rects if h.get("type") in CARVE_TYPES]:
            hx0, hy0, hx1, hy1 = hr["x0"], hr["y0"], hr["x1"], hr["y1"]
            if not (hx0 < zx1 and hx1 > zx0 and hy0 < zy1 and hy1 > zy0):
                continue
            new_regions = []
            for reg in pack_regions:
                is_vert = (hr["x1"] - hr["x0"]) <= (hr["y1"] - hr["y0"])
                if is_vert:
                    if hx0 > reg["x0"] + 2:
                        new_regions.append({"x0": reg["x0"], "y0": reg["y0"],
                                            "x1": hx0, "y1": reg["y1"]})
                    if hx1 < reg["x1"] - 2:
                        new_regions.append({"x0": hx1, "y0": reg["y0"],
                                            "x1": reg["x1"], "y1": reg["y1"]})
                else:
                    if hy0 > reg["y0"] + 2:
                        new_regions.append({"x0": reg["x0"], "y0": reg["y0"],
                                            "x1": reg["x1"], "y1": hy0})
                    if hy1 < reg["y1"] - 2:
                        new_regions.append({"x0": reg["x0"], "y0": hy1,
                                            "x1": reg["x1"], "y1": reg["y1"]})
            if new_regions:
                pack_regions = new_regions
        return pack_regions[0] if pack_regions else {"x0": zx0, "y0": zy0, "x1": zx1, "y1": zy1}

    def _pack_rooms(room_list, zx0, zy0, zx1, zy1, zone_name):
        """Pack rooms into a zone rect.
        
        - Sizes rooms from SF with aspect ratio targets (not hard constraints)
        - Wraps rows left-to-right within zone width
        - After packing, scales all rooms proportionally to fit zone depth
        - Snaps all coords to 1ft grid so walls always connect cleanly
        - NEVER places a room outside the zone boundary
        """
        if not room_list:
            return {}

        zone_w = max(zx1 - zx0, 8.0)
        zone_d = max(zy1 - zy0, 8.0)

        ASPECT = {
            "great room": 1.4, "kitchen": 1.2, "dining": 1.3,
            "master bed": 1.2, "master bath": 1.0, "master closet": 0.8,
            "bed": 1.1, "bath": 0.9, "laundry": 1.0,
            "mudroom": 1.2, "butler pantry": 0.7, "utility": 1.0,
            "home office": 1.2, "office": 1.2, "study": 1.2,
        }
        def _get_aspect(name):
            n = name.lower()
            for k, v in ASPECT.items():
                if k in n: return v
            return 1.15

        # ── Step 1: Compute natural room dimensions from SF ───────────────
        raw = []
        for r in room_list:
            sf = r.get("sf", 100)
            rw = r.get("w") or r.get("width")
            rd = r.get("d") or r.get("depth")
            dims = r.get("dimensions") or {}
            if isinstance(dims, dict):
                rw = rw or dims.get("w") or dims.get("width")
                rd = rd or dims.get("d") or dims.get("depth")
            if not rw or not rd:
                asp = _get_aspect(r["name"])
                rw = min(math.sqrt(sf * asp), zone_w)
                rw = max(8.0, rw)
                rd = max(8.0, sf / rw)
            raw.append((r, float(rw), float(rd)))

        # ── Step 2: Row-wrap layout ───────────────────────────────────────
        rows = []   # list of rows, each row = [(room, w, d), ...]
        cur_row = []
        cur_row_w = 0.0
        for (r, rw, rd) in raw:
            if rw > zone_w:
                rw = zone_w
                rd = r.get("sf", 100) / zone_w
            if cur_row_w + rw > zone_w + 0.5 and cur_row:
                rows.append(cur_row)
                cur_row = []
                cur_row_w = 0.0
            cur_row.append((r, rw, rd))
            cur_row_w += rw
        if cur_row:
            rows.append(cur_row)

        # ── Step 3: Scale rows proportionally to fit zone_d ──────────────
        total_natural_d = sum(max(rd for (_, _, rd) in row) for row in rows)
        if total_natural_d > zone_d and total_natural_d > 0:
            scale = zone_d / total_natural_d
        else:
            scale = 1.0

        # ── Step 4: Place rooms, snapping to 1ft grid ─────────────────────
        coords = {}
        cursor_y = zy0
        for row in rows:
            row_h = max(rd for (_, _, rd) in row) * scale
            row_h = max(8.0, row_h)
            # Clamp row to zone
            if cursor_y + row_h > zy1:
                row_h = max(4.0, zy1 - cursor_y)
            cursor_x = zx0
            for (r, rw, rd) in row:
                rw_scaled = rw * min(zone_w / max(sum(w for (_, w, _) in row), 1), 1.0)
                rw_scaled = max(8.0, rw_scaled)
                # Clamp to zone
                if cursor_x + rw_scaled > zx1:
                    rw_scaled = max(4.0, zx1 - cursor_x)
                # 1ft grid snap
                x0 = round(cursor_x)
                y0 = round(cursor_y)
                x1 = round(cursor_x + rw_scaled)
                y1 = round(cursor_y + row_h)
                # Hard clamp — NEVER outside zone
                x0 = max(x0, round(zx0))
                y0 = max(y0, round(zy0))
                x1 = min(x1, round(zx1))
                y1 = min(y1, round(zy1))
                coords[r["name"]] = {
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                    "sf": r.get("sf", 100), "zone": zone_name,
                    "dims_source": "model" if r.get("w") else "derived",
                }
                cursor_x += rw_scaled
            cursor_y += row_h
            if cursor_y >= zy1:
                break  # zone full — remaining rooms skipped

        return coords

    # ── Separate rooms by special type ────────────────────────────────────
    front_porches, back_porches = [], []
    garage_rooms, service_rooms = [], []
    master_rooms, living_rooms, bed_rooms = [], [], []

    for r in rooms:
        n = r["name"].lower()
        z = _get_zone(r["name"])
        if "front porch" in n:
            front_porches.append(r)
        elif "back porch" in n or "rear porch" in n or "covered porch" in n and "back" in n:
            back_porches.append(r)
        elif "porch" in n or "patio" in n:
            back_porches.append(r)  # default unknown porches to rear
        elif "garage" in n:
            garage_rooms.append(r)
        elif z == "service":
            service_rooms.append(r)
        elif z == "master":
            master_rooms.append(r)
        elif z == "beds":
            bed_rooms.append(r)
        else:
            living_rooms.append(r)

    # ── Resolve zone rects ────────────────────────────────────────────────
    def _zone(name_candidates):
        for k in name_candidates:
            if k in zones:
                return zones[k]
        return None

    master_zone  = _zone(["master"])
    living_zone  = _zone(["living_core", "living", "great_room"])
    bed_zone     = _zone(["bed_wing", "beds"])
    service_zone = _zone(["service"])
    garage_zone  = _zone(["garage"])
    porch_zone   = _zone(["porch"])

    # ── 1. Garage — use garage zone or right portion of service ──────────
    if garage_rooms:
        gz = garage_zone or service_zone
        if gz:
            g = garage_rooms[0]
            sf = g.get("sf", 576)
            gw = math.sqrt(sf * 1.2)
            gd = sf / gw
            gx0 = gz["x0"]
            gy0 = gz["y0"]
            room_coords[g["name"]] = {
                "x0": round(gx0, 1), "y0": round(gy0, 1),
                "x1": round(gx0 + gw, 1), "y1": round(gy0 + gd, 1),
                "sf": sf, "zone": "service", "dims_source": "derived",
            }

    # ── 2. Service rooms (laundry, mudroom, pantry, utility) ─────────────
    #    Mudroom always placed flush against garage entry wall
    #    Pantry/butler pantry adjacent to kitchen (inner/living side)
    #    Laundry/utility fill remaining space
    if service_rooms and service_zone:
        sz = service_zone
        gz = garage_zone or service_zone

        # Determine garage entry face (the wall shared with service zone)
        garage_x0 = gz["x0"]  # left face of garage = right face of service zone
        garage_y0 = gz["y0"]

        # Mudroom: snap to garage entry face, at garage y0
        mudroom = next((r for r in service_rooms if "mudroom" in r["name"].lower()), None)
        if mudroom:
            sf = mudroom.get("sf", 100)
            mw = 10.0  # 10ft wide
            md = sf / mw
            md = max(8.0, md)
            room_coords[mudroom["name"]] = {
                "x0": round(garage_x0 - mw, 1), "y0": round(garage_y0, 1),
                "x1": round(garage_x0, 1), "y1": round(garage_y0 + md, 1),
                "sf": sf, "zone": "service", "dims_source": "derived",
            }

        # Remaining service rooms: pack in service zone inner side (kitchen-adjacent)
        remaining_svc = [r for r in service_rooms if r is not mudroom]
        def _svc_priority(r):
            n = r["name"].lower()
            if "pantry" in n: return 0
            if "laundry" in n: return 1
            return 2
        remaining_svc.sort(key=_svc_priority)
        if remaining_svc:
            svc_carved = _carve_zone(sz["x0"], sz["y0"], sz["x1"], sz["y1"])
            room_coords.update(_pack_rooms(remaining_svc, svc_carved["x0"], svc_carved["y0"],
                                            svc_carved["x1"], svc_carved["y1"], "service"))

    # ── 3. Master suite ───────────────────────────────────────────────────
    if master_rooms and master_zone:
        mz = master_zone
        master_carved = _carve_zone(mz["x0"], mz["y0"], mz["x1"], mz["y1"])
        # Sort: master bed first (largest), then bath, then closet
        def _master_priority(r):
            n = r["name"].lower()
            if "bed" in n: return 0
            if "bath" in n: return 1
            return 2
        master_rooms.sort(key=_master_priority)
        room_coords.update(_pack_rooms(master_rooms, master_carved["x0"], master_carved["y0"],
                                        master_carved["x1"], master_carved["y1"], "master"))

    # ── 4. Living core ────────────────────────────────────────────────────
    if living_rooms and living_zone:
        lz = living_zone
        lx0, ly0, lx1, ly1 = lz["x0"], lz["y0"], lz["x1"], lz["y1"]
        living_carved = _carve_zone(lx0, ly0, lx1, ly1)

        # Pull home office out — place it as a separate side room
        # (adjacent to entry/foyer, not stacked with great room)
        office_rooms = [r for r in living_rooms
                        if "office" in r["name"].lower() or "study" in r["name"].lower()]
        main_living  = [r for r in living_rooms if r not in office_rooms]

        main_living.sort(key=lambda r: r.get("sf", 100), reverse=True)
        room_coords.update(_pack_rooms(main_living,
            living_carved["x0"], living_carved["y0"],
            living_carved["x1"], living_carved["y1"], "living"))

        # Home office: place inside living zone, at entry corner (south side)
        if office_rooms:
            for office in office_rooms:
                sf = office.get("sf", 150)
                ow = math.sqrt(sf * 1.2)
                od = sf / max(ow, 1)
                ow = min(ow, lx1 - lx0)
                od = min(od, ly1 - ly0)
                ow = max(10.0, ow)
                od = max(10.0, od)
                # Place at SE corner of living zone (near entry/foyer)
                ox0 = round(lx1 - ow)
                oy0 = round(ly0)
                ox1 = round(lx1)
                oy1 = round(ly0 + od)
                # Hard clamp to living zone
                ox0 = max(round(lx0), ox0)
                oy1 = min(round(ly1), oy1)
                room_coords[office["name"]] = {
                    "x0": ox0, "y0": oy0, "x1": ox1, "y1": oy1,
                    "sf": sf, "zone": "living", "dims_source": "derived",
                }

    # ── 5. Secondary bedrooms — place on BOTH sides of corridor ──────────
    if bed_rooms and bed_zone:
        bz = bed_zone
        bx0, by0, bx1, by1 = bz["x0"], bz["y0"], bz["x1"], bz["y1"]

        # Find vertical corridor in this zone
        vert_corr = next(
            (h for h in hall_rects
             if h.get("type") == "corridor"
             and h["x0"] > bx0 + 2 and h["x1"] < bx1 - 2
             and h["y0"] <= by1 and h["y1"] >= by0),
            None
        )

        if vert_corr:
            # Two columns: left of corridor and right of corridor
            left  = {"x0": bx0,              "y0": by0, "x1": vert_corr["x0"], "y1": by1}
            right = {"x0": vert_corr["x1"],  "y0": by0, "x1": bx1,             "y1": by1}

            # Pair beds with baths: Bed 2+Bath 2, Bed 3+Bath 3, etc.
            beds_only  = sorted([r for r in bed_rooms if "bath" not in r["name"].lower()],
                                 key=lambda r: r["name"])
            baths_only = sorted([r for r in bed_rooms if "bath" in r["name"].lower()],
                                 key=lambda r: r["name"])

            # Build paired groups: [(bed, bath_or_None), ...]
            pairs = []
            for i, bed in enumerate(beds_only):
                bath = baths_only[i] if i < len(baths_only) else None
                pairs.append((bed, bath))

            # Alternate pairs between left/right columns
            left_rooms, right_rooms = [], []
            for i, (bed, bath) in enumerate(pairs):
                col = left_rooms if i % 2 == 0 else right_rooms
                col.append(bed)
                if bath:
                    col.append(bath)

            # Any extra baths go into the column with more space
            for bath in baths_only[len(beds_only):]:
                left_rooms.append(bath)

            if left_rooms:
                room_coords.update(_pack_rooms(left_rooms,
                    left["x0"], left["y0"], left["x1"], left["y1"], "beds"))
            if right_rooms:
                room_coords.update(_pack_rooms(right_rooms,
                    right["x0"], right["y0"], right["x1"], right["y1"], "beds"))
        else:
            # No corridor — pair beds+baths and pack normally
            beds_only  = sorted([r for r in bed_rooms if "bath" not in r["name"].lower()],
                                 key=lambda r: r["name"])
            baths_only = sorted([r for r in bed_rooms if "bath" in r["name"].lower()],
                                 key=lambda r: r["name"])
            ordered = []
            for i, bed in enumerate(beds_only):
                ordered.append(bed)
                if i < len(baths_only):
                    ordered.append(baths_only[i])
            for b in baths_only[len(beds_only):]:
                ordered.append(b)
            room_coords.update(_pack_rooms(ordered, bx0, by0, bx1, by1, "beds"))

    # ── 6. Back porch — use porch zone (attached to rear/north face) ────────
    back_porch_zone = _zone(["porch"])
    if back_porches and back_porch_zone:
        bpz = back_porch_zone
        total_sf = sum(r.get("sf", 200) for r in back_porches)
        zpw = bpz["x1"] - bpz["x0"]
        zpd = bpz["y1"] - bpz["y0"]
        px0 = bpz["x0"]
        for r in back_porches:
            sf = r.get("sf", 200)
            rw = min(zpw, sf / max(zpd, 1))
            rw = max(10, rw)
            room_coords[r["name"]] = {
                "x0": round(px0, 1), "y0": round(bpz["y0"], 1),
                "x1": round(px0 + rw, 1), "y1": round(bpz["y1"], 1),
                "sf": sf, "zone": "porch", "dims_source": "derived",
            }
            px0 += rw
    elif back_porches:
        # Fallback: attach directly to north face of footprint
        porch_d = 12
        house_cx = (fp_x0 + fp_x1) / 2
        px0 = house_cx - 15
        for r in back_porches:
            sf = r.get("sf", 200)
            rw = sf / porch_d
            room_coords[r["name"]] = {
                "x0": round(px0, 1), "y0": round(fp_y1, 1),
                "x1": round(px0 + rw, 1), "y1": round(fp_y1 + porch_d, 1),
                "sf": sf, "zone": "porch", "dims_source": "derived",
            }
            px0 += rw

    # ── 7. Front porch — use front_porch zone (attached to south/entry face) ──
    front_porch_zone = _zone(["front_porch"])
    if front_porches and front_porch_zone:
        fpz = front_porch_zone
        zpw = fpz["x1"] - fpz["x0"]
        zpd = fpz["y1"] - fpz["y0"]
        house_cx = (fp_x0 + fp_x1) / 2
        total_fp_sf = sum(r.get("sf", 150) for r in front_porches)
        porch_w = min(total_fp_sf / max(zpd, 1), zpw * 0.7)
        px0 = house_cx - porch_w / 2
        for r in front_porches:
            sf = r.get("sf", 150)
            rw = min(sf / max(zpd, 1), porch_w)
            rw = max(10, rw)
            room_coords[r["name"]] = {
                "x0": round(px0, 1), "y0": round(fpz["y0"], 1),
                "x1": round(px0 + rw, 1), "y1": round(fpz["y1"], 1),
                "sf": sf, "zone": "porch", "dims_source": "derived",
            }
            px0 += rw
    elif front_porches:
        # Fallback: attach to south face
        porch_d = 10
        house_cx = (fp_x0 + fp_x1) / 2
        px0 = house_cx - 12
        for r in front_porches:
            sf = r.get("sf", 150)
            rw = sf / porch_d
            room_coords[r["name"]] = {
                "x0": round(px0, 1), "y0": round(fp_y0 - porch_d, 1),
                "x1": round(px0 + rw, 1), "y1": round(fp_y0, 1),
                "sf": sf, "zone": "porch", "dims_source": "derived",
            }
            px0 += rw

    # ── Align front porch to foyer from circulation spine ────────────────
    # Shift front porch x to center on foyer spine segment (not house center)
    foyer_seg = next((s for s in (circulation_spine or []) if s.get("type") == "foyer"), None)
    fp_coord = next((v for k, v in room_coords.items() if "front porch" in k.lower()), None)
    fp_key = next((k for k in room_coords if "front porch" in k.lower()), None)
    if foyer_seg and fp_coord and fp_key:
        foyer_cx = (foyer_seg["x0"] + foyer_seg["x1"]) / 2
        pw = fp_coord["x1"] - fp_coord["x0"]
        room_coords[fp_key]["x0"] = round(foyer_cx - pw/2, 1)
        room_coords[fp_key]["x1"] = round(foyer_cx + pw/2, 1)

    return room_coords


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


def _normalize_layout(layout_json: dict) -> dict:
    """Normalize brain output to planner-expected format.
    
    Brain outputs rooms as dict: {"great_room": {"sf": 500, ...}}
    Planner expects rooms as list: [{"name": "Great Room", "sf": 500, ...}]
    """
    rooms = layout_json.get("rooms", [])
    if isinstance(rooms, dict):
        normalized = []
        for key, val in rooms.items():
            if isinstance(val, dict):
                # Convert snake_case key to Title Case name
                name = val.get("name") or key.replace("_", " ").title()
                room = {"name": name, **val}
                normalized.append(room)
            else:
                normalized.append({"name": key.replace("_", " ").title(), "sf": val})
        return {**layout_json, "rooms": normalized}
    return layout_json


def _correct_layout(layout_json: dict) -> dict:
    """
    Rules-based corrector for brain output mistakes.
    Fixes zone assignments, room naming, and orientation issues.
    """
    rooms = layout_json.get("rooms", [])
    if not isinstance(rooms, list):
        return layout_json

    # ── Zone correction rules ─────────────────────────────────────────────
    # Room name keywords → correct zone
    ZONE_RULES = {
        "master": [
            "master bed", "master bath", "master closet", "his closet",
            "hers closet", "wic", "walk-in closet", "master sitting",
            "master suite", "sitting room",
        ],
        "service": [
            "garage", "mudroom", "mud room", "laundry", "utility",
            "butler pantry", "pantry", "mechanical", "hvac", "storage", "utility",
        ],
        "beds": [
            "bed 2", "bed 3", "bed 4", "bed 5", "bedroom 2", "bedroom 3",
            "bedroom 4", "bedroom 5", "bath 2", "bath 3", "bath 4",
            "bathroom 2", "bathroom 3", "bathroom 4", "bonus room",
            "hallway", "corridor", "landing",
        ],
        "living": [
            "great room", "kitchen", "dining", "living room", "office",
            "home office", "study", "foyer", "entry",
        ],
        "porch": [
            "porch", "back porch", "front porch", "covered porch",
            "outdoor", "patio", "breezeway",
        ],
    }

    # ── Room name standardization ─────────────────────────────────────────
    NAME_MAP = {
        "wic": "Master Closet",
        "his wic": "His Closet",
        "hers wic": "Hers Closet",
        "walk in closet": "Master Closet",
        "walk-in closet": "Master Closet",
        "sitting": "Master Sitting Room",
        "mud room": "Mudroom",
        "half bath": "Half Bath",
        "powder room": "Half Bath",
        "powder": "Half Bath",
        "utility room": "Utility",
        "mechanical": "Utility",
        "family room": "Great Room",
        "living room": "Great Room",
    }

    corrected = []
    for room in rooms:
        r = dict(room)
        name_lower = r["name"].lower().strip()

        # Standardize name
        for old_name, new_name in NAME_MAP.items():
            if name_lower == old_name:
                r["name"] = new_name
                name_lower = new_name.lower()
                break

        # Fix zone
        for zone, keywords in ZONE_RULES.items():
            if any(kw in name_lower for kw in keywords):
                r["zone"] = zone
                break

        corrected.append(r)

    # ── Ensure master suite has required components ───────────────────────
    room_names = {r["name"].lower() for r in corrected}
    master_bed = next((r for r in corrected if "master bed" in r["name"].lower()), None)

    if master_bed:
        # Add Master Bath if missing
        if not any("master bath" in r["name"].lower() or "master bath" in r["name"].lower() for r in corrected):
            corrected.append({"name": "Master Bath", "sf": 160, "zone": "master",
                               "adjacencies": ["Master Bed"]})

        # Add Master Closet if no WIC/closet
        if not any("closet" in r["name"].lower() or "wic" in r["name"].lower() for r in corrected):
            corrected.append({"name": "Master Closet", "sf": 80, "zone": "master",
                               "adjacencies": ["Master Bed", "Master Bath"]})

    # ── Ensure mudroom if garage present ─────────────────────────────────
    has_garage = any("garage" in r["name"].lower() for r in corrected)
    has_mudroom = any("mudroom" in r["name"].lower() or "mud room" in r["name"].lower() for r in corrected)
    if has_garage and not has_mudroom:
        corrected.append({"name": "Mudroom", "sf": 100, "zone": "service",
                           "adjacencies": ["Garage", "Kitchen"]})

    return {**layout_json, "rooms": corrected}



# ══════════════════════════════════════════════════════════════════════════════
#  SPEC GENERATOR — Full resolved design spec for Revit execution
# ══════════════════════════════════════════════════════════════════════════════

def generate_spec(
    submission_id: str,
    layout_json: dict,
    intake_json: dict,
    footprint: dict,
    room_coords: dict,
    circulation: dict,
    exterior_json: dict,
) -> dict:
    """
    Generate a fully resolved design spec JSON that the Revit sub-agent
    can use directly — no re-designing from scratch.

    Returns a dict saved as spec_[id].json in designs/.
    """
    import hashlib

    # Parse stories from intake
    _brief_s = intake_json.get("brief","")
    import re as _re2
    _sm = _re2.search(r"(\d+)[-\s]story", _brief_s, _re2.IGNORECASE)
    stories = int(intake_json.get("stories") or (_sm.group(1) if _sm else 1))

    # ── Exterior walls from footprint zones ──────────────────────────────
    shape = footprint.get("shape", "rectangle")
    zones = footprint.get("zones", {})
    ext_walls = []
    EXT_HALF = 0.3125  # half of 7.5" exterior wall

    def wall(label, x0, y0, x1, y1, face):
        """face = 'S'|'N'|'E'|'W' — exterior face direction"""
        offsets = {
            'S': (0, EXT_HALF, 0, EXT_HALF),
            'N': (0, -EXT_HALF, 0, -EXT_HALF),
            'W': (EXT_HALF, 0, EXT_HALF, 0),
            'E': (-EXT_HALF, 0, -EXT_HALF, 0),
        }
        dx0, dy0, dx1, dy1 = offsets[face]
        return {
            "label": label,
            "x0": round(x0 + dx0, 4), "y0": round(y0 + dy0, 4),
            "x1": round(x1 + dx1, 4), "y1": round(y1 + dy1, 4),
            "type": "Wall 7.5\" EXT PBR",
            "face": face,
        }

    # Build exterior walls from room_coords bounding box
    all_x = [v["x0"] for v in room_coords.values()] + [v["x1"] for v in room_coords.values()]
    all_y = [v["y0"] for v in room_coords.values()] + [v["y1"] for v in room_coords.values()]
    if all_x and all_y:
        bx0, bx1 = min(all_x), max(all_x)
        by0, by1 = min(all_y), max(all_y)
        ext_walls = [
            wall("EXT-S", bx0, by0, bx1, by0, 'S'),
            wall("EXT-N", bx0, by1, bx1, by1, 'N'),
            wall("EXT-W", bx0, by0, bx0, by1, 'W'),
            wall("EXT-E", bx1, by0, bx1, by1, 'E'),
        ]

    # ── Interior walls + doors — derived geometrically from shared edges ──
    # Works even when room_coords have no adjacencies key
    EDGE_TOL = 1.5  # rooms within 1.5ft are considered adjacent

    # Open-plan pairs — no wall between these rooms (just open space)
    OPEN_PLAN_PAIRS = {
        frozenset({"Great Room", "Kitchen"}),
        frozenset({"Great Room", "Dining"}),
        frozenset({"Kitchen", "Dining"}),
        frozenset({"Great Room", "Dining Room"}),
        frozenset({"Kitchen", "Dining Room"}),
    }
    int_walls = []
    doors = []
    processed = set()
    names = list(room_coords.keys())
    
    # Skip porch zones — they don't need interior walls
    OPEN_ZONES = {"porch", "front_porch", "back_porch", "outdoor"}
    
    for i, rname in enumerate(names):
        rc = room_coords[rname]
        if rc.get("zone") in OPEN_ZONES:
            continue
        for adj in names[i+1:]:
            ac = room_coords[adj]
            if ac.get("zone") in OPEN_ZONES:
                continue
            pair = tuple(sorted([rname, adj]))
            if pair in processed:
                continue
            # Skip walls between rooms in very different zones
            # (garage↔living, garage↔master, service↔master etc.)
            ZONE_NO_WALL = {
                frozenset({"service", "master"}),
                frozenset({"service", "living"}),
                frozenset({"garage", "master"}),
                frozenset({"garage", "living"}),
                frozenset({"garage", "beds"}),
            }
            rzone = rc.get("zone", "living")
            azone = ac.get("zone", "living")
            # Treat garage rooms as "service" for this check
            if "garage" in rname.lower(): rzone = "garage"
            if "garage" in adj.lower(): azone = "garage"
            if frozenset({rzone, azone}) in ZONE_NO_WALL:
                processed.add(pair)
                continue
            
            shared_wall = None
            door_pos = None
            
            # Vertical shared edge: rc.x1 ≈ ac.x0 or rc.x0 ≈ ac.x1
            for rx, ax in [(rc["x1"], ac["x0"]), (rc["x0"], ac["x1"])]:
                if abs(rx - ax) < EDGE_TOL:
                    shared_x = (rx + ax) / 2
                    oy0 = max(rc["y0"], ac["y0"])
                    oy1 = min(rc["y1"], ac["y1"])
                    if oy1 - oy0 > 3:
                        processed.add(pair)
                        shared_wall = {
                            "label": f"INT-{rname[:6]}-{adj[:6]}",
                            "x0": round(shared_x, 2), "y0": round(oy0, 2),
                            "x1": round(shared_x, 2), "y1": round(oy1, 2),
                            "type": 'Wall 4.5 Interior"',
                            "rooms": [rname, adj],
                        }
                        door_pos = {"x": round(shared_x, 2), "y": round((oy0+oy1)/2, 2)}
                    break
            
            if shared_wall is None:
                # Horizontal shared edge: rc.y1 ≈ ac.y0 or rc.y0 ≈ ac.y1
                for ry, ay in [(rc["y1"], ac["y0"]), (rc["y0"], ac["y1"])]:
                    if abs(ry - ay) < EDGE_TOL:
                        shared_y = (ry + ay) / 2
                        ox0 = max(rc["x0"], ac["x0"])
                        ox1 = min(rc["x1"], ac["x1"])
                        if ox1 - ox0 > 3:
                            processed.add(pair)
                            shared_wall = {
                                "label": f"INT-{rname[:6]}-{adj[:6]}",
                                "x0": round(ox0, 2), "y0": round(shared_y, 2),
                                "x1": round(ox1, 2), "y1": round(shared_y, 2),
                                "type": 'Wall 4.5 Interior"',
                                "rooms": [rname, adj],
                            }
                            door_pos = {"x": round((ox0+ox1)/2, 2), "y": round(shared_y, 2)}
                        break
            
            if shared_wall:
                # Skip wall if this is an open-plan pair
                pair_set = frozenset([rname, adj])
                is_open_plan = any(
                    all(r.lower() in p_name.lower() or p_name.lower() in r.lower()
                        for r, p_name in zip(sorted(pair_set), sorted(p)))
                    for p in OPEN_PLAN_PAIRS
                    if len(p) == 2
                ) or pair_set in OPEN_PLAN_PAIRS
                if is_open_plan:
                    continue
                int_walls.append(shared_wall)
                doors.append({
                    "label": f"DOOR-{rname[:6]}-{adj[:6]}",
                    "wall_label": shared_wall["label"],
                    "x": door_pos["x"], "y": door_pos["y"], "z": 0,
                    "family": "Door-Interior-Single-1_Panel-Wood",
                    "type": '36" x 96"',
                    "rooms": [rname, adj],
                })

    # ── Hardcoded architectural doors (garage→mudroom, etc.) ────────────
    # Always add a door between garage and mudroom if both exist and adjacent
    garage_coord = next((v for k, v in room_coords.items() if "garage" in k.lower()), None)
    mudroom_coord = next((v for k, v in room_coords.items() if "mudroom" in k.lower() or "mud room" in k.lower()), None)
    if garage_coord and mudroom_coord:
        # Check adjacency
        gx0,gy0,gx1,gy1 = garage_coord["x0"],garage_coord["y0"],garage_coord["x1"],garage_coord["y1"]
        mx0,my0,mx1,my1 = mudroom_coord["x0"],mudroom_coord["y0"],mudroom_coord["x1"],mudroom_coord["y1"]
        # Shared vertical edge
        for gx, mx in [(gx0, mx1), (gx1, mx0)]:
            if abs(gx - mx) < 2.0:
                shared_y0 = max(gy0, my0)
                shared_y1 = min(gy1, my1)
                if shared_y1 - shared_y0 > 3:
                    mid_y = (shared_y0 + shared_y1) / 2
                    shared_x = (gx + mx) / 2
                    doors.append({
                        "label": "DOOR-Garage-Mudroom",
                        "wall_label": "INT-Garage-Mudroom",
                        "x": round(shared_x, 1), "y": round(mid_y, 1), "z": 0,
                        "family": "Door-Interior-Single-1_Panel-Wood",
                        "type": '36" x 96"',
                        "rooms": ["Garage", "Mudroom"],
                    })
                    break
        # Shared horizontal edge
        for gy, my in [(gy0, my1), (gy1, my0)]:
            if abs(gy - my) < 2.0:
                shared_x0 = max(gx0, mx0)
                shared_x1 = min(gx1, mx1)
                if shared_x1 - shared_x0 > 3:
                    mid_x = (shared_x0 + shared_x1) / 2
                    shared_y = (gy + my) / 2
                    doors.append({
                        "label": "DOOR-Garage-Mudroom",
                        "wall_label": "INT-Garage-Mudroom",
                        "x": round(mid_x, 1), "y": round(shared_y, 1), "z": 0,
                        "family": "Door-Interior-Single-1_Panel-Wood",
                        "type": '36" x 96"',
                        "rooms": ["Garage", "Mudroom"],
                    })
                    break

    # ── Windows — rear/view wall gets max glass, others standard ─────────
    windows = []
    if all_y:
        rear_y = by0  # south face = rear/view wall
        for rname, rc in room_coords.items():
            if abs(rc["y0"] - rear_y) < 2.0:
                w = rc["x1"] - rc["x0"]
                if w >= 8:
                    windows.append({
                        "label": f"WIN-{rname[:8]}-rear",
                        "wall": "EXT-S",
                        "x": round((rc["x0"] + rc["x1"]) / 2, 1),
                        "y": round(rear_y, 1), "z": 2.5,
                        "family": "Instance-Window-Fixed",
                        "type": "72\" x 36\"",
                    })

    # ── Footprint polygon ─────────────────────────────────────────────────
    footprint_polygon = []
    if all_x and all_y:
        footprint_polygon = [
            {"x": round(bx0, 1), "y": round(by0, 1)},
            {"x": round(bx1, 1), "y": round(by0, 1)},
            {"x": round(bx1, 1), "y": round(by1, 1)},
            {"x": round(bx0, 1), "y": round(by1, 1)},
        ]

    # ── Assemble spec ─────────────────────────────────────────────────────
    spec = {
        "spec_version": "1.0",
        "submission_id": submission_id,
        "name": intake_json.get("name", ""),
        "shape": shape,
        "total_sf": intake_json.get("living") or intake_json.get("total_sf") or sum(v.get("sf",0) for v in room_coords.values()),
        "stories": stories,
        "footprint_polygon": footprint_polygon,
        "footprint_dimensions": {
            "width_ft": footprint.get("total_width"),
            "depth_ft": footprint.get("total_depth"),
        },
        "zones": footprint.get("zones", {}),
        "rooms": room_coords,
        "exterior_walls": ext_walls,
        "interior_walls": int_walls,
        "doors": doors,
        "windows": windows,
        "circulation": circulation,
        "exterior_style": exterior_json,
        "revit_config": {
            "level_1": "Level 1.0",
            "level_2": "Level 2.0",
            "ext_wall_type": "Wall 7.5\" EXT PBR",
            "int_wall_type": "Wall 4.5 Interior\"",
            "wall_height_l1": 11,
            "wall_height_garage": 12,
            "upper_limit_l1": "Level 2.0",
            "upper_limit_l2": "L2 Roof",
            "ext_half": EXT_HALF,
        },
    }

    # Save to file
    spec_path = os.path.join("designs", f"spec_{submission_id[:8]}.json")
    os.makedirs("designs", exist_ok=True)
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"✅ Spec saved: {spec_path}")
    return spec


def _upload_spec_to_supabase(spec: dict, submission_id: str) -> str:
    """Upload spec JSON to Supabase storage and return public URL."""
    bucket = "temp"
    storage_path = f"{submission_id}/spec_{submission_id[:8]}.json"
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"

    data = json.dumps(spec, indent=2).encode()
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "x-upsert": "true",
    }
    resp = requests.post(url, headers=headers, data=data)
    if resp.status_code == 400:
        resp = requests.put(url, headers=headers, data=data)

    if resp.status_code in (200, 201):
        return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{storage_path}"
    return f"Spec upload failed ({resp.status_code}): {resp.text}"


def render_spec_floorplan(spec: dict, output_path: str) -> str:
    """
    Render a precise architectural floor plan from a resolved spec JSON.
    Shows: room outlines + labels, interior walls, door openings, window marks.
    Returns output_path.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import FancyArrowPatch
    import numpy as np

    rooms      = spec.get("rooms", {})
    int_walls  = spec.get("interior_walls", [])
    ext_walls  = spec.get("exterior_walls", [])
    doors      = spec.get("doors", [])
    windows    = spec.get("windows", [])
    fp         = spec.get("footprint_polygon", [])
    name       = spec.get("name", "Floor Plan")
    sid        = spec.get("submission_id", "")[:8]
    _circ      = spec.get("circulation", {})
    _spine     = _circ.get("spine", []) if isinstance(_circ, dict) else []
    hall_rects = _expand_circulation_to_rects(_spine)

    # ── Canvas ──────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 14))
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("#F8F5F0")
    ax.set_facecolor("#F8F5F0")

    # ── Zone colors (light fill for rooms) ───────────────────────────────
    ZONE_FILL = {
        "master":      "#D6E8F5",
        "living":      "#FFF3E0",
        "beds":        "#E8F5E9",
        "service":     "#ECEFF1",
        "porch":       "#FFF9C4",
        "garage":      "#ECEFF1",
    }
    ZONE_DEFAULT = "#F5F5F5"

    # ── Collect all coords for axis limits ───────────────────────────────
    all_x, all_y = [], []
    for r in rooms.values():
        all_x += [r["x0"], r["x1"]]
        all_y += [r["y0"], r["y1"]]
    if not all_x:
        plt.close(fig)
        return output_path

    pad = 6
    ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
    ax.set_ylim(min(all_y) - pad, max(all_y) + pad + 12)  # top space for title

    # ── Draw footprint shadow ─────────────────────────────────────────────
    if fp and len(fp) >= 3:
        xs = [p["x"] for p in fp] + [fp[0]["x"]]
        ys = [p["y"] for p in fp] + [fp[0]["y"]]
        ax.fill(xs, ys, color="#E0D8CC", zorder=0, alpha=0.5)

    # ── Draw rooms (filled rect + thin border) ────────────────────────────
    OPEN_ZONES = {"porch", "front_porch", "back_porch", "outdoor"}
    for rname, r in rooms.items():
        zone = r.get("zone", "living")
        fill = ZONE_FILL.get(zone, ZONE_DEFAULT)
        is_open = zone in OPEN_ZONES

        rect = patches.Rectangle(
            (r["x0"], r["y0"]),
            r["x1"] - r["x0"],
            r["y1"] - r["y0"],
            linewidth=0.5 if is_open else 1.0,
            edgecolor="#AAAAAA" if is_open else "#888888",
            facecolor=fill,
            linestyle="--" if is_open else "-",
            zorder=1,
        )
        ax.add_patch(rect)

        # Room label
        cx = (r["x0"] + r["x1"]) / 2
        cy = (r["y0"] + r["y1"]) / 2
        sf = r.get("sf", 0)
        label = f"{rname}\n{sf} SF" if sf else rname
        fontsize = 7.5 if (r["x1"]-r["x0"]) > 10 else 6
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=fontsize, color="#333333",
                fontfamily="monospace", zorder=4,
                multialignment="center")

    # ── Draw circulation / hallways ──────────────────────────────────────
    HALL_COLORS = {
        "foyer":    "#E8D5B0",
        "gallery":  "#DDD0B8",
        "corridor": "#D8CCB0",
    }
    for hr in hall_rects:
        htype = hr.get("type", "corridor")
        
        # Landing = L2 open railing — render as dashed outline, no fill
        if htype == "landing":
            hrect = patches.Rectangle(
                (hr["x0"], hr["y0"]),
                hr["x1"] - hr["x0"],
                hr["y1"] - hr["y0"],
                linewidth=1.5,
                edgecolor="#AAAAAA",
                facecolor="none",
                linestyle="--",
                zorder=3,
            )
            ax.add_patch(hrect)
            hcx = (hr["x0"] + hr["x1"]) / 2
            hcy = (hr["y0"] + hr["y1"]) / 2
            ax.text(hcx, hcy, "open\\nto below", ha="center", va="center",
                    fontsize=6, color="#999999", style="italic", zorder=4)
            continue

        hcolor = HALL_COLORS.get(htype, "#DDD5C0")
        hrect = patches.Rectangle(
            (hr["x0"], hr["y0"]),
            hr["x1"] - hr["x0"],
            hr["y1"] - hr["y0"],
            linewidth=1.0,
            edgecolor="#999999",
            facecolor=hcolor,
            linestyle=":",
            zorder=2,
            alpha=0.8,
        )
        ax.add_patch(hrect)
        # Label
        hcx = (hr["x0"] + hr["x1"]) / 2
        hcy = (hr["y0"] + hr["y1"]) / 2
        hlabel = htype.title()
        hl = hr["x1"] - hr["x0"]
        hd = hr["y1"] - hr["y0"]
        if hl > 3 and hd > 3:
            ax.text(hcx, hcy, hlabel, ha="center", va="center",
                    fontsize=6, color="#666666", style="italic",
                    rotation=90 if hd > hl else 0, zorder=4)

    # ── Draw interior walls (thick lines) ─────────────────────────────────
    for w in int_walls:
        ax.plot(
            [w["x0"], w["x1"]], [w["y0"], w["y1"]],
            color="#555555", linewidth=2.5, solid_capstyle="butt", zorder=3
        )

    # ── Draw door openings (gap + arc) ────────────────────────────────────
    DOOR_W = 3.0  # ft
    for d in doors:
        dx, dy = d["x"], d["y"]
        # Find which wall this door is on to determine orientation
        wall_label = d.get("wall_label", "")
        wall = next((w for w in int_walls if w["label"] == wall_label), None)
        if wall is None:
            # guess orientation from door position
            is_horiz = True
        else:
            is_horiz = (wall["y0"] == wall["y1"])  # horizontal wall

        # Draw gap (erase wall segment) as white rectangle
        hw = DOOR_W / 2
        if is_horiz:
            gap = patches.Rectangle((dx - hw, dy - 0.3), DOOR_W, 0.6,
                                     facecolor="#F8F5F0", edgecolor="none", zorder=5)
            # Arc showing swing direction
            arc = patches.Arc((dx - hw, dy), DOOR_W, DOOR_W,
                               angle=0, theta1=0, theta2=90,
                               color="#888888", linewidth=1.0, zorder=5)
        else:
            gap = patches.Rectangle((dx - 0.3, dy - hw), 0.6, DOOR_W,
                                     facecolor="#F8F5F0", edgecolor="none", zorder=5)
            arc = patches.Arc((dx, dy - hw), DOOR_W, DOOR_W,
                               angle=0, theta1=0, theta2=90,
                               color="#888888", linewidth=1.0, zorder=5)
        ax.add_patch(gap)
        ax.add_patch(arc)

    # ── Draw exterior walls (heavy lines) ─────────────────────────────────
    EXT_LW = 4.0
    for w in ext_walls:
        ax.plot(
            [w["x0"], w["x1"]], [w["y0"], w["y1"]],
            color="#222222", linewidth=EXT_LW, solid_capstyle="butt", zorder=6
        )

    # ── Draw window marks (dashed lines on ext walls) ─────────────────────
    WIN_W = 3.0
    for win in windows:
        wx, wy = win["x"], win["y"]
        # Determine orientation from wall label
        wlabel = win.get("wall", "")
        if "EXT-S" in wlabel or "EXT-N" in wlabel:
            # horizontal window mark
            ax.plot([wx - WIN_W/2, wx + WIN_W/2], [wy, wy],
                    color="#4FC3F7", linewidth=3, zorder=7)
            ax.plot([wx - WIN_W/2, wx + WIN_W/2], [wy, wy],
                    color="white", linewidth=1, linestyle="--", zorder=8)
        else:
            ax.plot([wx, wx], [wy - WIN_W/2, wy + WIN_W/2],
                    color="#4FC3F7", linewidth=3, zorder=7)
            ax.plot([wx, wx], [wy - WIN_W/2, wy + WIN_W/2],
                    color="white", linewidth=1, linestyle="--", zorder=8)

    # ── North arrow ───────────────────────────────────────────────────────
    ax_xmin = min(all_x) - pad
    ax_ymax = max(all_y) + pad + 10
    ax.annotate("", xy=(ax_xmin + 2, ax_ymax - 1),
                xytext=(ax_xmin + 2, ax_ymax - 5),
                arrowprops=dict(arrowstyle="->", color="#333333", lw=2))
    ax.text(ax_xmin + 2, ax_ymax, "N", ha="center", va="top",
            fontsize=11, fontweight="bold", color="#333333")

    # ── Legend ────────────────────────────────────────────────────────────
    legend_x = max(all_x) + 0.5
    legend_y = max(all_y) + pad + 9
    legend_items = [
        ("Master", ZONE_FILL["master"]),
        ("Living",  ZONE_FILL["living"]),
        ("Beds",    ZONE_FILL["beds"]),
        ("Service", ZONE_FILL["service"]),
        ("Porch",   ZONE_FILL["porch"]),
    ]
    for i, (lbl, clr) in enumerate(legend_items):
        lx = legend_x
        ly = legend_y - i * 2.5
        rect = patches.Rectangle((lx, ly - 1), 3, 2,
                                   facecolor=clr, edgecolor="#888888", linewidth=0.8)
        ax.add_patch(rect)
        ax.text(lx + 3.5, ly, lbl, va="center", fontsize=8, color="#333333")

    # ── Title block ───────────────────────────────────────────────────────
    title_y = max(all_y) + pad + 11
    title_cx = (min(all_x) + max(all_x)) / 2
    dims = spec.get("footprint_dimensions", {})
    sf_total = spec.get("total_sf", 0)
    stories = spec.get("stories", 1)
    rooms_list = list(rooms.keys())
    beds = sum(1 for r in rooms_list if "bed" in r.lower() and "bath" not in r.lower() and "master" not in r.lower())
    baths = sum(1 for r in rooms_list if "bath" in r.lower())

    ax.text(title_cx, title_y + 1, name, ha="center", va="bottom",
            fontsize=16, fontweight="bold", color="#1A1A1A")
    ax.text(title_cx, title_y - 0.5,
            f"{sf_total:,} SF  |  {stories}-story  |  {beds+1} bed / {baths} bath  |  {dims.get('width_ft',0)}ft × {dims.get('depth_ft',0)}ft",
            ha="center", va="bottom", fontsize=9, color="#555555")
    ax.text(title_cx, title_y - 2.5, f"ID: {sid}",
            ha="center", va="bottom", fontsize=7, color="#AAAAAA")

    # ── Scale bar ─────────────────────────────────────────────────────────
    sb_x = min(all_x)
    sb_y = min(all_y) - pad + 1
    scale_len = 20
    ax.plot([sb_x, sb_x + scale_len], [sb_y, sb_y], color="#333333", lw=2)
    ax.plot([sb_x, sb_x], [sb_y - 0.5, sb_y + 0.5], color="#333333", lw=2)
    ax.plot([sb_x + scale_len, sb_x + scale_len], [sb_y - 0.5, sb_y + 0.5], color="#333333", lw=2)
    ax.text(sb_x + scale_len/2, sb_y - 1.5, "20 ft", ha="center", fontsize=8, color="#333333")

    plt.tight_layout(pad=0.5)
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✅ Spec floor plan rendered: {output_path}")
    return output_path

# ══════════════════════════════════════════════════════════════════════════════
#  SPATIAL MODEL — barnhaus-spatial-v1
#  Calls fine-tuned GPT-4o to generate exact room coordinates from brief
# ══════════════════════════════════════════════════════════════════════════════

SPATIAL_MODEL_V1 = "ft:gpt-4o-2024-08-06:personal:barnhaus-spatial-v1:DIs2DYf4"
SPATIAL_MODEL_V2 = "ft:gpt-4o-2024-08-06:personal:barnhaus-spatial-v2:pending"  # job: ftjob-5puub8YwRC6kaiQz0AppSSGX — update ID when done
SPATIAL_MODEL = SPATIAL_MODEL_V1  # switch to V2 once training is done

def solve_spatial_layout(layout_json: dict, intake_json: dict, footprint: dict) -> dict:
    """Call barnhaus-spatial-v1 to get exact room x/y coordinates.
    
    Returns room_coords dict: {room_name: {x0,y0,x1,y1,sf,zone}}
    Falls back to assign_rooms_to_zones() if model call fails.
    """
    import openai, os, json as _json

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  No OPENAI_API_KEY — falling back to rule-based layout")
        return None

    # Build brief for spatial model
    rooms = layout_json.get("rooms", [])
    if isinstance(rooms, list):
        room_list = ", ".join(
            f"{r['name']} ({r.get('sf',100)} SF)" for r in rooms
        )
    else:
        room_list = ", ".join(
            f"{k.replace('_',' ').title()} ({v.get('sf',100) if isinstance(v,dict) else v} SF)"
            for k, v in rooms.items()
        )

    # Fields may be top-level OR embedded in brief string — parse both
    _brief     = intake_json.get("brief", "")
    def _from_brief(pattern, default):
        import re as _re
        m = _re.search(pattern, _brief, _re.IGNORECASE)
        return m.group(1).strip() if m else default

    total_sf   = (intake_json.get("living") or
                  _from_brief(r"(\d+)\s*SF\s*living", None) or
                  _from_brief(r"(\d+)\s*SF", None) or
                  sum(r.get("sf",100) for r in (rooms if isinstance(rooms,list) else [])))
    total_sf   = int(str(total_sf).replace(",","").split()[0]) if total_sf else 2500

    shape      = (intake_json.get("house_shape") or
                  layout_json.get("footprint") or
                  _from_brief(r"footprint:\s*([a-z_\-]+)", "rectangle"))

    stories_raw = (intake_json.get("stories") or
                   _from_brief(r"(\d+)[-\s]story", None) or
                   _from_brief(r"(\d+)\s*stories", None) or 1)
    stories    = int(str(stories_raw).split()[0]) if stories_raw else 1

    style      = (intake_json.get("style") or
                  _from_brief(r"style:\s*([\w\s]+?)(?:\n|-|,)", "Hill Country"))
    fp_dims    = footprint.get("footprint_dimensions") or {}
    fp_w       = fp_dims.get("width_ft") or footprint.get("total_width", 80)
    fp_d       = fp_dims.get("depth_ft") or footprint.get("total_depth", 60)

    # Get zone boundaries from footprint
    zones = footprint.get("zones", {})
    zone_summary = []
    for zname, zv in zones.items():
        if isinstance(zv, dict):
            zone_summary.append(
                f"{zname}: x={zv['x0']}-{zv['x1']}, y={zv['y0']}-{zv['y1']}"
            )

    # Build room list with SF hints (match training prompt format)
    rooms_list_raw = layout_json.get("rooms", [])
    if isinstance(rooms_list_raw, list):
        room_sf_hints = ", ".join(
            f"{r['name']} ({r.get('sf',100)} SF)" for r in rooms_list_raw
        )
    else:
        room_sf_hints = ", ".join(
            f"{k.replace('_',' ').title()} ({v.get('sf',100) if isinstance(v,dict) else v} SF)"
            for k, v in rooms_list_raw.items()
        )

    # Match the original training prompt format — simple brief, no zone constraints
    garage_attach = (intake_json.get("garage_attachment") or
                     _from_brief(r"garage:\s*([\w\s\-]+?)(?:\n|,)", "attached right"))
    master_loc    = intake_json.get("master_location", "far end, rear corner")
    street_face   = intake_json.get("street_facing", "south")
    view_face     = "north" if street_face == "south" else "south"

    # Client bubble positions — spatial intent from intake form
    import json as _json2
    bubbles_raw = intake_json.get("bubble_positions") or _from_brief(r"bubble positions:\s*(\{[^}]+\})", None)
    bubble_hint = ""
    if bubbles_raw:
        try:
            bubbles = _json2.loads(bubbles_raw) if isinstance(bubbles_raw, str) else bubbles_raw
            if bubbles:
                bubble_hint = "\n- Client room positions (relative x,y from intake): " + ", ".join(
                    f"{k}≈({int(v.get('x',0))},{int(v.get('y',0))})" 
                    for k,v in list(bubbles.items())[:8]
                )
        except:
            pass

    prompt = f"""Design a new Barnhaus Steel Builders home with the following requirements:
- Living area: {total_sf} SF, {stories}-story
- Footprint: {shape} — {fp_w}ft wide x {fp_d}ft deep
- Style: {style} barndominium
- Garage: {garage_attach}
- Primary view/hero elevation: {view_face} face
- Rooms: {room_sf_hints}{bubble_hint}
- Master suite: {master_loc}
- All rooms connected — no isolated sections
- Front porch leads into foyer or great room (never a bedroom)
- Corridor stays inside footprint
- Garage shares wall with mudroom"""

    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=SPATIAL_MODEL,
            messages=[
                {"role": "system", "content": "You are a Barnhaus spatial layout engine. Given a design brief, output structured room coordinates as JSON. CRITICAL: Use the exact room widths and depths provided in the prompt. NEVER use 10x10 placeholder sizes. Rooms must not overlap. Each room x1-x0 and y1-y0 must match the target dimensions given."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = _json.loads(raw)

        # Normalize output — model returns {"rooms": {...}} or just {...}
        rooms_out = data.get("rooms", data)

        # Detect v2 adjacency graph output vs v1 coordinate output
        first_rv = next((v for v in rooms_out.values() if isinstance(v, dict)), {})
        is_v2 = "adjacent_to" in first_rv and "x0" not in first_rv

        if is_v2:
            print("  spatial-v2 adjacency graph detected → running graph packer")
            from barnhaus_graph_packer import pack as _graph_pack
            room_coords = _graph_pack(rooms_out, footprint)
            for rname, rc in room_coords.items():
                rc["dims_source"] = "spatial_v2_packed"
        else:
            room_coords = {}
            for rname, rv in rooms_out.items():
                if not isinstance(rv, dict):
                    continue
                if "x0" not in rv:
                    continue
                room_coords[rname] = {
                    "x0": float(rv["x0"]), "y0": float(rv["y0"]),
                    "x1": float(rv["x1"]), "y1": float(rv["y1"]),
                    "sf": rv.get("sf", 100),
                    "zone": rv.get("zone", "living"),
                    "dims_source": "spatial_v1",
                }

        # Apply zone corrections
        for rname, rc in room_coords.items():
            correct_zone = _get_zone(rname)
            if correct_zone != "living":  # living is default — trust model on living
                rc["zone"] = correct_zone

        # Fix SF labels from brain output — don't move rooms, just correct the numbers
        rooms_src = layout_json.get("rooms", [])
        if isinstance(rooms_src, list):
            sf_lookup = {r["name"]: r.get("sf",100) for r in rooms_src if isinstance(r,dict)}
        else:
            sf_lookup = {k.replace("_"," ").title(): v.get("sf",100) if isinstance(v,dict) else v
                         for k,v in rooms_src.items()}
        for rname, rc in room_coords.items():
            if rname in sf_lookup:
                rc["sf"] = sf_lookup[rname]

        print(f"✅ Spatial model placed {len(room_coords)} rooms")
        return room_coords

    except Exception as e:
        print(f"⚠️  Spatial model error: {e} — falling back to rule-based layout")
        return None


def run_planner(
    submission_id: str,
    layout_json: dict,
    intake_json: dict,
) -> dict:
    """Full pipeline: validate -> solve -> assign -> render -> upload -> spec."""
    layout_json = _normalize_layout(layout_json)
    layout_json = _correct_layout(layout_json)
    violations = validate_layout(layout_json, intake_json)
    footprint = solve_footprint(layout_json, intake_json)
    circulation = solve_circulation(layout_json, footprint["zones"], intake_json)
    # Try spatial model first — falls back to rule-based if it fails
    room_coords = solve_spatial_layout(layout_json, intake_json, footprint)
    if room_coords is None:
        room_coords = assign_rooms_to_zones(layout_json, footprint["zones"], circulation_spine=circulation.get("spine", []) if isinstance(circulation, dict) else [])
    # Generate fully resolved spec for Revit execution
    exterior_json = intake_json.get("exterior", {})
    spec = generate_spec(
        submission_id, layout_json, intake_json,
        footprint, room_coords, circulation, exterior_json
    )
    spec_url = _upload_spec_to_supabase(spec, submission_id)
    print(f"Spec URL: {spec_url}")

    # Render precise floor plan from spec (walls, doors, windows, labels)
    sid8 = submission_id[:8]
    image_path = f"designs/floorplan_{sid8}.png"
    render_spec_floorplan(spec, image_path)
    floorplan_url = _upload_to_supabase(image_path, submission_id)

    return {
        "violations": violations,
        "footprint": footprint,
        "room_coords": room_coords,
        "circulation": circulation,
        "floorplan_url": floorplan_url,
        "spec_url": spec_url,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    import sys, os
    # Run from workspace root so relative "designs/" path works
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(workspace)
    if len(sys.argv) < 2:
        print("Usage: python3 barnhaus_planner.py <submission_id_prefix>")
        sys.exit(1)
    prefix = sys.argv[1]
    import glob
    matches = glob.glob(f"designs/design_{prefix}*.json")
    if not matches:
        print(f"No design file found for prefix: {prefix}")
        sys.exit(1)
    design_path = matches[0]
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


