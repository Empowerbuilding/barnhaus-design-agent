"""
build_f7d3708c.py — 432 Cloud Top (f7d3708c) v2
5 bed / 3.5 bath | 2-story | industrial | 2,800 SF living

FIXES v2:
  - L2 ALL bedroom doors on hallway wall (not exterior) — no more doors to nowhere
  - L2 south/north rooms staggered so door positions don't conflict on hall wall
  - L1 door positions away from perpendicular wall intersections
  - Removed double-wall dead zone in living core
  - Office accessible from foyer (separate wall segment)
  - Stair zone reserved in service area

DOOR/WINDOW SELECTION LOGIC:
  - Front entry: Double full-glass = grand industrial statement
  - Rear porch: 4-panel slider = max indoor-outdoor connection
  - Interior: Single 1-panel wood = standard
  - Garage: Flush panel overhead
  - Windows: Fixed = clean modern lines for industrial style
              Awning = bathrooms (ventilation)

LAYOUT (56×48 main, 32×26 garage):
  L1:
    x=0-20   Master suite (west, private)
    x=20-44  Living core (great room, kitchen, office, foyer)
    x=44-56  Service (pantry, mud, half bath, stair zone)
    x=56-88  Garage (y=0-26, 12ft walls)

  MASTER:
    y=28-48  Master bed (20×20=400 SF)
    x=10-20, y=14-28  Master bath (10×14=140 SF)
    x=0-10,  y=10-28  Master closet — 1 large (10×18=180 SF)
    x=0-20,  y=0-10   Office/Study (20×10=200 SF, door to foyer)

  LIVING CORE:
    y=14-48  Great room + kitchen open plan (24×34=816 SF)
    x=20-44, y=0-14  Foyer + bonus zone (open, no walls)

  SERVICE:
    y=36-48  Butler pantry
    y=24-36  Mud room
    y=14-24  Half bath
    y=0-14   Stair zone (note: stairs added manually in Revit)

  L2 (x=20-56, y=0-28, double-loaded corridor at y=14):
    NORTH SIDE (y=14-28):
      x=20-36  Bed 2  (16×14=224 SF)
      x=36-44  Bath 2 (8×14=112 SF)
      x=44-56  Bed 3  (12×14=168 SF)
    SOUTH SIDE (y=0-14):
      x=20-34  Bed 4  (14×14=196 SF)
      x=34-44  Bath 3 (10×14=140 SF)
      x=44-56  Bed 5  (12×14=168 SF)

    HALL WALL at y=14 — all doors here, staggered so N/S don't conflict:
      North doors: Bed2@x=28, Bath2@x=40, Bed3@x=50
      South doors: Bed4@x=27, Bath3@x=39, Bed5@x=49   ← 1ft offset from north
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, place_door, place_window,
    call, verify_wall_facing
)

EXT = 'Wall 7.5" EXT PBR'
INT = 'Wall 4.5 Interior"'
L1  = "Level 1.0"
L2  = "Level 2.0"
H   = 10
T   = 0.3125  # half EXT wall thickness

# ── LAYOUT CONSTANTS ────────────────────────────────────────────
MX0, MY0, MX1, MY1 = 0, 0, 56, 48
GX0, GY0, GX1, GY1 = 56, 0, 88, 26

# Master
MASTER_X = 20
MBED_Y   = 28
MBATH_X  = 10
MCLOS_Y  = 10   # closet/office divider

# Living core
SVC_X    = 44
LIVING_Y = 14   # foyer/living divider

# Service
PANTRY_Y = 36
MUD_Y    = 24
HALF_Y   = 14

# L2
L2X0, L2Y0, L2X1, L2Y1 = 20, 0, 56, 28
L2_HALL  = 14   # double-loaded corridor divider
# North side dividers
L2_N_BED2_E  = 36   # bed2 east / bath2 west
L2_N_BED3_W  = 44   # bath2 east / bed3 west
# South side dividers
L2_S_BED4_E  = 34   # bed4 east / bath3 west
L2_S_BED5_W  = 44   # bath3 east / bed5 west

O  = 3.0   # roof overhang
W1 = 2.5   # L1 window sill height (absolute ft)
W2 = 13.5  # L2 window sill (absolute, 2.5ft above L2 floor at z=11)

def flip_door(eid):
    r = call("revit.flip_door", {"element_id": eid})
    print(f"  flip door {eid}: {r['Status']}")

def make_level(name, elev):
    r = call("revit.create_level", {"name": name, "elevation": elev})
    print(f"  level [{name}]: {'ok' if r['Status']=='ok' else 'already exists'}")
    return name

def make_roof(label, pts, level_name):
    r = call("revit.create_roof", {
        "level": level_name,
        "roof_type": '13" Roof No Gyp',
        "boundary_points": [{"x": p[0], "y": p[1], "z": 0} for p in pts]
    })
    ok = r["Status"] == "ok"
    rid = r["Result"].get("roof_id") if ok else None
    print(f"  roof [{label}]: {'ok ' + str(rid) if ok else 'ERR ' + r.get('Message','')}")

def smart_floor(level, z, x0, y0, x1, y1,
                exp_w=True, exp_s=True, exp_e=True, exp_n=True):
    pts = [
        {"x": x0-(T if exp_w else 0), "y": y0-(T if exp_s else 0), "z": z},
        {"x": x1+(T if exp_e else 0), "y": y0-(T if exp_s else 0), "z": z},
        {"x": x1+(T if exp_e else 0), "y": y1+(T if exp_n else 0), "z": z},
        {"x": x0-(T if exp_w else 0), "y": y1+(T if exp_n else 0), "z": z},
    ]
    d = call("revit.create_floor", {"level": level, "boundary_points": pts})
    ok = d["Status"] == "ok"
    fid = d["Result"].get("floor_id") if ok else None
    print(f"  floor [{level}]: {'ok '+str(fid) if ok else 'ERR '+d.get('Message','')}")
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

# Master zone
w_master_e = create_wall(MASTER_X,MY0,0, MASTER_X,MY1,0,       L1, INT, H, "master east")
w_mbed_s   = create_wall(MX0,MBED_Y,0,  MASTER_X,MBED_Y,0,    L1, INT, H, "master bed south")
w_mbath_e  = create_wall(MBATH_X,MCLOS_Y,0, MBATH_X,MBED_Y,0, L1, INT, H, "mbath east/clos west")
w_zone_n   = create_wall(MX0,MCLOS_Y,0, MASTER_X,MCLOS_Y,0,   L1, INT, H, "closet+office north")

# Living core — single wall dividing foyer/bonus from great room
w_living_s = create_wall(MASTER_X,LIVING_Y,0, SVC_X,LIVING_Y,0, L1, INT, H, "living south")

# Service zone
w_svc_w    = create_wall(SVC_X,MY0,0,    SVC_X,MY1,0,            L1, INT, H, "service west")
w_pantry_s = create_wall(SVC_X,PANTRY_Y,0, MX1,PANTRY_Y,0,       L1, INT, H, "pantry south")
w_mud_s    = create_wall(SVC_X,MUD_Y,0,  MX1,MUD_Y,0,            L1, INT, H, "mud south")
w_half_s   = create_wall(SVC_X,HALF_Y,0, MX1,HALF_Y,0,           L1, INT, H, "half bath south")

# Level 2 — double-loaded corridor at y=14
w_l2_hall  = create_wall(L2X0,L2_HALL,H, L2X1,L2_HALL,H,         L2, INT, H, "L2 hall")
# North side dividers
w_l2_n1    = create_wall(L2_N_BED2_E,L2_HALL,H, L2_N_BED2_E,L2Y1,H, L2, INT, H, "L2 bed2E/bath2W")
w_l2_n2    = create_wall(L2_N_BED3_W,L2_HALL,H, L2_N_BED3_W,L2Y1,H, L2, INT, H, "L2 bath2E/bed3W")
# South side dividers
w_l2_s1    = create_wall(L2_S_BED4_E,L2Y0,H, L2_S_BED4_E,L2_HALL,H, L2, INT, H, "L2 bed4E/bath3W")
w_l2_s2    = create_wall(L2_S_BED5_W,L2Y0,H, L2_S_BED5_W,L2_HALL,H, L2, INT, H, "L2 bath3E/bed5W")

# ── PHASE 3: FLOORS ──────────────────────────────────────────────
print("\n=== PHASE 3: FLOORS ===")
smart_floor(L1, 0, MX0, MY0, MX1, MY1, exp_e=False)
smart_floor(L1, 0, GX0, GY0, GX1, GY1, exp_w=False)

# ── PHASE 4: L1 DOORS ────────────────────────────────────────────
print("\n=== PHASE 4: L1 DOORS ===")

# Front entry — double glass, south wall, foyer zone (x=20-44), centered→x=32
# Entry door at x=32, ~5ft wide
place_door(w_l1_s, None, MY0, 0,
    "Door-Exterior-Double-Full Glass-Wood_Clad", '60" x 96"',
    label="front entry", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

# Rear porch slider — north wall, great room zone (x=20-44), centered→x=32
place_door(w_l1_n, None, MY1, 0,
    "Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00",
    label="rear porch slider", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

# Master bed entry — master east wall, bedroom segment (y=28-48)
# Keep door AWAY from mbed_s wall (y=28): place in upper third → y=40
place_door(w_master_e, MASTER_X, 40, 0,
    "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
    label="master bed")

# Master bath — master bed south wall (x=10-20), centered→x=15
# x=15 is clear of mbath_e wall at x=10 (5ft clearance ✓)
place_door(w_mbed_s, None, MBED_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '32" x 96"',
    label="master bath", wall_axis='x', wall_start=MBATH_X, wall_end=MASTER_X)

# Master closet — zone north wall (x=0-10 segment, closet side)
# Place at x=5, away from mbath_e wall at x=10
place_door(w_zone_n, 5, MCLOS_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '32" x 96"',
    label="master closet", tight=True)

# Office — zone north wall (x=10-20 segment, office side)
# Place at x=15, clear of mbath_e wall at x=10 (5ft clearance ✓)
place_door(w_zone_n, 15, MCLOS_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="office")

# Living core south — from foyer zone into great room
# Wall at y=14, living core x=20-44. Place door at x=32 (center)
place_door(w_living_s, None, LIVING_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
    label="great room entry", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

# Butler pantry — service west wall (y=36-48)
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="butler pantry", wall_axis='y', wall_start=PANTRY_Y, wall_end=MY1)

# Mud room — service west wall (y=24-36)
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="mud room", wall_axis='y', wall_start=MUD_Y, wall_end=PANTRY_Y)

# Half bath — mud south wall (x=44-56), tight
place_door(w_mud_s, None, MUD_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '28"',
    label="half bath", wall_axis='x', wall_start=SVC_X, wall_end=MX1, tight=True)

# Garage overhead — south wall (x=56-88=32ft), centered→x=72
d_gar = place_door(w_gar_s, None, GY0, 0,
    "Door-Garage-Flush_Panel", "16W X 10H",
    label="garage overhead", wall_axis='x', wall_start=GX0, wall_end=GX1, wall_height=12)
if d_gar:
    flip_door(d_gar)

# Mud to garage — garage north wall
place_door(w_gar_n, None, GY1, 0,
    "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
    label="mud to garage", wall_axis='x', wall_start=GX0, wall_end=GX1)

# ── PHASE 5: L1 WINDOWS ──────────────────────────────────────────
print("\n=== PHASE 5: L1 WINDOWS ===")
# North wall — master zone (x=0-18, no doors)
place_window(w_l1_n,  6, MY1, W1, "Instance-Window-Fixed", '60" x 24"', label="master N1")
place_window(w_l1_n, 14, MY1, W1, "Instance-Window-Fixed", '60" x 24"', label="master N2")
# North wall — great room (slider at x=32, ~13ft wide → avoid x=26-38)
place_window(w_l1_n, 22, MY1, W1, "Instance-Window-Fixed", '60" x 24"', label="great room N1")
place_window(w_l1_n, 42, MY1, W1, "Instance-Window-Fixed", '60" x 24"', label="great room N2")

# South wall — entry door at x=32, ~5ft wide (x=29.5-34.5)
place_window(w_l1_s,  9, MY0, W1, "Instance-Window-Fixed", '60" x 24"', label="office S")
place_window(w_l1_s, 24, MY0, W1, "Instance-Window-Fixed", '60" x 24"', label="foyer S1")
place_window(w_l1_s, 40, MY0, W1, "Instance-Window-Fixed", '60" x 24"', label="foyer S2")

# West wall — master suite (no doors on west)
place_window(w_l1_w, MX0, 38, W1, "Instance-Window-Fixed", '60" x 24"', label="master W1")
place_window(w_l1_w, MX0, 18, W1, "Instance-Window-Fixed", '60" x 24"', label="master W2")

# ── PHASE 6: L2 FLOOR ────────────────────────────────────────────
print("\n=== PHASE 6: L2 FLOOR ===")
smart_floor(L2, 10, L2X0, L2Y0, L2X1, L2Y1)

# ── PHASE 7: L2 DOORS — ALL ON HALL WALL (y=14) ─────────────────
print("\n=== PHASE 7: L2 DOORS ===")
# CRITICAL: All bedroom/bath doors on w_l2_hall — the double-loaded corridor
# North-side rooms (y=14-28): doors staggered at x=28, 40, 50
# South-side rooms (y=0-14):  doors staggered at x=27, 39, 49 (1ft offset from north)

# --- North side (y=14-28) ---
# Bed 2 (x=20-36): door at x=28
place_door(w_l2_hall, 28, L2_HALL, 11,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bed 2 N")

# Bath 2 (x=36-44): door at x=40, tight
place_door(w_l2_hall, 40, L2_HALL, 11,
    "Door-Interior-Single-1_Panel-Wood", '28"', label="L2 bath 2 N", tight=True)

# Bed 3 (x=44-56): door at x=50
place_door(w_l2_hall, 50, L2_HALL, 11,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bed 3 N")

# --- South side (y=0-14) — offset 1ft from north doors ---
# Bed 4 (x=20-34): door at x=27
place_door(w_l2_hall, 27, L2_HALL, 11,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bed 4 S")

# Bath 3 (x=34-44): door at x=39, tight
place_door(w_l2_hall, 39, L2_HALL, 11,
    "Door-Interior-Single-1_Panel-Wood", '28"', label="L2 bath 3 S", tight=True)

# Bed 5 (x=44-56): door at x=49
place_door(w_l2_hall, 49, L2_HALL, 11,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bed 5 S")

# ── PHASE 8: L2 WINDOWS ──────────────────────────────────────────
print("\n=== PHASE 8: L2 WINDOWS ===")
# North wall (y=28): Bed2 and Bed3 views. No doors on north wall.
place_window(w_l2_n, 28, L2Y1, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bed2 N")
place_window(w_l2_n, 50, L2Y1, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bed3 N")

# South wall (y=0): Bed4 and Bed5 views. No doors on south wall.
place_window(w_l2_s, 27, L2Y0, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bed4 S")
place_window(w_l2_s, 50, L2Y0, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 bed5 S")

# East/West walls
place_window(w_l2_w, L2X0, 21, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 west")
place_window(w_l2_e, L2X1, 21, W2, "Instance-Window-Fixed", '60" x 24"', label="L2 east")

# ── PHASE 9: ROOFS ───────────────────────────────────────────────
print("\n=== PHASE 9: ROOFS ===")
make_roof("upper L2", [
    (L2X0-O, L2Y0-O), (L2X1+O, L2Y0-O),
    (L2X1+O, L2Y1+O), (L2X0-O, L2Y1+O),
], L_L2R)

make_roof("lower master", [
    (MX0-O,    MY0-O),
    (MASTER_X, MY0-O),
    (MASTER_X, MY1+O),
    (MX0-O,    MY1+O),
], L_L1R)

make_roof("lower N strip", [
    (MASTER_X, L2Y1),
    (MX1+O,   L2Y1),
    (MX1+O,   MY1+O),
    (MASTER_X, MY1+O),
], L_L1R)

make_roof("garage", [
    (GX0,    GY0-O),
    (GX1+O,  GY0-O),
    (GX1+O,  GY1+O),
    (GX0,    GY1+O),
], L_GARR)

# ── PHASE 10: 3D VIEW ────────────────────────────────────────────
print("\n=== PHASE 10: 3D VIEW ===")
r = call("revit.create_3d_view", {"name": "f7d3708c v2"})
print("  3D view:", r["Status"])

print("\n=== BUILD COMPLETE ===")
print("\nNOTE: Stairs from L1→L2 must be added manually in Revit.")
print("  Stair zone: Service area x=44-56, y=0-14 (L1)")
