"""
barnhaus_graph_packer.py — Adjacency-driven edge-snap packer (v4)

Algorithm:
1. Anchor: place Great Room (or largest living room) at center
2. For each room in BFS order from adjacency graph:
   - Find an already-placed neighbor
   - Snap to an open face of that neighbor (N/S/E/W)
   - Use zone bias to prefer direction (master→left, beds→right, service→left+back)
3. Porches snap to the actual south/north face of the placed house mass
4. After placement, trace outer perimeter → draw as house outline
5. No hard zone boxes — shape emerges from adjacency
"""
from __future__ import annotations
import math
from collections import deque
from typing import Dict, List, Optional, Tuple

GRID = 1.0

def snap(v):
    return round(v / GRID) * GRID

def _dims(sf: float, hint_wide: bool = True) -> Tuple[float, float]:
    """Return (w, d) for a given SF. Wide rooms get landscape aspect, narrow get portrait."""
    sf = max(sf, 48)
    aspect = 1.6 if hint_wide else 0.8
    w = snap(math.sqrt(sf * aspect))
    d = snap(sf / max(w, 1))
    return max(w, 8.0), max(d, 6.0)

# ── Zone bias: which direction each room type prefers ───────────────────────
def _zone_key(name: str) -> str:
    n = name.lower()
    if "garage" in n:                               return "garage"
    if "master" in n:                               return "master"
    if "bed" in n and "bath" not in n:              return "beds"
    if "bath" in n and "master" not in n:           return "beds"
    if n in ("mudroom","laundry","utility","utility room","mechanical","storage"): return "service"
    if "pantry" in n or "butler" in n:              return "living"
    if "front porch" in n:                          return "front_porch"
    if "back porch" in n or "porch" in n:           return "back_porch"
    return "living"

# Preferred face to try first when placing against a neighbor
# face = which face of the neighbor we attach to: N=north(+y), S=south(-y), E=east(+x), W=west(-x)
ZONE_FACE_PREF = {
    "master":      ["W","S","N","E"],   # master wants to go left/west
    "beds":        ["E","N","S","W"],   # beds want to go right/east
    "service":     ["W","N","S","E"],   # service near master, upper
    "garage":      ["W","S","N","E"],   # garage far left, lower
    "living":      ["N","E","S","W"],   # living fills center
    "front_porch": ["S","E","W","N"],   # porch hangs off south face
    "back_porch":  ["N","E","W","S"],   # porch hangs off north face
}

CIRCULATION = {"foyer","gallery","corridor","hallway","landing","entry","breezeway"}

# ── Overlap detection ────────────────────────────────────────────────────────
def _overlaps(a: dict, b: dict, tol: float = 0.5) -> bool:
    return (a["x0"] < b["x1"] - tol and a["x1"] > b["x0"] + tol and
            a["y0"] < b["y1"] - tol and a["y1"] > b["y0"] + tol)

def _any_overlap(cand: dict, placed: dict, skip: str) -> bool:
    return any(_overlaps(cand, p) for n, p in placed.items() if n != skip)

# ── Try placing on a face of a placed neighbor ───────────────────────────────
def _try_face(neighbor: dict, face: str, w: float, d: float,
              placed: dict, name: str) -> Optional[dict]:
    """
    Try to place a w×d room on 'face' of neighbor.
    Center-align along the shared edge.
    Returns room dict or None if it overlaps.
    """
    nw = neighbor["x1"] - neighbor["x0"]
    nd = neighbor["y1"] - neighbor["y0"]
    cx = (neighbor["x0"] + neighbor["x1"]) / 2
    cy = (neighbor["y0"] + neighbor["y1"]) / 2

    if face == "S":   # attach to south face of neighbor (room goes below)
        x0 = snap(cx - w/2); y0 = snap(neighbor["y0"] - d)
    elif face == "N": # attach to north face (room goes above)
        x0 = snap(cx - w/2); y0 = snap(neighbor["y1"])
    elif face == "W": # attach to west face (room goes left)
        x0 = snap(neighbor["x0"] - w); y0 = snap(cy - d/2)
    elif face == "E": # attach to east face (room goes right)
        x0 = snap(neighbor["x1"]);     y0 = snap(cy - d/2)
    else:
        return None

    cand = {"x0": x0, "y0": y0, "x1": snap(x0+w), "y1": snap(y0+d)}
    if _any_overlap(cand, placed, name):
        # Try sliding along the shared edge to find a clear spot
        if face in ("S","N"):
            for dx in [nw/4, -nw/4, nw/2, -nw/2, nw, -nw]:
                c2 = {"x0":snap(x0+dx),"y0":cand["y0"],"x1":snap(cand["x1"]+dx),"y1":cand["y1"]}
                if not _any_overlap(c2, placed, name):
                    return c2
        else:
            for dy in [nd/4, -nd/4, nd/2, -nd/2, nd, -nd]:
                c2 = {"x0":cand["x0"],"y0":snap(y0+dy),"x1":cand["x1"],"y1":snap(cand["y1"]+dy)}
                if not _any_overlap(c2, placed, name):
                    return c2
        return None
    return cand

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
def pack(adjacency: dict, footprint: dict, shape: str = "rectangle") -> dict:
    """
    adjacency: {RoomName: {"adjacent_to":[...], "sf": int}}
    footprint: {"width": ft, "depth": ft, "zones": {...}, "front_porch_sf": int, "back_porch_sf": int}
    Returns:   {RoomName: {"x0","y0","x1","y1","sf","zone"}}
    """
    fp_w = footprint.get("width", 89)
    fp_d = footprint.get("depth", 79)
    front_porch_sf = footprint.get("front_porch_sf", 200)
    back_porch_sf  = footprint.get("back_porch_sf",  200)

    # Build normalized room list, skip circulation
    rooms: Dict[str, dict] = {}
    adj_map: Dict[str, List[str]] = {}
    for name, val in adjacency.items():
        if name.lower() in CIRCULATION:
            continue
        sf = val.get("sf", 100) if isinstance(val, dict) else 100
        adjs = val.get("adjacent_to", []) if isinstance(val, dict) else (val if isinstance(val, list) else [])
        rooms[name] = {"name": name, "sf": sf, "zone": _zone_key(name)}
        adj_map[name] = [a for a in adjs if a in adjacency and a.lower() not in CIRCULATION]

    # ── Step 1: Place zone anchors first (garage far-left, master left, beds right) ──
    # These are hard-anchored BEFORE the BFS so they don't drift to center
    placed: Dict[str, dict] = {}

    # Garage anchor — far left, upper area
    garage_name = next((n for n in rooms if "garage" in n.lower()), None)
    if garage_name:
        gw, gd = _dims(rooms[garage_name]["sf"], hint_wide=True)
        placed[garage_name] = {"x0": 0.0, "y0": 0.0, "x1": snap(gw), "y1": snap(gd),
                                "sf": rooms[garage_name]["sf"], "zone": "garage"}

    # Master Bed anchor — left side, below garage
    master_name = next((n for n in rooms if "master bed" in n.lower()), None)
    if master_name:
        mw, md = _dims(rooms[master_name]["sf"], hint_wide=True)
        gy1 = placed[garage_name]["y1"] if garage_name and garage_name in placed else 0
        placed[master_name] = {"x0": 0.0, "y0": snap(gy1), "x1": snap(mw), "y1": snap(gy1+md),
                                "sf": rooms[master_name]["sf"], "zone": "master"}

    # Great Room anchor — center, adjacent to master
    anchor = next((n for n in rooms if "great room" in n.lower()), None)
    if not anchor:
        anchor = max((n for n in rooms if rooms[n]["zone"] == "living" and n not in placed),
                     key=lambda n: rooms[n]["sf"], default=None)
    if anchor and anchor not in placed:
        aw, ad = _dims(rooms[anchor]["sf"], hint_wide=True)
        ref_x1 = max((p["x1"] for p in placed.values()), default=0)
        ref_y0 = placed[master_name]["y0"] if master_name and master_name in placed else 0
        ax0 = snap(ref_x1)
        ay0 = snap(ref_y0)
        placed[anchor] = {"x0": ax0, "y0": ay0, "x1": snap(ax0+aw), "y1": snap(ay0+ad),
                          "sf": rooms[anchor]["sf"], "zone": "living"}
    elif not anchor:
        anchor = max(rooms, key=lambda n: rooms[n]["sf"])

    # ── Step 2: BFS from anchor, place each room on a face of a neighbor ──
    # Separate porches — handle after everything else
    porches = {n for n in rooms if "porch" in n.lower() or "deck" in n.lower()}
    non_porches = [n for n in rooms if n not in porches]

    # BFS order
    visited = {anchor}
    queue = deque([anchor])
    bfs_order = [anchor]
    while queue:
        cur = queue.popleft()
        for nb in adj_map.get(cur, []):
            if nb not in visited and nb in rooms and nb not in porches:
                visited.add(nb)
                queue.append(nb)
                bfs_order.append(nb)
    # Append any unvisited non-porch rooms
    for n in non_porches:
        if n not in visited and n not in porches:
            bfs_order.append(n)

    for name in bfs_order:
        if name == anchor or name in porches:
            continue
        rm = rooms[name]
        zk = rm["zone"]
        hint_wide = zk in ("living", "master", "garage")
        w, d = _dims(rm["sf"], hint_wide)

        face_prefs = ZONE_FACE_PREF.get(zk, ["N","E","S","W"])

        # Try neighbors in adjacency order first
        result = None
        neighbors_placed = [nb for nb in adj_map.get(name, []) if nb in placed]
        # Also consider all placed rooms as fallback neighbors
        all_placed = list(placed.keys())

        for nb_name in (neighbors_placed + [n for n in all_placed if n not in neighbors_placed]):
            nb = placed[nb_name]
            for face in face_prefs:
                result = _try_face(nb, face, w, d, placed, name)
                if result:
                    break
            if result:
                break

        if not result:
            # Last resort: place near anchor with offset
            offset = len(placed) * 2
            result = {"x0": snap(ax0 + offset), "y0": snap(ay0 + offset),
                      "x1": snap(ax0 + offset + w), "y1": snap(ay0 + offset + d)}

        placed[name] = {**result, "sf": rm["sf"], "zone": zk}

    # ── Step 3: Place porches on actual south/north house face ────────────
    # Find the south (min y0) and north (max y1) extents of placed house
    if placed:
        all_x0 = [p["x0"] for p in placed.values()]
        all_x1 = [p["x1"] for p in placed.values()]
        all_y0 = [p["y0"] for p in placed.values()]
        all_y1 = [p["y1"] for p in placed.values()]
        house_x0 = min(all_x0); house_x1 = max(all_x1)
        house_y0 = min(all_y0); house_y1 = max(all_y1)
        house_cx = (house_x0 + house_x1) / 2

        # Living zone cluster for centering porches
        living_rooms = [p for n,p in placed.items() if rooms.get(n,{}).get("zone") == "living"]
        if living_rooms:
            lx0 = min(p["x0"] for p in living_rooms)
            lx1 = max(p["x1"] for p in living_rooms)
        else:
            lx0 = house_x0 + (house_x1-house_x0)*0.25
            lx1 = house_x0 + (house_x1-house_x0)*0.75

        for pname in sorted(porches):
            sf = rooms[pname]["sf"]
            pw = snap(lx1 - lx0)  # match living cluster width
            pd = max(snap(sf / max(pw, 1)), 6.0)
            px0 = snap(lx0)
            if "front" in pname.lower():
                # Attach to south face of house
                py0 = snap(house_y0 - pd)
                placed[pname] = {"x0":px0,"y0":py0,"x1":snap(px0+pw),"y1":snap(py0+pd),
                                 "sf":sf,"zone":"front_porch"}
            else:
                # Attach to north face of house
                py0 = snap(house_y1)
                placed[pname] = {"x0":px0,"y0":py0,"x1":snap(px0+pw),"y1":snap(py0+pd),
                                 "sf":sf,"zone":"back_porch"}

    # ── Print summary ─────────────────────────────────────────────────────
    for name, r in placed.items():
        w = r["x1"]-r["x0"]; d = r["y1"]-r["y0"]
        print(f"  {name:<22} zone={r['zone']:<14} ({r['x0']:.0f},{r['y0']:.0f})->({r['x1']:.0f},{r['y1']:.0f})  {w*d:.0f} SF")

    return placed

# Backward compat
def get_zone_bounds(shape, fp_w, fp_d, fp_zones, **kw):
    return {}
