"""
barnhaus_graph_packer.py

Takes a room adjacency graph (spatial-v2 output) + footprint
and produces x/y room coordinates using constraint-based packing.
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
        "home office":1.2,"porch":2.0,"garage":1.5,"foyer":1.0,
        "corridor":4.0,"gallery":3.0,"study":1.1,
    }
    n = name.lower()
    asp = next((v for k,v in ASPECT.items() if k in n), 1.15)
    w = max(8.0, math.sqrt(sf * asp))
    d = max(8.0, sf / w)
    return snap(w), snap(d)

def pack(adjacency: dict, footprint: dict) -> dict:
    fp_w = footprint.get("width", 89)
    fp_d = footprint.get("depth", 79)
    placed = {}

    def _try_place(x0, y0, w, d, name):
        """Clamp to footprint, return rect or None if overlaps."""
        x0 = max(0.0, min(snap(x0), fp_w - w))
        y0 = max(0.0, min(snap(y0), fp_d - d))
        x1, y1 = snap(x0 + w), snap(y0 + d)
        c = {"x0":x0,"y0":y0,"x1":x1,"y1":y1}
        if any(rooms_overlap(c, p) for n,p in placed.items() if n != name):
            return None
        return c

    def _place_room(name, rc):
        w, d = dims_from_sf(name, rc.get("sf", 100))
        pos_tags = rc.get("position", [])

        # --- Special cluster rules ---

        # PORCH: snap to named face, centered
        if "porch" in name.lower():
            if "south_face" in pos_tags or "front" in name.lower():
                # Try to sit adjacent to foyer/great room x-center
                anchor = next((placed[n] for n in ["Foyer","Great Room"] if n in placed), None)
                cx = ((anchor["x0"]+anchor["x1"])/2) if anchor else fp_w/2
                x0 = snap(cx - w/2)
                r = _try_place(x0, 0, w, d, name)
                if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}
            if "north_face" in pos_tags or "back" in name.lower():
                anchor = next((placed[n] for n in ["Great Room","Back Porch"] if n in placed and n!=name), None)
                cx = ((anchor["x0"]+anchor["x1"])/2) if anchor else fp_w/2
                x0 = snap(cx - w/2)
                r = _try_place(x0, fp_d - d, w, d, name)
                if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}

        # MASTER SUITE: force sequential chain west_face/rear
        if "master" in name.lower():
            if "Master Bath" in placed and "closet" in name.lower():
                mb = placed["Master Bath"]
                for r in [_try_place(mb["x1"], mb["y0"], w, d, name),
                           _try_place(mb["x0"]-w, mb["y0"], w, d, name),
                           _try_place(mb["x0"], mb["y1"], w, d, name)]:
                    if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}
            if "Master Bed" in placed and "bath" in name.lower():
                mb = placed["Master Bed"]
                for r in [_try_place(mb["x0"], mb["y1"], w, d, name),
                           _try_place(mb["x1"], mb["y0"], w, d, name),
                           _try_place(mb["x0"]-w, mb["y0"], w, d, name)]:
                    if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}

        # BED ZONE: pack beds side-by-side in rear zone
        if rc.get("zone") == "beds" and "bed" in name.lower() and "bath" not in name.lower():
            beds_placed = [(n,p) for n,p in placed.items() if "bed" in n.lower() and "bath" not in n.lower() and "master" not in n.lower()]
            if beds_placed:
                last_n, last_p = max(beds_placed, key=lambda x: x[1]["x1"])
                r = _try_place(last_p["x1"], last_p["y0"], w, d, name)
                if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}
                r = _try_place(last_p["x0"]-w, last_p["y0"], w, d, name)
                if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}

        # BATH in bed zone: snap to adjacent bed
        if rc.get("zone") == "beds" and "bath" in name.lower():
            bed_num = next((c for c in name if c.isdigit()), None)
            if bed_num:
                bed_name = next((n for n in placed if f"Bed {bed_num}" in n), None)
                if bed_name:
                    bp = placed[bed_name]
                    for r in [_try_place(bp["x1"], bp["y0"], w, d, name),
                               _try_place(bp["x0"]-w, bp["y0"], w, d, name),
                               _try_place(bp["x0"], bp["y1"], w, d, name),
                               _try_place(bp["x0"], bp["y0"]-d, w, d, name)]:
                        if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}

        # GENERIC: try each adjacent neighbor's 4 faces
        for neighbor in rc.get("adjacent_to", []):
            if neighbor not in placed: continue
            n = placed[neighbor]
            for (tx, ty) in [(n["x1"], n["y0"]), (n["x0"], n["y1"]),
                              (n["x0"]-w, n["y0"]), (n["x0"], n["y0"]-d)]:
                r = _try_place(tx, ty, w, d, name)
                if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}

        # FALLBACK: position-tag based
        if "south_face" in pos_tags:   x0,y0 = snap(fp_w/2-w/2), 0.0
        elif "north_face" in pos_tags: x0,y0 = snap(fp_w/2-w/2), snap(fp_d-d)
        elif "west_face" in pos_tags:  x0,y0 = 0.0, snap(fp_d/2-d/2)
        elif "east_face" in pos_tags:  x0,y0 = snap(fp_w-w), snap(fp_d/2-d/2)
        elif "left_third" in pos_tags: x0,y0 = snap(fp_w*0.1), snap(fp_d/2-d/2)
        elif "right_third" in pos_tags:x0,y0 = snap(fp_w*0.65), snap(fp_d/2-d/2)
        elif "rear_zone" in pos_tags:  x0,y0 = snap(fp_w/2-w/2), snap(fp_d-d)
        else:                           x0,y0 = snap(fp_w/2-w/2), snap(fp_d/2-d/2)

        # Nudge until no overlap
        for _ in range(30):
            r = _try_place(x0, y0, w, d, name)
            if r: return {**r, "sf":rc["sf"], "zone":rc["zone"]}
            x0 += w + 1  # push right
            if x0 + w > fp_w: x0 = 0; y0 += d + 1

        x0 = max(0.0, min(x0, fp_w-w))
        y0 = max(0.0, min(y0, fp_d-d))
        return {"x0":snap(x0),"y0":snap(y0),"x1":snap(x0+w),"y1":snap(y0+d),
                "sf":rc["sf"],"zone":rc["zone"],"level":rc.get("level",1)}

    # Placement order: anchors first, then BFS
    PRIORITY_KEYS = ["foyer","great room","master bed","garage","corridor",
                     "kitchen","dining","front porch","back porch","master bath",
                     "master closet","bed 2","bed 3","bed 4","bath 2","bath 3"]

    def _priority(name):
        n = name.lower()
        for i,k in enumerate(PRIORITY_KEYS):
            if k == n: return i
        return 50

    ordered = sorted(adjacency.keys(), key=_priority)

    for name in ordered:
        rc = adjacency[name]
        placed[name] = _place_room(name, rc)

    # Any remaining (shouldn't happen)
    for name, rc in adjacency.items():
        if name not in placed:
            placed[name] = _place_room(name, rc)

    # Report overlaps
    names = list(placed.keys())
    for i,a in enumerate(names):
        for b in names[i+1:]:
            if rooms_overlap(placed[a], placed[b], tol=1.0):
                print(f"  ⚠️  Overlap: {a} ↔ {b}")

    return placed
