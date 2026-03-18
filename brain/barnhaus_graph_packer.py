"""
barnhaus_graph_packer.py

Takes a room adjacency graph (spatial-v2 output) + footprint
and produces x/y room coordinates using shape-zone-aware packing.
"""
import math
from collections import deque

GRID = 1.0

def snap(v): return round(v / GRID) * GRID

def rooms_overlap(a, b, tol=0.5):
    return (a["x0"]+tol < b["x1"] and b["x0"]+tol < a["x1"] and
            a["y0"]+tol < b["y1"] and b["y0"]+tol < a["y1"])

def dims_from_sf(name: str, sf: int) -> tuple:
    ASPECT = {
        "great room":1.4,"kitchen":1.2,"dining":1.3,"master bed":1.2,
        "master bath":1.0,"master closet":0.8,"bed":1.1,"bath":0.85,
        "laundry":1.0,"mudroom":1.2,"butler pantry":0.7,"utility":1.0,
        "home office":1.2,"porch":2.5,"garage":1.5,"foyer":1.2,
        "corridor":4.0,"gallery":3.0,"study":1.1,
    }
    n = name.lower()
    asp = next((v for k,v in ASPECT.items() if k in n), 1.15)
    w = max(8.0, math.sqrt(sf * asp))
    d = max(8.0, sf / w)
    return snap(w), snap(d)

def get_shape_zones(shape: str, fp_w: float, fp_d: float) -> dict:
    """
    Return zone boundaries per shape.
    Each zone: {x0, y0, x1, y1}
    """
    s = (shape or "rectangle").lower().replace(" ", "-")

    if s == "h-shape":
        lw = fp_w * 0.30  # left wing 30%
        rw = fp_w * 0.70  # right wing starts at 70%
        bridge_y0 = fp_d * 0.25
        bridge_y1 = fp_d * 0.75
        return {
            "master":   {"x0": 0,   "y0": 0,         "x1": lw,   "y1": fp_d},
            "living":   {"x0": lw,  "y0": bridge_y0, "x1": rw,   "y1": bridge_y1},
            "beds":     {"x0": rw,  "y0": 0,         "x1": fp_w, "y1": fp_d},
            "service":  {"x0": lw,  "y0": 0,         "x1": rw,   "y1": bridge_y0},
            "garage":   {"x0": 0,   "y0": fp_d*0.6,  "x1": lw,   "y1": fp_d},
            "porch":    {"x0": lw,  "y0": 0,         "x1": rw,   "y1": fp_d},
        }
    elif s in ("l-shape", "asymmetric-l"):
        return {
            "master":   {"x0": 0,        "y0": fp_d*0.4, "x1": fp_w*0.35, "y1": fp_d},
            "living":   {"x0": fp_w*0.2, "y0": 0,        "x1": fp_w*0.7,  "y1": fp_d},
            "beds":     {"x0": fp_w*0.65,"y0": 0,        "x1": fp_w,      "y1": fp_d},
            "service":  {"x0": 0,        "y0": 0,        "x1": fp_w*0.3,  "y1": fp_d*0.45},
            "garage":   {"x0": 0,        "y0": 0,        "x1": fp_w*0.25, "y1": fp_d*0.4},
            "porch":    {"x0": fp_w*0.2, "y0": 0,        "x1": fp_w*0.8,  "y1": fp_d},
        }
    elif s == "t-shape":
        return {
            "master":   {"x0": 0,        "y0": 0,        "x1": fp_w*0.28, "y1": fp_d*0.6},
            "living":   {"x0": fp_w*0.25,"y0": 0,        "x1": fp_w*0.75, "y1": fp_d},
            "beds":     {"x0": fp_w*0.72,"y0": 0,        "x1": fp_w,      "y1": fp_d*0.6},
            "service":  {"x0": fp_w*0.25,"y0": fp_d*0.6, "x1": fp_w*0.75, "y1": fp_d},
            "garage":   {"x0": 0,        "y0": fp_d*0.55,"x1": fp_w*0.28, "y1": fp_d},
            "porch":    {"x0": fp_w*0.25,"y0": 0,        "x1": fp_w*0.75, "y1": fp_d},
        }
    elif s == "u-shape":
        return {
            "master":   {"x0": 0,        "y0": 0,        "x1": fp_w*0.28, "y1": fp_d},
            "living":   {"x0": fp_w*0.25,"y0": fp_d*0.4, "x1": fp_w*0.75, "y1": fp_d},
            "beds":     {"x0": fp_w*0.72,"y0": 0,        "x1": fp_w,      "y1": fp_d},
            "service":  {"x0": fp_w*0.25,"y0": 0,        "x1": fp_w*0.75, "y1": fp_d*0.45},
            "garage":   {"x0": 0,        "y0": fp_d*0.6, "x1": fp_w*0.28, "y1": fp_d},
            "porch":    {"x0": fp_w*0.3, "y0": fp_d*0.4, "x1": fp_w*0.7,  "y1": fp_d},
        }
    elif s == "dogtrot":
        return {
            "master":   {"x0": 0,        "y0": 0,        "x1": fp_w*0.4,  "y1": fp_d},
            "living":   {"x0": 0,        "y0": 0,        "x1": fp_w*0.4,  "y1": fp_d},
            "beds":     {"x0": fp_w*0.6, "y0": 0,        "x1": fp_w,      "y1": fp_d},
            "service":  {"x0": fp_w*0.6, "y0": 0,        "x1": fp_w,      "y1": fp_d},
            "garage":   {"x0": fp_w*0.6, "y0": fp_d*0.5, "x1": fp_w,      "y1": fp_d},
            "porch":    {"x0": fp_w*0.4, "y0": 0,        "x1": fp_w*0.6,  "y1": fp_d},
        }
    elif s == "z-shape":
        return {
            "master":   {"x0": 0,        "y0": fp_d*0.5, "x1": fp_w*0.5,  "y1": fp_d},
            "living":   {"x0": fp_w*0.15,"y0": 0,        "x1": fp_w*0.85, "y1": fp_d},
            "beds":     {"x0": fp_w*0.5, "y0": 0,        "x1": fp_w,      "y1": fp_d*0.5},
            "service":  {"x0": 0,        "y0": fp_d*0.5, "x1": fp_w*0.5,  "y1": fp_d},
            "garage":   {"x0": 0,        "y0": fp_d*0.5, "x1": fp_w*0.3,  "y1": fp_d},
            "porch":    {"x0": fp_w*0.2, "y0": 0,        "x1": fp_w*0.8,  "y1": fp_d},
        }
    else:  # rectangle, barn-bar, courtyard, default
        return {
            "master":   {"x0": 0,        "y0": 0,        "x1": fp_w*0.28, "y1": fp_d},
            "living":   {"x0": fp_w*0.25,"y0": 0,        "x1": fp_w*0.65, "y1": fp_d},
            "beds":     {"x0": fp_w*0.62,"y0": 0,        "x1": fp_w,      "y1": fp_d},
            "service":  {"x0": fp_w*0.62,"y0": 0,        "x1": fp_w,      "y1": fp_d},
            "garage":   {"x0": 0,        "y0": fp_d*0.5, "x1": fp_w*0.28, "y1": fp_d},
            "porch":    {"x0": fp_w*0.2, "y0": 0,        "x1": fp_w*0.8,  "y1": fp_d},
        }

def zone_for_room(name: str, room_zone: str) -> str:
    """Map brain zone name → shape zone key."""
    n = name.lower()
    if "garage" in n:             return "garage"
    if "porch" in n:              return "porch"
    if "master" in n:             return "master"
    if "bed" in n and "bath" not in n and "master" not in n: return "beds"
    if "bath" in n and "master" not in n: return "beds"
    if room_zone in ("service","utility","laundry","mudroom"): return "service"
    if room_zone == "master":     return "master"
    if room_zone == "beds":       return "beds"
    if room_zone == "garage":     return "garage"
    return "living"

def get_void_zones(shape: str, fp_w: float, fp_d: float) -> list:
    """Return list of void rectangles (areas rooms must NOT enter)."""
    s = (shape or "rectangle").lower().replace(" ","-")
    if s == "h-shape":
        lw = fp_w * 0.30; rw = fp_w * 0.70
        by0 = fp_d * 0.25; by1 = fp_d * 0.75
        return [
            {"x0": lw, "y0": 0,   "x1": rw, "y1": by0},   # front void
            {"x0": lw, "y0": by1, "x1": rw, "y1": fp_d},   # rear void
        ]
    elif s in ("l-shape","asymmetric-l"):
        return [{"x0": fp_w*0.6, "y0": fp_d*0.55, "x1": fp_w, "y1": fp_d}]
    elif s == "t-shape":
        return [
            {"x0": 0,       "y0": fp_d*0.6, "x1": fp_w*0.25, "y1": fp_d},
            {"x0": fp_w*0.75,"y0": fp_d*0.6,"x1": fp_w,      "y1": fp_d},
        ]
    elif s == "u-shape":
        return [{"x0": fp_w*0.3, "y0": fp_d*0.45, "x1": fp_w*0.7, "y1": fp_d}]
    elif s == "dogtrot":
        return [{"x0": fp_w*0.42, "y0": 0, "x1": fp_w*0.58, "y1": fp_d*0.3},
                {"x0": fp_w*0.42, "y0": fp_d*0.7, "x1": fp_w*0.58, "y1": fp_d}]
    return []

def get_real_voids(shape: str, fp_w: float, fp_d: float, fp_zones: dict) -> list:
    """
    Derive actual void rectangles from real footprint zone geometry.
    Voids = areas inside bounding box but outside any zone.
    """
    s = (shape or "rectangle").lower().replace(" ","-")
    voids = []
    if s == "h-shape" and fp_zones:
        lw  = fp_zones.get("master") or fp_zones.get("left_wing")
        br  = fp_zones.get("center_bridge") or fp_zones.get("living_core") or fp_zones.get("living")
        rw  = fp_zones.get("bed_wing") or fp_zones.get("right_wing") or fp_zones.get("beds")
        if lw and br and rw:
            # Front-left void: between left wing east and bridge west, south of bridge
            voids.append({"x0": lw["x1"], "y0": 0,       "x1": br["x0"], "y1": br["y0"]})
            # Front-right void: between bridge east and right wing west, south of bridge
            voids.append({"x0": br["x1"], "y0": 0,       "x1": rw["x0"], "y1": br["y0"]})
            # Rear-left void: between left wing east and bridge west, north of bridge
            voids.append({"x0": lw["x1"], "y0": br["y1"], "x1": br["x0"], "y1": lw["y1"]})
            # Rear-right void: between bridge east and right wing west, north of bridge
            voids.append({"x0": br["x1"], "y0": br["y1"], "x1": rw["x0"], "y1": rw["y1"]})
            # Front-center void: south face of bridge (if bridge doesn't reach y=0)
            if br["y0"] > 2:
                voids.append({"x0": br["x0"], "y0": 0, "x1": br["x1"], "y1": br["y0"]})
            # Rear-center void: north face of bridge  
            if br["y1"] < lw["y1"] - 2:
                voids.append({"x0": br["x0"], "y0": br["y1"], "x1": br["x1"], "y1": lw["y1"]})
    elif s in ("l-shape","asymmetric-l") and fp_zones:
        mw = fp_zones.get("master")
        bw = fp_zones.get("bed_wing") or fp_zones.get("beds")
        if mw and bw:
            voids.append({"x0": bw["x0"], "y0": bw["y1"], "x1": fp_w, "y1": fp_d})
    elif s == "u-shape" and fp_zones:
        br = fp_zones.get("living_core") or fp_zones.get("living")
        if br:
            voids.append({"x0": br["x0"], "y0": br["y1"], "x1": br["x1"], "y1": fp_d})
    return [v for v in voids if v["x1"]-v["x0"] > 2 and v["y1"]-v["y0"] > 2]

def pack(adjacency: dict, footprint: dict, shape: str = "rectangle") -> dict:
    fp_w = footprint.get("width", 89)
    fp_d = footprint.get("depth", 79)
    fp_zones_raw = footprint.get("zones", {})
    zones = get_shape_zones(shape, fp_w, fp_d)
    # Use real voids from actual footprint geometry if available
    voids = get_real_voids(shape, fp_w, fp_d, fp_zones_raw) or get_void_zones(shape, fp_w, fp_d)
    placed = {}

    def zone_bounds(zkey: str) -> dict:
        # Prefer real footprint zone geometry over computed percentages
        ZONE_MAP = {
            "master":  ["master","left_wing"],
            "living":  ["living_core","center_bridge","living"],
            "beds":    ["bed_wing","right_wing","beds"],
            "service": ["service"],
            "garage":  ["garage"],
            "porch":   ["porch"],
        }
        for key in ZONE_MAP.get(zkey, [zkey]):
            if key in fp_zones_raw:
                z = fp_zones_raw[key]
                # Add some padding so rooms don't butt right up against zone edge
                return {"x0": z["x0"], "y0": z["y0"], "x1": z["x1"], "y1": z["y1"]}
        return zones.get(zkey, {"x0":0,"y0":0,"x1":fp_w,"y1":fp_d})

    def _try_place(x0, y0, w, d, name, zkey=None):
        """Place room, clamped to its zone bounds, avoiding voids."""
        zb = zone_bounds(zkey) if zkey else {"x0":0,"y0":0,"x1":fp_w,"y1":fp_d}
        x0 = max(zb["x0"], min(snap(x0), zb["x1"] - w))
        y0 = max(zb["y0"], min(snap(y0), zb["y1"] - d))
        x1 = snap(min(x0 + w, zb["x1"]))
        y1 = snap(min(y0 + d, zb["y1"]))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return None
        c = {"x0":x0,"y0":y0,"x1":x1,"y1":y1}
        # Check void zones — rooms must not enter voids
        for v in voids:
            if rooms_overlap(c, v, 0.5):
                return None
        if any(rooms_overlap(c, p, 0.5) for n,p in placed.items() if n != name):
            return None
        return c

    def _place_room(name, rc):
        w, d = dims_from_sf(name, rc.get("sf", 100))
        zkey = zone_for_room(name, rc.get("zone","living"))
        zb = zone_bounds(zkey)
        zw = zb["x1"] - zb["x0"]
        zh = zb["y1"] - zb["y0"]

        # Clamp w/d to zone size
        w = min(w, zw - 1)
        d = min(d, zh - 1)

        # Porch: snap to zone edge
        if "front porch" in name.lower():
            cx = snap((zb["x0"] + zb["x1"]) / 2 - w / 2)
            r = _try_place(cx, zb["y0"], w, d, name, zkey)
            if r: return {**r, "sf":rc["sf"], "zone":zkey}

        if "back porch" in name.lower():
            cx = snap((zb["x0"] + zb["x1"]) / 2 - w / 2)
            r = _try_place(cx, zb["y1"] - d, w, d, name, zkey)
            if r: return {**r, "sf":rc["sf"], "zone":zkey}

        # Try adjacent neighbors first (within same zone preferred)
        for neighbor in rc.get("adjacent_to", []):
            if neighbor not in placed: continue
            nb = placed[neighbor]
            for (tx, ty) in [
                (nb["x1"], nb["y0"]),
                (nb["x0"] - w, nb["y0"]),
                (nb["x0"], nb["y1"]),
                (nb["x0"], nb["y0"] - d),
                (nb["x1"], nb["y1"] - d),
                (nb["x0"] - w, nb["y1"] - d),
            ]:
                r = _try_place(tx, ty, w, d, name, zkey)
                if r: return {**r, "sf":rc["sf"], "zone":zkey}

        # Grid scan within zone
        step = GRID * 2
        y = zb["y0"]
        while y + d <= zb["y1"]:
            x = zb["x0"]
            while x + w <= zb["x1"]:
                r = _try_place(x, y, w, d, name, zkey)
                if r: return {**r, "sf":rc["sf"], "zone":zkey}
                x += step
            y += step

        # Last resort: zone top-left
        x0 = zb["x0"]
        y0 = zb["y0"]
        return {"x0":snap(x0),"y0":snap(y0),"x1":snap(x0+w),"y1":snap(y0+d),
                "sf":rc["sf"],"zone":zkey}

    # Priority: anchors first
    PRIORITY = ["great room","foyer","master bed","garage","kitchen",
                "dining","front porch","back porch","master bath","master closet",
                "bed 2","bed 3","bed 4","bath 2","bath 3","corridor","gallery",
                "butler pantry","laundry","utility","mudroom","home office"]

    def _pri(name):
        n = name.lower()
        for i,k in enumerate(PRIORITY):
            if k == n: return i
        return 99

    for name in sorted(adjacency.keys(), key=_pri):
        placed[name] = _place_room(name, adjacency[name])

    # Report overlaps
    names = list(placed.keys())
    for i,a in enumerate(names):
        for b in names[i+1:]:
            if rooms_overlap(placed[a], placed[b], 1.0):
                print(f"  ⚠️  Overlap: {a} ↔ {b}")

    return placed
