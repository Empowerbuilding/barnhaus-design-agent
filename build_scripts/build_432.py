"""
build_432.py — 432 Cloud Top
Client: Mitchell Davis Madison
2-story, 4bed/2.5bath, modern-desert, single-slope roof
Main: 52x30ft | Garage: 22x24ft east | 10ft ceilings

Uses barnhaus_revit_utils.py for all rule enforcement.
"""

from barnhaus_revit_utils import (
    create_wall, create_floor, outer_rect,
    place_door, place_window, call, half_thick
)

EXT = 'Wall 7.5" EXT PBR'
INT = 'Wall 4.5 Interior"'
L1  = "Level 1.0"
L2  = "Level 2.0"
H   = 10  # floor-to-floor height

# ─── LAYOUT CONSTANTS ───────────────────────────────────────────
# Main house centerline extents
MX0, MY0, MX1, MY1 = 0, 0, 52, 30
# Garage centerline extents (east of main)
GX0, GY0, GX1, GY1 = 52, 0, 74, 24

# Interior zone boundaries (all on wall centerlines)
MASTER_X   = 20   # master zone east wall
MBED_Y     = 18   # master bed south wall (separates bed from bath/closets)
MBATH_X    = 12   # master bath east wall
MBATH_Y    =  8   # master bath north wall (also closet north wall)
CLOS_X     = 12   # closet east wall (same as MBATH_X)
CLOS_Y     =  4   # his/hers closet divider
SVC_X      = 42   # service corridor west wall
PANTRY_Y   = 20   # butler pantry / mud room divider
MUD_Y      = 10   # mud room / half bath divider
STAIR_W    = 26   # stair west wall
STAIR_E    = 34   # stair east wall
STAIR_N    =  8   # stair north wall

# Level 2 zone boundaries
L2_HALL_S  = 10   # hallway south
L2_HALL_N  = 18   # hallway north
L2_B23_X   = 20   # bed2/bed3 divider
L2_B3BATH  = 36   # bed3/bath divider
L2_B4_X    = 26   # bed4 east wall
L2_B5_X    = 40   # bed5 east wall

# ─── PHASE 1: EXTERIOR WALLS ────────────────────────────────────
print("\n=== PHASE 1: EXTERIOR WALLS ===")
# Level 1 main house
w_l1_s = create_wall(MX0,MY0,0, MX1,MY0,0, L1, EXT, H, "L1 south")
w_l1_n = create_wall(MX0,MY1,0, MX1,MY1,0, L1, EXT, H, "L1 north")
w_l1_w = create_wall(MX0,MY0,0, MX0,MY1,0, L1, EXT, H, "L1 west")
w_l1_e = create_wall(MX1,MY0,0, MX1,MY1,0, L1, EXT, H, "L1 east")

# Level 1 garage (west wall is shared with main east — no separate wall needed)
w_gar_s = create_wall(GX0,GY0,0, GX1,GY0,0, L1, EXT, H, "garage south")
w_gar_e = create_wall(GX1,GY0,0, GX1,GY1,0, L1, EXT, H, "garage east")
w_gar_n = create_wall(GX0,GY1,0, GX1,GY1,0, L1, EXT, H, "garage north")

# Level 2 main house (same footprint)
w_l2_s = create_wall(MX0,MY0,H, MX1,MY0,H, L2, EXT, H, "L2 south")
w_l2_n = create_wall(MX0,MY1,H, MX1,MY1,H, L2, EXT, H, "L2 north")
w_l2_w = create_wall(MX0,MY0,H, MX0,MY1,H, L2, EXT, H, "L2 west")
w_l2_e = create_wall(MX1,MY0,H, MX1,MY1,H, L2, EXT, H, "L2 east")

# ─── PHASE 2: INTERIOR WALLS ────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")
# Level 1
w_master_e = create_wall(MASTER_X,MY0,0,  MASTER_X,MY1,0,  L1, INT, H, "master east")
w_mbed_s   = create_wall(MX0,MBED_Y,0,   MASTER_X,MBED_Y,0, L1, INT, H, "master bed south")
w_mbath_e  = create_wall(MBATH_X,MBATH_Y,0, MBATH_X,MBED_Y,0, L1, INT, H, "master bath east")
w_mbath_n  = create_wall(MX0,MBATH_Y,0,  MBATH_X,MBATH_Y,0, L1, INT, H, "master bath north")
w_clos_e   = create_wall(CLOS_X,MY0,0,   CLOS_X,MBATH_Y,0, L1, INT, H, "closet east")
w_clos_d   = create_wall(MX0,CLOS_Y,0,   CLOS_X,CLOS_Y,0,  L1, INT, H, "closet divider")
w_svc_w    = create_wall(SVC_X,MY0,0,    SVC_X,MY1,0,      L1, INT, H, "service west")
w_pantry_s = create_wall(SVC_X,PANTRY_Y,0, MX1,PANTRY_Y,0, L1, INT, H, "pantry south")
w_mud_s    = create_wall(SVC_X,MUD_Y,0,  MX1,MUD_Y,0,      L1, INT, H, "mud south")
w_stair_n  = create_wall(STAIR_W,STAIR_N,0, STAIR_E,STAIR_N,0, L1, INT, H, "stair north")
w_stair_w  = create_wall(STAIR_W,MY0,0,  STAIR_W,STAIR_N,0, L1, INT, H, "stair west")
w_stair_e  = create_wall(STAIR_E,MY0,0,  STAIR_E,STAIR_N,0, L1, INT, H, "stair east")

# Level 2
w_l2_hall_s = create_wall(MX0,L2_HALL_S,H, MX1,L2_HALL_S,H, L2, INT, H, "L2 hall south")
w_l2_hall_n = create_wall(MX0,L2_HALL_N,H, MX1,L2_HALL_N,H, L2, INT, H, "L2 hall north")
w_l2_b23   = create_wall(L2_B23_X,MY0,H, L2_B23_X,L2_HALL_S,H, L2, INT, H, "L2 bed2/3")
w_l2_b3b   = create_wall(L2_B3BATH,MY0,H, L2_B3BATH,L2_HALL_S,H, L2, INT, H, "L2 bed3/bath")
w_l2_b4    = create_wall(L2_B4_X,L2_HALL_N,H, L2_B4_X,MY1,H, L2, INT, H, "L2 bed4 east")
w_l2_b5    = create_wall(L2_B5_X,L2_HALL_N,H, L2_B5_X,MY1,H, L2, INT, H, "L2 bed5 east")

# ─── PHASE 3: LEVEL 1 FLOOR ─────────────────────────────────────
print("\n=== PHASE 3: L1 FLOORS ===")
# Outer face of exterior walls = centerline ± half_thick
fl1 = create_floor(L1, 0, outer_rect(MX0, MY0, MX1, MY1, EXT))
fl1_gar = create_floor(L1, 0, outer_rect(GX0, GY0, GX1, GY1, EXT))

# ─── PHASE 4: LEVEL 1 DOORS ─────────────────────────────────────
print("\n=== PHASE 4: L1 DOORS ===")
# Front entry: south wall, use segment x=20 to x=26 (master east to stair west = 6ft)
# Too narrow for 6ft double door. Use single entry door (3ft) on segment x=34 to x=42 (8ft).
# 8ft - 2*2ft clearance - 3ft door = 1ft valid → too tight still.
# Best option: segment x=0 to x=20 (20ft, foyer zone). Center at x=10. Clean entry foyer.
# Single 36" door is appropriate — Barnhaus often has a statement single pivot entry.
place_door(w_l1_s, None, 0, 0,
           "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
           label="front entry",
           wall_axis='x', wall_start=MX0, wall_end=MASTER_X)

# Rear patio slider: north wall, centered in great room (x=20 to x=42 = 22ft)
# 22ft - 2*3ft clearance - 4ft door = 12ft valid range → center at x=31
place_door(w_l1_n, None, 30, 0,
           "Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00",
           label="rear patio",
           wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

# Master bedroom door: master east wall (y=0 to y=30), segment in master bed zone (y=18 to y=30)
# 12ft segment, 3ft door → valid: y=21 to y=27 → center y=24
place_door(w_master_e, 20, None, 0,
           "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
           label="master bed",
           wall_axis='y', wall_start=MBED_Y, wall_end=MY1)

# Master bath door: master bed south wall (x=0 to x=20), place at x=6
# Segment x=0 to x=12 (bath east wall at x=12), 12ft → center x=6
place_door(w_mbed_s, None, 18, 0,
           "Door-Interior-Single-1_Panel-Wood", '32" x 96"',
           label="master bath",
           wall_axis='x', wall_start=MX0, wall_end=MBATH_X)

# His closet door: master bath north wall (x=0 to x=12), center x=6
place_door(w_mbath_n, None, MBATH_Y, 0,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="his closet",
           wall_axis='x', wall_start=MX0, wall_end=MBATH_X)

# Hers closet door: closet divider (x=0 to x=12), center x=6
place_door(w_clos_d, None, CLOS_Y, 0,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="hers closet",
           wall_axis='x', wall_start=MX0, wall_end=CLOS_X)

# Half bath door: mud/halfbath divider (x=42 to x=52 = 10ft), center x=47
place_door(w_mud_s, None, MUD_Y, 0,
           "Door-Interior-Single-1_Panel-Wood", '28"',
           label="half bath",
           wall_axis='x', wall_start=SVC_X, wall_end=MX1)

# Butler pantry: service wall (y=20 to y=30 = 10ft), center y=25
place_door(w_svc_w, SVC_X, None, 0,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="butler pantry",
           wall_axis='y', wall_start=PANTRY_Y, wall_end=MY1)

# Mud room: service wall (y=10 to y=20 = 10ft), center y=15
place_door(w_svc_w, SVC_X, None, 0,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="mud room",
           wall_axis='y', wall_start=MUD_Y, wall_end=PANTRY_Y)

# Garage overhead: garage south wall (x=52 to x=74 = 22ft), centered = x=63
place_door(w_gar_s, None, 0, 0,
           "Door-Garage-Flush_Panel", "16W X 10H",
           label="garage overhead",
           wall_axis='x', wall_start=GX0, wall_end=GX1)

# Garage walk-in: mud south wall (x=42 to x=52 = 10ft)
# NOTE: NOT on the east wall (joining wall between main and garage)
place_door(w_mud_s, None, MUD_Y, 0,
           "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
           label="garage walk-in",
           wall_axis='x', wall_start=SVC_X, wall_end=MX1)

# ─── PHASE 4b: LEVEL 1 WINDOWS ──────────────────────────────────
print("\n=== PHASE 4b: L1 WINDOWS ===")
# List available window families
wf = call("revit.list_families", {"category": "Windows"})
print("  Available window families:")
for f in wf["Result"]["families"][:8]:
    for t in f["types"][:2]:
        print(f"    {f['name']} : {t['name']}")

# ─── PHASE 5: LEVEL 2 FLOOR ─────────────────────────────────────
print("\n=== PHASE 5: L2 FLOOR ===")
fl2 = create_floor(L2, 11, outer_rect(MX0, MY0, MX1, MY1, EXT))

# ─── PHASE 6: LEVEL 2 DOORS ─────────────────────────────────────
print("\n=== PHASE 6: L2 DOORS ===")
# Bed 2: L2 hall south wall, segment x=0 to x=20 = 20ft → center x=10
place_door(w_l2_hall_s, None, L2_HALL_S, 11,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="bed 2",
           wall_axis='x', wall_start=MX0, wall_end=L2_B23_X)

# Bed 3: L2 hall south wall, segment x=20 to x=36 = 16ft → center x=28
place_door(w_l2_hall_s, None, L2_HALL_S, 11,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="bed 3",
           wall_axis='x', wall_start=L2_B23_X, wall_end=L2_B3BATH)

# Shared bath: L2 hall south wall, segment x=36 to x=52 = 16ft → center x=44
place_door(w_l2_hall_s, None, L2_HALL_S, 11,
           "Door-Interior-Single-1_Panel-Wood", '28"',
           label="L2 bath",
           wall_axis='x', wall_start=L2_B3BATH, wall_end=MX1)

# Bed 4: L2 hall north wall, segment x=0 to x=26 = 26ft → center x=13
place_door(w_l2_hall_n, None, L2_HALL_N, 11,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="bed 4",
           wall_axis='x', wall_start=MX0, wall_end=L2_B4_X)

# Bed 5: L2 hall north wall, segment x=26 to x=40 = 14ft → center x=33
place_door(w_l2_hall_n, None, L2_HALL_N, 11,
           "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
           label="bed 5",
           wall_axis='x', wall_start=L2_B4_X, wall_end=L2_B5_X)

print("\n=== BUILD COMPLETE — check Revit ===")
