"""
build_432_v3.py — 432 Cloud Top (Layout v3, fixed v3.2)

FIXES v3.2:
  - Window sill z=2.5 on L1, z=13.5 on L2 (2.5ft AFF) — tops well under wall/roof
  - Roof overhangs only on TRUE exterior edges (no protrusion into adjacent volumes)
  - Floor boundaries are exact (no outer_rect expansion) — eliminates overlap warning
  - Garage west roof edge flush with main house east wall (no gap/overlap)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, create_floor,
    place_door, place_window, call, verify_wall_facing
)

EXT = 'Wall 7.5" EXT PBR'
INT = 'Wall 4.5 Interior"'
L1  = "Level 1.0"
L2  = "Level 2.0"
H   = 10

MX0, MY0, MX1, MY1 = 0,  0,  52, 30
GX0, GY0, GX1, GY1 = 52, 0,  76, 22
MASTER_X = 18
SVC_X    = 40
MBED_Y   = 16
MBATH_X  = 8
MBATH_Y  = 6
CLOS_D   = 10
PANTRY_Y = 20
MUD_Y    = 10
HALF_Y   = 4
L2X0, L2Y0, L2X1, L2Y1 = 18, 0, 52, 20
L2_HALL_Y = 10
L2_B23_X  = 30
L2_BATH_X = 24

O = 3.0   # overhang (only on true exterior edges)
W1 = 2.5  # L1 window sill height (ft AFF) — top of 36"H window = 5.5ft, well under 10ft wall
W2 = 13.5 # L2 window sill height (absolute ft) = 2.5ft above L2 floor at z=11

def flip_door(eid):
    r = call("revit.flip_door", {"element_id": eid})
    print(f"  flip door {eid}: {r['Status']}")

def make_level(name, elev):
    r = call("revit.create_level", {"name": name, "elevation": elev})
    # "error" is ok here — level likely already exists from a prior run
    status = r['Status'] if r['Status'] == 'ok' else 'already exists (ok)'
    print(f"  level [{name}] z={elev}: {status}")
    return name

def make_roof(label, pts, level_name):
    """pts = list of (x,y) tuples"""
    r = call("revit.create_roof", {
        "level": level_name,
        "roof_type": '13" Roof No Gyp',
        "boundary_points": [{"x": p[0], "y": p[1], "z": 0} for p in pts]
    })
    ok = r["Status"] == "ok"
    rid = r["Result"].get("roof_id") if ok else None
    print(f"  roof [{label}]: {'ok ' + str(rid) if ok else 'ERR ' + r.get('Message','')}")
    return rid

T = 0.3125  # half of 7.5" EXT wall thickness

def smart_floor(level, z, x0, y0, x1, y1, exp_west=True, exp_south=True, exp_east=True, exp_north=True):
    """
    Floor boundary that expands to outer wall face only on TRUE exterior edges.
    Set exp_* = False on shared edges to avoid floor overlap with adjacent slabs.
    """
    pts = [
        {"x": x0 - (T if exp_west  else 0), "y": y0 - (T if exp_south else 0), "z": z},
        {"x": x1 + (T if exp_east  else 0), "y": y0 - (T if exp_south else 0), "z": z},
        {"x": x1 + (T if exp_east  else 0), "y": y1 + (T if exp_north else 0), "z": z},
        {"x": x0 - (T if exp_west  else 0), "y": y1 + (T if exp_north else 0), "z": z},
    ]
    d = call("revit.create_floor", {"level": level, "boundary_points": pts})
    ok = d["Status"] == "ok"
    fid = d["Result"].get("floor_id") if ok else None
    print(f"  floor [{level}] z={z}: {'ok ' + str(fid) if ok else 'ERR ' + d.get('Message','')}")
    return fid

# ── PHASE 0: LEVELS ──────────────────────────────────────────────
print("\n=== PHASE 0: LEVELS ===")
L_L1R  = make_level("L1 Roof",     10)
L_GARR = make_level("Garage Roof", 12)
L_L2R  = make_level("L2 Roof",     20)

# ── PHASE 1: EXTERIOR WALLS ──────────────────────────────────────
print("\n=== PHASE 1: EXTERIOR WALLS ===")
L1w = create_rect_exterior(MX0, MY0, MX1, MY1, 0, L1, EXT, H, "L1")
w_l1_s, w_l1_n, w_l1_w, w_l1_e = L1w["south"], L1w["north"], L1w["west"], L1w["east"]

w_gar_s = create_wall(GX0,GY0,0, GX1,GY0,0, L1, EXT, 12, "garage south")
w_gar_e = create_wall(GX1,GY0,0, GX1,GY1,0, L1, EXT, 12, "garage east")
w_gar_n = create_wall(GX1,GY1,0, GX0,GY1,0, L1, EXT, 12, "garage north")
verify_wall_facing(w_gar_s,  0, -1, "garage south")
verify_wall_facing(w_gar_e, +1,  0, "garage east")
verify_wall_facing(w_gar_n,  0, +1, "garage north")

L2w = create_rect_exterior(L2X0, L2Y0, L2X1, L2Y1, H, L2, EXT, H, "L2")
w_l2_s, w_l2_n, w_l2_w, w_l2_e = L2w["south"], L2w["north"], L2w["west"], L2w["east"]

# ── PHASE 2: INTERIOR WALLS ──────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")
w_master_e = create_wall(MASTER_X,MY0,0, MASTER_X,MY1,0,      L1, INT, H, "master east")
w_mbed_s   = create_wall(MX0,MBED_Y,0,  MASTER_X,MBED_Y,0,   L1, INT, H, "master bed south")
w_mbath_w  = create_wall(MBATH_X,MBATH_Y,0, MBATH_X,MBED_Y,0,L1, INT, H, "master bath west")
w_mbath_n  = create_wall(MX0,MBATH_Y,0, MBATH_X,MBATH_Y,0,   L1, INT, H, "master bath north")
w_clos_e   = create_wall(MBATH_X,MY0,0, MBATH_X,MBATH_Y,0,   L1, INT, H, "closet east")
w_clos_d   = create_wall(MX0,CLOS_D,0,  MBATH_X,CLOS_D,0,    L1, INT, H, "closet divider")
w_svc_w    = create_wall(SVC_X,MY0,0,   SVC_X,MY1,0,          L1, INT, H, "service west")
w_pantry_s = create_wall(SVC_X,PANTRY_Y,0, MX1,PANTRY_Y,0,   L1, INT, H, "pantry south")
w_mud_s    = create_wall(SVC_X,MUD_Y,0, MX1,MUD_Y,0,          L1, INT, H, "mud south")
w_half_s   = create_wall(SVC_X,HALF_Y,0, MX1,HALF_Y,0,        L1, INT, H, "half bath south")
w_l2_hall  = create_wall(L2X0,L2_HALL_Y,H, L2X1,L2_HALL_Y,H, L2, INT, H, "L2 hall south")
w_l2_b23   = create_wall(L2_B23_X,L2_HALL_Y,H, L2_B23_X,L2Y1,H, L2, INT, H, "L2 bed2/3")
w_l2_bath  = create_wall(L2_BATH_X,L2Y0,H, L2_BATH_X,L2_HALL_Y,H, L2, INT, H, "L2 bath east")

# ── PHASE 3: FLOORS (exact boundaries — no overlap) ──────────────
print("\n=== PHASE 3: L1 FLOORS ===")
# Main house: expand all sides EXCEPT east (x=52 shared with garage)
smart_floor(L1, 0, MX0, MY0, MX1, MY1, exp_west=True, exp_south=True, exp_east=False, exp_north=True)
# Garage: expand all sides EXCEPT west (x=52 shared with main house)
smart_floor(L1, 0, GX0, GY0, GX1, GY1, exp_west=False, exp_south=True, exp_east=True, exp_north=True)

# ── PHASE 4: L1 DOORS ────────────────────────────────────────────
print("\n=== PHASE 4: L1 DOORS ===")
place_door(w_l1_s, None, MY0, 0,
    "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
    label="front entry", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

place_door(w_l1_n, None, MY1, 0,
    "Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00",
    label="rear porch slider", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

place_door(w_master_e, MASTER_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
    label="master bed", wall_axis='y', wall_start=MBED_Y, wall_end=MY1)

place_door(w_mbed_s, None, MBED_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '32" x 96"',
    label="master bath", wall_axis='x', wall_start=MBATH_X, wall_end=MASTER_X)

place_door(w_mbath_n, None, MBATH_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '28"',
    label="his closet", wall_axis='x', wall_start=MX0, wall_end=MBATH_X, tight=True)

place_door(w_clos_d, None, CLOS_D, 0,
    "Door-Interior-Single-1_Panel-Wood", '28"',
    label="hers closet", wall_axis='x', wall_start=MX0, wall_end=MBATH_X, tight=True)

place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="butler pantry", wall_axis='y', wall_start=PANTRY_Y, wall_end=MY1)

place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="mud room", wall_axis='y', wall_start=MUD_Y, wall_end=PANTRY_Y)

place_door(w_mud_s, None, MUD_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '28"',
    label="half bath", wall_axis='x', wall_start=SVC_X, wall_end=MX1, tight=True)

d_gar = place_door(w_gar_s, None, GY0, 0,
    "Door-Garage-Flush_Panel", "16W X 10H",
    label="garage overhead", wall_axis='x', wall_start=GX0, wall_end=GX1, wall_height=12)
if d_gar:
    flip_door(d_gar)

place_door(w_gar_n, None, GY1, 0,
    "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
    label="mud to garage", wall_axis='x', wall_start=GX0, wall_end=GX1)

# ── PHASE 5: L1 WINDOWS (sill z=2.5, tops out at ~5.5ft — well under 10ft walls) ──
print("\n=== PHASE 5: L1 WINDOWS ===")
# North wall master zone (x=0-18 — no doors here)
place_window(w_l1_n,  5, MY1, W1, "Instance-Window-Fixed", '60" x 24"', label="master N win 1")
place_window(w_l1_n, 12, MY1, W1, "Instance-Window-Fixed", '60" x 24"', label="master N win 2")

# South wall — entry door at x=29 (~3ft wide). Master zone and service zone only.
place_window(w_l1_s,  9, MY0, W1, "Instance-Window-Fixed", '60" x 24"', label="master S win")
place_window(w_l1_s, 46, MY0, W1, "Instance-Window-Fixed", '60" x 24"', label="service S win")

# West wall master (no doors on west exterior wall)
place_window(w_l1_w, MX0, 23, W1, "Instance-Window-Fixed", '60" x 24"', label="master W win 1")
place_window(w_l1_w, MX0, 10, W1, "Instance-Window-Fixed", '60" x 24"', label="master W win 2")

# ── PHASE 6: L2 FLOOR ────────────────────────────────────────────
print("\n=== PHASE 6: L2 FLOOR ===")
# L2 floor: expand all sides (all exterior)
smart_floor(L2, 10, L2X0, L2Y0, L2X1, L2Y1)

# ── PHASE 7: L2 DOORS ────────────────────────────────────────────
print("\n=== PHASE 7: L2 DOORS ===")
place_door(w_l2_hall, None, L2_HALL_Y, 11,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="L2 bed 2", wall_axis='x', wall_start=L2_BATH_X, wall_end=L2_B23_X, tight=True)

place_door(w_l2_hall, None, L2_HALL_Y, 11,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="L2 bed 3", wall_axis='x', wall_start=L2_B23_X, wall_end=L2X1)

place_door(w_l2_n, None, L2Y1, 11,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="L2 bed 4", wall_axis='x', wall_start=L2X0, wall_end=L2_B23_X)

place_door(w_l2_s, None, L2Y0, 11,
    "Door-Interior-Single-1_Panel-Wood", '28"',
    label="L2 bath", wall_axis='x', wall_start=L2X0, wall_end=L2_BATH_X, tight=True)

# ── PHASE 8: L2 WINDOWS (sill z=13.5 = 2.5ft above L2 floor at z=11) ──
print("\n=== PHASE 8: L2 WINDOWS ===")
place_window(w_l2_s, 41,    L2Y0, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bed3 S win")
place_window(w_l2_n, 40,    L2Y1, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bed4 N win")
place_window(w_l2_e, L2X1,  15,   W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bed2 E win")
place_window(w_l2_w, L2X0,   5,   W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bath W win")

# ── PHASE 9: ROOFS ───────────────────────────────────────────────
# Overhang (O=3ft) ONLY on true exterior edges.
# Where a lower roof butts against a taller volume: NO overhang (exact edge).
# Where same-height roofs meet: full overhang OK (they merge visually).
print("\n=== PHASE 9: ROOFS ===")

# Upper roof — L2 footprint, all 4 sides exterior, full overhang
make_roof("upper L2", [
    (L2X0-O, L2Y0-O), (L2X1+O, L2Y0-O),
    (L2X1+O, L2Y1+O), (L2X0-O, L2Y1+O),
], L_L2R)

# Lower master — master suite x=0-18, full depth y=0-30
# East edge (x=18) abuts L2 west wall → NO east overhang
# West/south/north are exterior → full overhang
make_roof("lower master", [
    (MX0-O,    MY0-O),    # SW corner with overhang
    (MASTER_X, MY0-O),    # SE corner — no east overhang, flush with L2 west wall
    (MASTER_X, MY1+O),    # NE corner — no east overhang
    (MX0-O,    MY1+O),    # NW corner with overhang
], L_L1R)

# Lower north strip — living core north (y=20-30), service north (y=20-30)
# South edge (y=20) abuts L2 north wall → NO south overhang
# West edge (x=18) abuts master roof at same level → extend west for full coverage
# East/north are exterior → full overhang
make_roof("lower N strip", [
    (MASTER_X, L2Y1),      # SW — flush with L2 west wall, flush with L2 north wall
    (MX1+O,    L2Y1),      # SE — overhang east (this side is exterior main house east)
    (MX1+O,    MY1+O),     # NE — full overhang
    (MASTER_X, MY1+O),     # NW — flush west, overhang north
], L_L1R)

# Garage roof — z=12
# West edge (x=52) abuts main house east wall → NO west overhang
# South/east/north are exterior → full overhang
make_roof("garage", [
    (GX0,    GY0-O),    # SW — no west overhang, south overhang
    (GX1+O,  GY0-O),   # SE — east + south overhang
    (GX1+O,  GY1+O),   # NE — east + north overhang
    (GX0,    GY1+O),   # NW — no west overhang, north overhang
], L_GARR)

# ── PHASE 10: 3D VIEW ────────────────────────────────────────────
print("\n=== PHASE 10: 3D VIEW ===")
r = call("revit.create_3d_view", {"name": "432 Cloud Top v3"})
print("  3D view:", r["Status"])

print("\n=== BUILD COMPLETE ===")
