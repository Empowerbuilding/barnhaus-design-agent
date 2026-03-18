"""
barnhaus_graph_packer.py

Takes a room adjacency graph (from spatial-v2 model) + footprint
and produces x/y room coordinates using constraint-based packing.

Algorithm:
1. Build adjacency graph
2. Find anchor rooms (dead ends, face-attached)
3. BFS outward from anchors, placing each room adjacent to its already-placed neighbors
4. Snap to 1ft grid, enforce no-overlap via push-apart
"""
import math
from collections import deque

GRID = 1.0  # ft snap

def snap(v):
    return round(v / GRID) * GRID

def rooms_overlap(a, b, tol=0.5):
    return (a["x0"]+tol < b["x1"] and b["x0"]+tol < a["x1"] and
            a["y0"]+tol < b["y1"] and b["y0"]+tol < a["y1"])

def place_adjacent(placed: dict, neighbor_name: str, new_name: str,
                   new_w: float, new_d: float, face: str):
    """Place new_room adjacent to neighbor on given face (N/S/E/W)."""
    n = placed[neighbor_name]
    if face == "E":   x0, y0 = n["x1"], n["y0"]
    elif face == "W": x0, y0 = n["x0"] - new_w, n["y0"]
    elif face == "N": x0, y0 = n["x0"], n["y1"]
    elif face == "S": x0, y0 = n["x0"], n["y0"] - new_d
    else:             x0, y0 = n["x1"], n["y0"]
    return {"x0": snap(x0), "y0": snap(y0),
            "x1": snap(x0+new_w), "y1": snap(y0+new_d)}

def dims_from_sf(name: str, sf: int) -> tuple:
    """Return (width, depth) from SF + aspect ratio hint."""
    ASPECT = {
        "great room":1.4,"kitchen":1.2,"dining":1.3,"master bed":1.2,
        "master bath":1.0,"master closet":0.8,"bed":1.1,"bath":0.85,
        "laundry":1.0,"mudroom":1.2,"butler pantry":0.7,"utility":1.0,
        "home office":1.2,"porch":2.0,"garage":1.5,"foyer":1.0,
        "corridor":3.0,"gallery":3.0,"study":1.1,
    }
    n = name.lower()
    asp = next((v for k,v in ASPECT.items() if k in n), 1.15)
    w = max(8.0, math.sqrt(sf * asp))
    d = max(8.0, sf / w)
    return snap(w), snap(d)

def pack(adjacency: dict, footprint: dict) -> dict:
    """
    adjacency: {room_name: {zone, sf, adjacent_to, position, dead_end}}
    footprint: {width, depth, shape}
    returns: {room_name: {x0,y0,x1,y1,sf,zone}}
    """
    fp_w = footprint.get("width", 89)
    fp_d = footprint.get("depth", 79)
    placed = {}

    # Priority order: anchor rooms first
    PRIORITY = ["foyer","great room","master bed","garage","front porch","kitchen"]

    def priority_score(name):
        n = name.lower()
        for i, p in enumerate(PRIORITY):
            if p in n: return i
        return 99

    rooms = dict(sorted(adjacency.items(), key=lambda x: priority_score(x[0])))

    def _place(name, rc):
        w, d = dims_from_sf(name, rc.get("sf", 100))
        pos_tags = rc.get("position", [])

        # Try to place adjacent to an already-placed neighbor
        for neighbor in rc.get("adjacent_to", []):
            if neighbor not in placed: continue
            n = placed[neighbor]
            # Try each face
            for face, (tx, ty) in [
                ("E", (n["x1"], n["y0"])),
                ("N", (n["x0"], n["y1"])),
                ("W", (n["x0"]-w, n["y0"])),
                ("S", (n["x0"], n["y0"]-d)),
            ]:
                x0, y0 = snap(tx), snap(ty)
                x1, y1 = snap(x0+w), snap(y0+d)
                # Clamp to footprint
                if x0 < 0: x0, x1 = 0.0, snap(w)
                if y0 < 0: y0, y1 = 0.0, snap(d)
                if x1 > fp_w: x0, x1 = snap(fp_w-w), fp_w
                if y1 > fp_d: y0, y1 = snap(fp_d-d), fp_d
                candidate = {"x0":x0,"y0":y0,"x1":x1,"y1":y1}
                # Check no overlap with already placed
                if not any(rooms_overlap(candidate, p) for p in placed.values()):
                    return {**candidate, "sf": rc.get("sf",100), "zone": rc.get("zone","living")}

        # Fallback: position tag based placement
        if "south_face" in pos_tags or "front_zone" in pos_tags:
            x0, y0 = snap(fp_w/2 - w/2), 0.0
        elif "north_face" in pos_tags or "rear_zone" in pos_tags:
            x0, y0 = snap(fp_w/2 - w/2), snap(fp_d - d)
        elif "west_face" in pos_tags or "left_third" in pos_tags:
            x0, y0 = 0.0, snap(fp_d/2 - d/2)
        elif "east_face" in pos_tags or "right_third" in pos_tags:
            x0, y0 = snap(fp_w - w), snap(fp_d/2 - d/2)
        else:
            x0, y0 = snap(fp_w/2 - w/2), snap(fp_d/2 - d/2)

        x1, y1 = snap(x0+w), snap(y0+d)
        # Push apart from overlaps
        for _ in range(20):
            overlapping = [p for p in placed.values() if rooms_overlap({"x0":x0,"y0":y0,"x1":x1,"y1":y1}, p)]
            if not overlapping: break
            for op in overlapping:
                cx = (op["x0"]+op["x1"])/2
                if x0 < cx: x1 = snap(op["x0"]); x0 = snap(x1-w)
                else:        x0 = snap(op["x1"]); x1 = snap(x0+w)
        x0 = max(0.0, min(x0, fp_w-w))
        y0 = max(0.0, min(y0, fp_d-d))
        x1, y1 = snap(x0+w), snap(y0+d)
        return {"x0":x0,"y0":y0,"x1":x1,"y1":y1,"sf":rc.get("sf",100),"zone":rc.get("zone","living")}

    # BFS from highest-priority anchors
    queue = deque(rooms.keys())
    visited = set()
    while queue:
        name = queue.popleft()
        if name in visited: continue
        visited.add(name)
        placed[name] = _place(name, rooms[name])
        for neighbor in rooms[name].get("adjacent_to", []):
            if neighbor not in visited:
                queue.append(neighbor)

    # Any unplaced rooms (disconnected)
    for name, rc in rooms.items():
        if name not in placed:
            placed[name] = _place(name, rc)

    # Log overlaps
    names = list(placed.keys())
    for i, a in enumerate(names):
        for b in names[i+1:]:
            if rooms_overlap(placed[a], placed[b], tol=1.0):
                print(f"  ⚠️  Overlap after pack: {a} ↔ {b}")

    return placed


if __name__ == "__main__":
    # Quick smoke test
    test_adj = {
        "Foyer":        {"zone":"living", "sf":80,  "adjacent_to":["Great Room","Front Porch"], "position":["south_face","center"],   "dead_end":False},
        "Great Room":   {"zone":"living", "sf":400, "adjacent_to":["Foyer","Kitchen","Dining"], "position":["center","mid_zone"],      "dead_end":False},
        "Kitchen":      {"zone":"living", "sf":250, "adjacent_to":["Great Room","Dining"],       "position":["center","mid_zone"],      "dead_end":False},
        "Dining":       {"zone":"living", "sf":200, "adjacent_to":["Kitchen","Great Room"],      "position":["right_third","mid_zone"], "dead_end":False},
        "Master Bed":   {"zone":"master", "sf":300, "adjacent_to":["Master Bath"],               "position":["west_face","rear_zone"],  "dead_end":True},
        "Master Bath":  {"zone":"master", "sf":150, "adjacent_to":["Master Bed","Master Closet"],"position":["west_face","rear_zone"],  "dead_end":False},
        "Master Closet":{"zone":"master", "sf":80,  "adjacent_to":["Master Bath"],               "position":["west_face","rear_zone"],  "dead_end":True},
        "Garage":       {"zone":"service","sf":500, "adjacent_to":["Mudroom"],                   "position":["east_face","mid_zone"],   "dead_end":False},
        "Mudroom":      {"zone":"service","sf":100, "adjacent_to":["Garage","Kitchen"],          "position":["right_third","mid_zone"], "dead_end":False},
        "Front Porch":  {"zone":"porch",  "sf":150, "adjacent_to":["Foyer"],                     "position":["south_face","center"],    "dead_end":True},
        "Back Porch":   {"zone":"porch",  "sf":200, "adjacent_to":["Great Room"],                "position":["north_face","center"],    "dead_end":True},
    }
    result = pack(test_adj, {"width":89,"depth":79,"shape":"rectangle"})
    for name, rc in result.items():
        print(f"  {name:<20} ({rc['x0']:.0f},{rc['y0']:.0f})->({rc['x1']:.0f},{rc['y1']:.0f})  {rc['sf']} SF")
