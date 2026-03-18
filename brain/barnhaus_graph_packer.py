"""
barnhaus_graph_packer.py — Row-fill zone packer (v3)

Algorithm:
1. Group rooms by zone (master, living, beds, service, garage, porch)
2. For each zone, sort rooms largest->smallest
3. Fill rows left->right within zone bounds, wrapping to next row
4. Stretch rooms horizontally to fill zone width (no gaps, no overlaps)
"""
from __future__ import annotations
import math
from typing import Dict, List, Tuple

GRID = 1.0

def snap(v):
    return round(v / GRID) * GRID

# ── Zone routing ─────────────────────────────────────────────────────────────
def zone_for_room(name: str) -> str:
    n = name.lower()
    if "garage" in n:                                           return "garage"
    if "front porch" in n or ("porch" in n and "front" in n):  return "front_porch"
    if "back porch" in n  or ("porch" in n and "back" in n):   return "back_porch"
    if "porch" in n or "deck" in n or "balcony" in n:          return "back_porch"
    if "master" in n:                                           return "master"
    if "bed" in n and "bath" not in n:                          return "beds"
    if "bath" in n and "master" not in n:                       return "beds"
    if n in ("mudroom","laundry","utility","utility room","mechanical","storage"): return "service"
    if "pantry" in n or "butler" in n:                          return "living"
    return "living"

# ── Zone bounds ───────────────────────────────────────────────────────────────
def get_zone_bounds(shape, fp_w, fp_d, fp_zones):
    s = (shape or "rectangle").lower().replace(" ","-").replace("_","-")
    bounds = {}

    def _z(keys, fallback):
        for k in keys:
            if k in fp_zones:
                z = fp_zones[k]
                return {"x0":max(0,z["x0"]),"y0":max(0,z["y0"]),"x1":min(fp_w,z["x1"]),"y1":min(fp_d,z["y1"])}
        return fallback

    if s == "h-shape":
        bounds["master"]      = _z(["master","left_wing"],              {"x0":0,          "y0":0,         "x1":fp_w*0.28, "y1":fp_d*0.65})
        bounds["living"]      = _z(["center_bridge","living_core","living"],{"x0":fp_w*0.28,"y0":0,       "x1":fp_w*0.72, "y1":fp_d*0.65})
        bounds["beds"]        = _z(["bed_wing","right_wing","beds"],    {"x0":fp_w*0.72,  "y0":0,         "x1":fp_w,      "y1":fp_d*0.65})
        bounds["service"]     = _z(["service"],                         {"x0":0,          "y0":fp_d*0.50, "x1":fp_w*0.28, "y1":fp_d*0.70})
        bounds["garage"]      = _z(["garage"],                          {"x0":0,          "y0":fp_d*0.60, "x1":fp_w*0.28, "y1":fp_d})
        # Porches snap to bridge front/back face
        bz = bounds["living"]
        bounds["front_porch"] = {"x0":bz["x0"], "y0":0,         "x1":bz["x1"], "y1":fp_d*0.12}
        bounds["back_porch"]  = {"x0":bz["x0"], "y0":fp_d*0.88, "x1":bz["x1"], "y1":fp_d}
    elif s in ("l-shape","asymmetric-l"):
        bounds["master"]      = _z(["master","left_wing"],  {"x0":0,         "y0":0,        "x1":fp_w*0.50, "y1":fp_d})
        bounds["living"]      = _z(["living_core","living"],{"x0":fp_w*0.30, "y0":0,        "x1":fp_w,      "y1":fp_d*0.55})
        bounds["beds"]        = _z(["bed_wing","beds"],     {"x0":fp_w*0.50, "y0":0,        "x1":fp_w,      "y1":fp_d*0.55})
        bounds["service"]     = {"x0":0,         "y0":fp_d*0.65, "x1":fp_w*0.40, "y1":fp_d}
        bounds["garage"]      = _z(["garage"],              {"x0":fp_w*0.55, "y0":fp_d*0.55,"x1":fp_w,      "y1":fp_d})
        bounds["front_porch"] = {"x0":fp_w*0.25, "y0":0,         "x1":fp_w*0.75, "y1":fp_d*0.12}
        bounds["back_porch"]  = {"x0":fp_w*0.10, "y0":fp_d*0.88, "x1":fp_w*0.60, "y1":fp_d}
    else:
        bounds["master"]      = _z(["master"],  {"x0":0,         "y0":0,        "x1":fp_w*0.35, "y1":fp_d*0.55})
        bounds["living"]      = _z(["living_core","living"],{"x0":fp_w*0.25,"y0":0,"x1":fp_w*0.75,"y1":fp_d*0.65})
        bounds["beds"]        = _z(["beds"],    {"x0":fp_w*0.60, "y0":0,        "x1":fp_w,      "y1":fp_d*0.55})
        bounds["service"]     = {"x0":0,         "y0":fp_d*0.55, "x1":fp_w*0.35,"y1":fp_d}
        bounds["garage"]      = _z(["garage"],  {"x0":0,         "y0":fp_d*0.60, "x1":fp_w*0.30,"y1":fp_d})
        bounds["front_porch"] = {"x0":fp_w*0.25,"y0":0,         "x1":fp_w*0.75,"y1":fp_d*0.12}
        bounds["back_porch"]  = {"x0":fp_w*0.25,"y0":fp_d*0.88, "x1":fp_w*0.75,"y1":fp_d}

    return bounds

# ── Row-fill engine ───────────────────────────────────────────────────────────
def _target_dims(sf, zone_w):
    sf = max(sf, 36)
    for aspect in [1.5, 1.2, 1.0, 2.0, 0.8]:
        w = math.sqrt(sf * aspect)
        d = sf / w
        w = snap(min(w, zone_w))
        d = snap(d)
        if w >= 6 and d >= 6:
            return w, d
    return max(snap(min(math.sqrt(sf), zone_w)), 6.0), max(snap(sf / max(math.sqrt(sf),1)), 6.0)

def _fill_zone(rooms, zb, zone_key):
    zw = zb["x1"] - zb["x0"]
    zd = zb["y1"] - zb["y0"]
    if zw <= 0 or zd <= 0 or not rooms:
        return []

    rooms = sorted(rooms, key=lambda r: -r["sf"])
    placed = []
    cursor_y = zb["y0"]
    remaining = list(rooms)

    while remaining and cursor_y < zb["y1"] - 2:
        row = []
        row_width = 0.0
        row_depth = 0.0
        i = 0
        while i < len(remaining):
            rm = remaining[i]
            w, d = _target_dims(rm["sf"], zw - row_width)
            w = min(w, zw - row_width)
            if w < 4:
                i += 1
                continue
            row.append({**rm, "_w": w, "_d": d})
            row_width += w
            row_depth = max(row_depth, d)
            remaining.pop(i)
            if row_width >= zw * 0.80:
                break

        if not row:
            break

        row_depth = snap(min(row_depth, zb["y1"] - cursor_y))
        if row_depth < 4:
            break

        # Stretch to fill zone width exactly
        scale = zw / max(row_width, 0.01)
        x = zb["x0"]
        for j, rm in enumerate(row):
            w = snap(rm["_w"] * scale)
            if j == len(row) - 1:
                w = snap(zb["x1"] - x)
            w = max(w, 4.0)
            placed.append({
                "name": rm["name"], "sf": rm["sf"], "zone": zone_key,
                "x0": snap(x), "y0": snap(cursor_y),
                "x1": snap(x + w), "y1": snap(cursor_y + row_depth),
            })
            x += w

        cursor_y = snap(cursor_y + row_depth)

    return placed

# ── Void zones (for renderer) ─────────────────────────────────────────────────
def get_real_voids(shape, fp_w, fp_d, fp_zones):
    s = (shape or "rectangle").lower().replace(" ","-").replace("_","-")
    voids = []
    if s == "h-shape" and fp_zones:
        lw = fp_zones.get("master") or fp_zones.get("left_wing")
        br = fp_zones.get("center_bridge") or fp_zones.get("living_core") or fp_zones.get("living")
        rw = fp_zones.get("bed_wing") or fp_zones.get("right_wing") or fp_zones.get("beds")
        if lw and br and rw:
            lx1=lw["x1"]; bx0=br["x0"]; bx1=br["x1"]; rx0=rw["x0"]
            by0=br["y0"]; by1=br["y1"]
            lyd=max(lw.get("y1",fp_d),by1); ryd=max(rw.get("y1",fp_d),by1)
            if bx0 > lx1 + 1:
                voids.append({"x0":lx1,"y0":0,   "x1":bx0,"y1":by0})
                voids.append({"x0":lx1,"y0":by1, "x1":bx0,"y1":lyd})
            if rx0 > bx1 + 1:
                voids.append({"x0":bx1,"y0":0,   "x1":rx0,"y1":by0})
                voids.append({"x0":bx1,"y0":by1, "x1":rx0,"y1":ryd})
    return [v for v in voids if v["x1"]-v["x0"]>1 and v["y1"]-v["y0"]>1]

def get_void_zones(shape, fp_w, fp_d):
    return get_real_voids(shape, fp_w, fp_d, {})

# ── Main entry point ──────────────────────────────────────────────────────────
CIRCULATION = {"foyer","gallery","corridor","hallway","landing","entry","breezeway"}

def pack(adjacency: dict, footprint: dict, shape: str = "rectangle") -> dict:
    fp_w     = footprint.get("width", 89)
    fp_d     = footprint.get("depth", 79)
    fp_zones = footprint.get("zones", {})
    zb_all   = get_zone_bounds(shape, fp_w, fp_d, fp_zones)

    # Build room list, skip circulation
    rooms_list = []
    for name, val in adjacency.items():
        if name.lower() in CIRCULATION:
            continue
        sf = val.get("sf", 100) if isinstance(val, dict) else 100
        rooms_list.append({"name": name, "sf": sf})

    # Group by zone
    groups = {k: [] for k in zb_all}
    for rm in rooms_list:
        zk = zone_for_room(rm["name"])
        if zk not in groups:
            zk = "living"
        groups[zk].append(rm)

    # Fill zones
    placed_list = []
    for zk, zb in zb_all.items():
        rms = groups.get(zk, [])
        if not rms:
            continue
        placed_list.extend(_fill_zone(rms, zb, zk))

    result = {}
    for p in placed_list:
        result[p["name"]] = {"x0":p["x0"],"y0":p["y0"],"x1":p["x1"],"y1":p["y1"],"sf":p["sf"],"zone":p["zone"]}
        w=p["x1"]-p["x0"]; d=p["y1"]-p["y0"]
        print(f"  {p['name']:<22} zone={p['zone']:<14} ({p['x0']:.0f},{p['y0']:.0f})->({p['x1']:.0f},{p['y1']:.0f})  {w*d:.0f} SF")

    return result
