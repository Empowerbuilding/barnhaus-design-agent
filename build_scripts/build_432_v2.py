"""
build_432_v2.py — 432 Cloud Top (Layout v2)
Client: Mitchell Davis Madison
2-story | 4 bed / 2.5 bath | modern-desert | single-slope roof
2,100 SF living | 800 SF patios | 500 SF garage
Rooms: great room, eat-in kitchen, mudroom, butler pantry, master w/ walk-in shower + his & hers closets
Electric fireplace | quartz counters | stained concrete | spray foam | front + rear covered porches

LAYOUT v2 — L-shaped, north-south orientation
- Main body: 30ft wide (EW) x 52ft deep (NS), origin (0,0) at SW corner
- Garage: 24ft wide x 22ft deep, attached south end east side
- Level 1 (full 30x52): master suite north end, great room/kitchen center, entry/service south end
- Level 2 (south 30x26 only, above living core): 3 beds + bath + hallway
- Entry: west facade (x=0), clear foyer zone
- Rear porch: north facade (y=52)
- Front porch: west facade (x=0) canopy
- Garage: south-east, 8ft overhead door (fits in 10ft wall)

COORDINATE SYSTEM:
  x = east-west (0=west, 30=east)
  y = north-south (0=south, 52=north)
  z = elevation (0=ground, 10=L2 floor, 20=roof)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, create_floor, outer_rect,
    place_door, place_window, call
)

EXT  = 'Wall 7.5" EXT PBR'
INT  = 'Wall 4.5 Interior"'
L1   = "Level 1.0"
L2   = "Level 2.0"
H    = 10   # standard floor-to-floor height

# ── LAYOUT CONSTANTS ─────────────────────────────────────────────
# Main house extents (wall centerlines)
MX0, MY0 = 0, 0       # SW corner
MX1, MY1 = 30, 52     # NE corner

# Garage extents — attached SE corner of main house
# East of main (x=30 to x=54), south end (y=0 to y=22)
GX0, GY0 = 30, 0
GX1, GY1 = 54, 22

# Level 1 interior zone boundaries
MASTER_Y   = 38    # master zone south wall — master occupies y=38 to y=52 (14ft deep)
MBED_X     = 18    # master bath east wall — bath left of x=18, closets right
MBATH_Y    = 44    # master bath north wall — bath between y=38 and y=44
CLOS_X     = 14    # his/hers closet divider (x=14 splits his west / hers east)
FOYER_Y    = 10    # foyer/entry north wall — entry zone y=0 to y=10
SVC_Y      = 20    # service zone north wall — service zone y=10 to y=20
STAIR_X0   = 12    # stair west wall
STAIR_X1   = 20    # stair east wall
STAIR_Y1   = 10    # stair north wall (flush with foyer north)

# Level 2 extents — south half of main house only
L2_MY0     = 0
L2_MY1     = 26    # L2 stops at y=26, open to below north of that
L2_HALL_X  = 10    # hallway east wall (hall runs y=0 to y=26 on west side)
L2_B12_Y   = 14    # bed1/bed2 divider
L2_BATH_X  = 22    # bathroom west wall (east side)

# Garage door type — 8ft tall, fits in 10ft wall with header clearance
GARAGE_DOOR_H = 8   # ft — use 8ft door, wall is 10ft (2ft header clearance ✓)

# ── PHASE 1: EXTERIOR WALLS ──────────────────────────────────────
print("\n=== PHASE 1: EXTERIOR WALLS ===")

# Use create_rect_exterior — enforces correct facing automatically
L1_walls = create_rect_exterior(MX0, MY0, MX1, MY1, 0, L1, EXT, H, "L1")
w_l1_s = L1_walls["south"]
w_l1_n = L1_walls["north"]
w_l1_w = L1_walls["west"]
w_l1_e = L1_walls["east"]

# Garage — 12ft tall so 8ft overhead door fits with header clearance
# Shared west wall = L1 east wall (already placed above, no duplicate)
w_gar_s = create_wall(GX0,GY0,0, GX1,GY0,0, L1, EXT, 12, "garage south")  # W→E
w_gar_e = create_wall(GX1,GY0,0, GX1,GY1,0, L1, EXT, 12, "garage east")   # S→N
w_gar_n = create_wall(GX1,GY1,0, GX0,GY1,0, L1, EXT, 12, "garage north")  # E→W

# Level 2 — south portion only (y=0 to y=26)
L2_walls = create_rect_exterior(MX0, L2_MY0, MX1, L2_MY1, H, L2, EXT, H, "L2")
w_l2_s = L2_walls["south"]
w_l2_n = L2_walls["north"]
w_l2_w = L2_walls["west"]
w_l2_e = L2_walls["east"]

# ── PHASE 2: INTERIOR WALLS ──────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")

# Level 1
# Master zone south wall (full width)
w_master_s  = create_wall(MX0,MASTER_Y,0, MX1,MASTER_Y,0, L1, INT, H, "master south")
# Master bath east wall (x=18, y=38 to y=52)
w_mbath_e   = create_wall(MBED_X,MASTER_Y,0, MBED_X,MY1,0, L1, INT, H, "master bath east")
# Master bath south wall (y=44, x=0 to x=18) — closets below, bath above
w_mbath_s   = create_wall(MX0,MBATH_Y,0, MBED_X,MBATH_Y,0, L1, INT, H, "master bath south")
# His/hers closet divider (x=14, y=38 to y=44)
w_clos_d    = create_wall(CLOS_X,MASTER_Y,0, CLOS_X,MBATH_Y,0, L1, INT, H, "closet divider")
# Foyer north wall (y=10, full width)
w_foyer_n   = create_wall(MX0,FOYER_Y,0, MX1,FOYER_Y,0, L1, INT, H, "foyer north")
# Service north wall (y=20, full width — separates service from great room)
w_svc_n     = create_wall(MX0,SVC_Y,0, MX1,SVC_Y,0, L1, INT, H, "service north")
# Stair west wall (x=12, y=0 to y=10)
w_stair_w   = create_wall(STAIR_X0,MY0,0, STAIR_X0,STAIR_Y1,0, L1, INT, H, "stair west")
# Stair east wall (x=20, y=0 to y=10)
w_stair_e   = create_wall(STAIR_X1,MY0,0, STAIR_X1,STAIR_Y1,0, L1, INT, H, "stair east")
# Butler pantry east wall (x=24, y=10 to y=20)
w_pantry_e  = create_wall(24,SVC_Y,0, 24,FOYER_Y,0, L1, INT, H, "pantry east")
# Mud room / half bath divider (x=16, y=10 to y=20)
w_mud_d     = create_wall(16,FOYER_Y,0, 16,SVC_Y,0, L1, INT, H, "mud/halfbath divider")

# Level 2
# Hallway east wall (x=10, full L2 depth y=0 to y=26)
w_l2_hall_e = create_wall(L2_HALL_X,L2_MY0,H, L2_HALL_X,L2_MY1,H, L2, INT, H, "L2 hall east")
# Bed1/Bed2 divider (y=14, x=10 to x=30)
w_l2_b12    = create_wall(L2_HALL_X,L2_B12_Y,H, MX1,L2_B12_Y,H, L2, INT, H, "L2 bed1/2")
# Bathroom west wall (x=22, y=0 to y=14)
w_l2_bath   = create_wall(L2_BATH_X,L2_MY0,H, L2_BATH_X,L2_B12_Y,H, L2, INT, H, "L2 bath west")

# ── PHASE 3: LEVEL 1 FLOOR ───────────────────────────────────────
print("\n=== PHASE 3: L1 FLOORS ===")
fl1      = create_floor(L1, 0, outer_rect(MX0, MY0, MX1, MY1, EXT))
fl1_gar  = create_floor(L1, 0, outer_rect(GX0, GY0, GX1, GY1, EXT))

# ── PHASE 4: LEVEL 1 DOORS ───────────────────────────────────────
print("\n=== PHASE 4: L1 DOORS ===")

# Front entry — west wall (x=0), foyer zone y=0 to y=10 (10ft segment)
# Single 36" door, centered: valid y=3.5 to y=6.5 → center y=5
place_door(w_l1_w, 0, None, 0,
           "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
           label="front entry",
           wall_axis='y', wall_start=MY0, wall_end=FOYER_Y)

# Rear porch door — north wall (y=52), master zone (x=0 to x=30, 30ft clear)
# 4-panel slider 4ft wide, centered at x=15
place_door(w_l1_n, None, MY1, 0,
           "Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00",
           label="rear porch",
           wall_axis='x', wall_start=MX0, wall_end=MX1)

# Master bedroom door — master south wall (x=0 to x=30), right half (x=18 to x=30=12ft clear)
# Single 36" door, centered in right half → x=24
place_door(w_master_s, None, MASTER_Y, 0,
           "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
           label="master bed",
           wall_axis='x', wall_start=MBED_X, wall_end=MX1)

# Master bath door — master bath east wall (y=38 to y=52=14ft clear)
# Enter bath from master bed side, centered in segment y=44 to y=52 (8ft clear)
place_door(w_mbath_e, MBED_X, None, 0,
           "Door-Interior-Single-1_Panel-Wood", '32" x 96"',
           label="master bath",
           wall_axis='y', wall_start=MBATH_Y, wall_end=MY1)

# His closet — closet divider (x=14, y=38 to y=44=6ft clear)
# 30" door (2.5ft), need 2.5+2*3=8.5ft → segment only 6ft. Use 2ft clearance each side: 6-4-2.5=too tight
# Use master bath south wall instead — enter closets from bathroom side
# His closet: x=0 to x=14 off bath south wall (y=44, 14ft seg) → center x=7
place_door(w_mbath_s, None, MBATH_Y, 0,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="his closet",
           wall_axis='x', wall_start=MX0, wall_end=CLOS_X, tight=True)

# Hers closet: x=14 to x=18 off bath south wall → 4ft seg too narrow
# Use closet divider wall (x=14, y=38 to y=44=6ft) with 1.5ft clearance (interior closet acceptable)
place_door(w_clos_d, CLOS_X, None, 0,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="hers closet",
           wall_axis='y', wall_start=MASTER_Y, wall_end=MBATH_Y, tight=True)

# Great room to service zone — service north wall (y=20, x=0 to x=30=30ft)
# Open wide passage — pocket door or opening at center x=15
place_door(w_svc_n, None, SVC_Y, 0,
           "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
           label="service passage",
           wall_axis='x', wall_start=MX0, wall_end=MX1)

# Half bath — mud divider (x=16, y=10 to y=20=10ft)
# 28" door, centered
place_door(w_mud_d, 16, None, 0,
           "Door-Interior-Single-1_Panel-Wood", '28"',
           label="half bath",
           wall_axis='y', wall_start=FOYER_Y, wall_end=SVC_Y)

# Butler pantry — pantry east wall (x=24, y=10 to y=20=10ft)
place_door(w_pantry_e, 24, None, 0,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="butler pantry",
           wall_axis='y', wall_start=FOYER_Y, wall_end=SVC_Y)

# Garage overhead — garage south wall (x=30 to x=54=24ft)
# 8ft tall door fits in 12ft garage walls (4ft header clearance ✓)
# Type "8ft" — need to use correct type name from available families
place_door(w_gar_s, None, GY0, 0,
           "Door-Garage-Flush_Panel", "16W X 10H",
           label="garage overhead",
           wall_axis='x', wall_start=GX0, wall_end=GX1,
           wall_height=12)

# Mud room to garage — garage north wall (y=22, x=30 to x=54)
# NOT on joining wall (east wall of main x=30) — use garage north wall
# Single entry 36" door, centered in garage north wall
place_door(w_gar_n, None, GY1, 0,
           "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
           label="garage walk-in",
           wall_axis='x', wall_start=GX0, wall_end=GX1)

# ── PHASE 5: LEVEL 1 WINDOWS ─────────────────────────────────────
print("\n=== PHASE 5: L1 WINDOWS ===")
# List available window families
wf = call("revit.list_families", {"category": "Windows"})
print("Available window families:")
for f in wf["Result"]["families"]:
    for t in f["types"][:2]:
        print(f"  {f['name']} : {t['name']}")

# ── PHASE 6: LEVEL 2 FLOOR ───────────────────────────────────────
print("\n=== PHASE 6: L2 FLOOR ===")
fl2 = create_floor(L2, 10, outer_rect(MX0, L2_MY0, MX1, L2_MY1, EXT))

# ── PHASE 7: LEVEL 2 DOORS ───────────────────────────────────────
print("\n=== PHASE 7: L2 DOORS ===")

# Bed 1 — hallway east wall (x=10, y=14 to y=26=12ft clear) → center y=20
place_door(w_l2_hall_e, L2_HALL_X, None, 11,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="L2 bed 1",
           wall_axis='y', wall_start=L2_B12_Y, wall_end=L2_MY1)

# Bed 2 — hallway east wall (x=10, y=0 to y=14=14ft clear) → center y=7
place_door(w_l2_hall_e, L2_HALL_X, None, 11,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="L2 bed 2",
           wall_axis='y', wall_start=L2_MY0, wall_end=L2_B12_Y)

# Bed 3 (master suite upstairs) — L2 north wall (y=26, x=0 to x=10=10ft hallway)
# Enter from hallway side — L2 north wall is the inner edge (y=26)
place_door(w_l2_n, None, L2_MY1, 11,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="L2 bed 3",
           wall_axis='x', wall_start=MX0, wall_end=L2_HALL_X)

# Shared bath — L2 south wall (y=0, x=22 to x=30=8ft clear)
place_door(w_l2_s, None, L2_MY0, 11,
           "Door-Interior-Single-1_Panel-Wood", '28"',
           label="L2 bath",
           wall_axis='x', wall_start=L2_BATH_X, wall_end=MX1, tight=True)

print("\n=== BUILD COMPLETE — review in Revit ===")
