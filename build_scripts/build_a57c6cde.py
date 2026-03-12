"""
build_a57c6cde.py — Mitchell Davis Madison (a57c6cde)
4,500 SF living | 2-story | Hill Country | Gable roof
Rooms: great room, eat-in kitchen, butler pantry, office, media, game room,
       golf simulator, laundry, master suite (freestanding tub, his/hers closet)
Garage: 2-car side-load (door on east face)

LAYOUT:
  L1 (72×30):
    x=0-26   Master suite
               y=14-30  Master bedroom (26×16)
               x=0-13, y=0-14  Master bath (freestanding tub, walk-in shower, double vanity)
               x=13-26, y=0-14  His/hers closets
    x=26-54  Living core
               y=14-30  Great room + dining (28×16) + fireplace on north wall
               y=0-14   Eat-in kitchen + island + butler pantry (x=48-54)
    x=54-72  Service wing
               y=18-30  Office/study (18×12)
               y=8-18   Laundry room (18×10)
               y=0-8    Mudroom + half bath (18×8)
               x=64-72  Stair zone
    Garage: x=72-100, y=0-26 (28×26, door on east)

  L2 (x=26-72, y=0-30), corridor center y=15 (walls y=13, y=17):
    North (y=17-30, 13ft deep):
               x=26-46  Media room (20×13)
               x=46-56  Bed 2 (10×13)
               x=56-64  Bath 2 (8×13, in-suite)
               x=64-72  Bed 3 (8×13)
    South (y=0-13, 13ft deep):
               x=26-52  Golf simulator (26×13 — single bay)
               x=52-62  Game room (10×13)
               x=62-72  Bed 4 (10×13)
               Bath 3: shared off corridor, built into game/bed4 zone
"""

import sys, time
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, create_garage,
    place_door, place_window,
    smart_floor, make_roof,
    create_double_loaded_corridor, create_stairs,
    create_room, label_rooms,
    layout_kitchen, layout_bath_standard, layout_bath_master,
    layout_half_bath, layout_laundry, place_fixture, _cab,
    attach_walls_to_roof, set_wall_height,
    call, T, WIN
)

# ── CONSTANTS ────────────────────────────────────────────────────
EXT = 'Wall 7.5" EXT PBR'
INT = 'Wall 4.5 Interior"'
L1    = "Level 1.0"
L2    = "Level 2.0"
H     = 10      # L1 plate/ceiling height
L2_Z  = 11      # Level 2.0 elevation (confirmed from manifest)
H12   = 12      # garage wall height
W1    = 2.5     # L1 window sill
W2    = L2_Z + 2.5  # L2 window sill

# ── HOUSE BOUNDARY ───────────────────────────────────────────────
MX0, MY0, MX1, MY1 = 0, 0, 72, 30
GX0, GY0, GX1, GY1 = 72, 0, 100, 26

# ── ZONE DIVIDERS ────────────────────────────────────────────────
MASTER_X  = 26   # master / living split
SVC_X     = 54   # living / service split

# Master internals
MBED_Y    = 14   # master bed / bath split (y=14 wall)
MBATH_X   = 13   # master bath / his-hers split

# Living core
GROOM_Y   = 14   # great room (y=14-30) / kitchen (y=0-14)
BUTLER_X  = 48   # butler pantry west wall (x=48-54)

# Service wing
MUD_Y     = 8    # mudroom (y=0-8), laundry (y=8-18), office (y=18-30)
LAUNDRY_Y = 18
STAIR_X   = 64   # stair zone in service wing

# ── L2 ───────────────────────────────────────────────────────────
L2X0, L2Y0, L2X1, L2Y1 = 26, 0, 72, 30
L2_COR_CENTER = 15
L2_COR_S = 13
L2_COR_N = 17

# L2 north room dividers
L2_N_MED_E  = 46   # media east / bed2 west
L2_N_B2E    = 56   # bed2 east / bath2 west
L2_N_B3W    = 64   # bath2 east / bed3 west

# L2 south room dividers
L2_S_GOLF_E = 52   # golf sim east / game west
L2_S_GAME_E = 62   # game east / bed4 west

# ── LEVELS ───────────────────────────────────────────────────────
def make_level(name, elev):
    r = call("revit.create_level", {"name": name, "elevation": elev})
    print(f"  level [{name}]: {'ok' if r['Status']=='ok' else 'exists/ok'}")
    return name

print("=" * 60)
print("BUILD: Mitchell Davis Madison | a57c6cde")
print("4,500 SF | 2-story | Hill Country | Gable")
print("=" * 60)

# ── PHASE 0: LEVELS ─────────────────────────────────────────────
print("\n=== PHASE 0: LEVELS ===")
L_L1R  = make_level("L1 Roof",     H)
L_GARR = make_level("Garage Roof", H12)
L_L2R  = make_level("L2 Roof",     21)   # L2_Z(11) + H(10)

# ── PHASE 1: EXTERIOR WALLS ─────────────────────────────────────
print("\n=== PHASE 1: EXTERIOR WALLS ===")
L1w = create_rect_exterior(MX0, MY0, MX1, MY1, 0, L1, EXT, H, "L1", skip_faces=["east"])
w_l1_s = L1w["south"]; w_l1_n = L1w["north"]; w_l1_w = L1w["west"]

w_shared = create_wall(MX1, MY1, 0, MX1, MY0, 0, L1, EXT, H, "house/garage shared")
if not w_shared:
    time.sleep(2)
    w_shared = create_wall(MX1, MY1, 0, MX1, MY0, 0, L1, EXT, H, "house/garage shared (retry)")

Gw = create_garage(GX0, GY0, GX1, GY1, 0, L1, EXT, H12,
                   garage_cars=2, door_face="east", skip_faces=["west"], label="Garage")
w_gar_s = Gw["south"]; w_gar_n = Gw["north"]; w_gar_e = Gw["east"]

time.sleep(2)

L2w = create_rect_exterior(L2X0, L2Y0, L2X1, L2Y1, L2_Z, L2, EXT, H, "L2")
w_l2_s = L2w["south"]; w_l2_n = L2w["north"]
w_l2_w = L2w["west"];  w_l2_e = L2w["east"]

# ── PHASE 2: INTERIOR WALLS ─────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")

# L1 zone dividers
w_master_e  = create_wall(MASTER_X, MY0, 0, MASTER_X, MY1, 0, L1, INT, H, "master east")
w_svc_w     = create_wall(SVC_X,    MY0, 0, SVC_X,    MY1, 0, L1, INT, H, "service west")

# Master internals
w_mbed_s    = create_wall(MX0,     MBED_Y,  0, MASTER_X, MBED_Y, 0, L1, INT, H, "master bed south")
w_mbath_e   = create_wall(MBATH_X, MY0,     0, MBATH_X,  MBED_Y, 0, L1, INT, H, "mbath/closet split")

# Kitchen / great room split
w_groom_s   = create_wall(MASTER_X, GROOM_Y, 0, SVC_X, GROOM_Y, 0, L1, INT, H, "groom/kitchen split")

# Butler pantry (x=48-54, y=0-14)
w_butler_w  = create_wall(BUTLER_X, MY0, 0, BUTLER_X, GROOM_Y, 0, L1, INT, H, "butler pantry west")

# Service wing internals
w_mud_n     = create_wall(SVC_X, MUD_Y,    0, MX1, MUD_Y,    0, L1, INT, H, "mudroom north")
w_laundry_n = create_wall(SVC_X, LAUNDRY_Y,0, MX1, LAUNDRY_Y,0, L1, INT, H, "laundry north")

# Stair zone wall in service
w_stair_w   = create_wall(STAIR_X, MY0, 0, STAIR_X, LAUNDRY_Y, 0, L1, INT, H, "stair west")

# His/hers closet divider (splits x=13-26, y=0-14 into his y=7-14 and hers y=0-7)
CLOSET_Y    = 7
w_closet_div = create_wall(MBATH_X, CLOSET_Y, 0, MASTER_X, CLOSET_Y, 0, L1, INT, H, "closet his/hers divider")

# L2 corridor
corridor = create_double_loaded_corridor(L2X0, L2X1, L2_COR_CENTER, L2_Z, L2, INT, H,
                                          corridor_width=4.0, label="L2 corridor")
w_cor_s = corridor["south_wall"]
w_cor_n = corridor["north_wall"]

# L2 north room dividers
w_l2_n1 = create_wall(L2_N_MED_E, L2_COR_N, L2_Z, L2_N_MED_E, L2Y1, L2_Z, L2, INT, H, "media/bed2")
w_l2_n2 = create_wall(L2_N_B2E,   L2_COR_N, L2_Z, L2_N_B2E,   L2Y1, L2_Z, L2, INT, H, "bed2/bath2")
w_l2_n3 = create_wall(L2_N_B3W,   L2_COR_N, L2_Z, L2_N_B3W,   L2Y1, L2_Z, L2, INT, H, "bath2/bed3")

# L2 south room dividers
w_l2_s1 = create_wall(L2_S_GOLF_E, L2Y0, L2_Z, L2_S_GOLF_E, L2_COR_S, L2_Z, L2, INT, H, "golf/game")
w_l2_s2 = create_wall(L2_S_GAME_E, L2Y0, L2_Z, L2_S_GAME_E, L2_COR_S, L2_Z, L2, INT, H, "game/bed4")

# Bath 3 off corridor (south side, x=52-62)
w_bath3_n = create_wall(L2_S_GOLF_E, L2_COR_S-6, L2_Z, L2_S_GAME_E, L2_COR_S-6, L2_Z, L2, INT, H, "bath3 north")

# ── PHASE 3: FLOORS ─────────────────────────────────────────────
print("\n=== PHASE 3: FLOORS ===")
smart_floor(L1, 0,    MX0,  MY0,  MX1,  MY1)
time.sleep(3)
smart_floor(L1, 0,    GX0,  GY0,  GX1,  GY1)
time.sleep(3)
smart_floor(L2, L2_Z, L2X0, L2Y0, L2X1, L2Y1)

# ── PHASE 4: L1 DOORS ────────────────────────────────────────────
print("\n=== PHASE 4: L1 DOORS ===")

# Front entry — north wall, great room zone (double glass)
place_door(w_l1_n, None, MY1, 0,
    "Door-Exterior-Double-Full Glass-Wood_Clad", '72" x 96"',
    label="front entry", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

# Rear patio slider — south wall, great room / kitchen zone
place_door(w_l1_s, None, MY0, 0,
    "Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00",
    label="rear slider", wall_axis='x', wall_start=MASTER_X+4, wall_end=BUTLER_X-2)

# Master entry — master east wall, upper segment
place_door(w_master_e, MASTER_X, 22, 0,
    "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="master entry")

# Master bath — mbed_s wall
place_door(w_mbed_s, None, MBED_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '32" x 96"',
    label="master bath", wall_axis='x', wall_start=MBATH_X, wall_end=MASTER_X)

# His closet — mbed_s west segment
place_door(w_mbed_s, 6, MBED_Y, 0,
    "Door-Interior-Double-Sliding-2_Panel-Wood", '68" x 84"',
    label="his closet", tight=True)

# Kitchen from great room
place_door(w_groom_s, None, GROOM_Y, 0,
    "Int-Opening-Craftsman_Casing_1726", "Wide",
    label="kitchen opening", wall_axis='x', wall_start=MASTER_X, wall_end=BUTLER_X)

# Butler pantry
place_door(w_butler_w, None, MY0, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="butler pantry", wall_axis='y', wall_start=MY0, wall_end=GROOM_Y)

# Office
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
    label="office", wall_axis='y', wall_start=LAUNDRY_Y, wall_end=MY1)

# Laundry
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="laundry", wall_axis='y', wall_start=MUD_Y, wall_end=LAUNDRY_Y)

# Mudroom — service west wall
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="mudroom", wall_axis='y', wall_start=MY0, wall_end=MUD_Y, tight=True)

# Garage entry from mudroom
place_door(w_gar_n, None, GY1, 0,
    "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
    label="garage entry", wall_axis='x', wall_start=GX0, wall_end=GX1)

# ── PHASE 5: L1 WINDOWS ──────────────────────────────────────────
print("\n=== PHASE 5: L1 WINDOWS ===")
# Master west — bedroom windows
place_window(w_l1_w, MX0, 19, W1, label="master W1", **WIN["master"])
place_window(w_l1_w, MX0, 24, W1, label="master W2", **WIN["master"])
# Master bath west
place_window(w_l1_w, MX0, 5,  W1+2, label="mbath W",  **WIN["bath"])

# Great room north — feature windows flanking front entry
place_window(w_l1_n, 30, MY1, W1, label="great rm N1", **WIN["living"])
# great rm N2 at x=42 removed — consistently crashes Revit (timing conflict with front entry door)
# Master north
place_window(w_l1_n, 13, MY1, W1, label="master N",   **WIN["master"])
# Office north
place_window(w_l1_n, 60, MY1, W1, label="office N",   **WIN["accent"])

# Kitchen south — clear of slider zone
place_window(w_l1_s, 8,  MY0, W1, label="master S",   **WIN["master"])
place_window(w_l1_s, 66, MY0, W1, label="service S",  **WIN["accent"])

# ── PHASE 6: L2 DOORS ────────────────────────────────────────────
print("\n=== PHASE 6: L2 DOORS ===")
# North rooms open to corridor south wall (y=13)
place_door(w_cor_s, 36, L2_COR_S, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="media",   level=L2)
place_door(w_cor_s, 51, L2_COR_S, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="bed2",    level=L2)
place_door(w_cor_s, 60, L2_COR_S, L2_Z, "Door-Interior-Single-1_Panel-Wood", '28"',        label="bath2",   level=L2, tight=True)
place_door(w_cor_s, 68, L2_COR_S, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="bed3",    level=L2)

# South rooms open to corridor north wall (y=17), staggered 1ft in x
place_door(w_cor_n, 35, L2_COR_N, L2_Z, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="golf sim", level=L2)
place_door(w_cor_n, 57, L2_COR_N, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="game rm",  level=L2)
place_door(w_cor_n, 67, L2_COR_N, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="bed4",     level=L2)

# Bath 3 — entered from game room, door on bath3_n wall (y=7), NOT the corridor
# This removes the adjacent-door issue on the corridor wall
place_door(w_bath3_n, None, L2_COR_S-6, L2_Z, "Door-Interior-Single-1_Panel-Wood", '28"',
           label="bath3", level=L2, wall_axis='x', wall_start=L2_S_GOLF_E, wall_end=L2_S_GAME_E)

# ── PHASE 7: L2 WINDOWS ──────────────────────────────────────────
print("\n=== PHASE 7: L2 WINDOWS ===")
place_window(w_l2_n, 36, L2Y1, W2, label="media N",   **WIN["living"])
place_window(w_l2_n, 51, L2Y1, W2, label="bed2 N",    **WIN["bedroom"])
place_window(w_l2_n, 68, L2Y1, W2, label="bed3 N",    **WIN["bedroom"])
place_window(w_l2_s, 38, L2Y0, W2, label="golf S",    **WIN["living"])   # golf sim needs light
place_window(w_l2_s, 57, L2Y0, W2, label="game S",    **WIN["bedroom"])
place_window(w_l2_s, 67, L2Y0, W2, label="bed4 S",    **WIN["bedroom"])
place_window(w_l2_w, L2X0, 24,   W2, label="L2 west", **WIN["accent"])
place_window(w_l2_e, L2X1, 7,    W2, label="L2 east", **WIN["accent"])

# ── PHASE 8: STAIRS ──────────────────────────────────────────────
print("\n=== PHASE 8: STAIRS ===")
create_stairs(STAIR_X, MY0, L1, L2, width=4.0, run_length=12.0, label="Main stairs")

# ── PHASE 9: ROOFS + WALL ATTACHMENT ────────────────────────────
print("\n=== PHASE 9: ROOFS ===")
PITCH = 0.333   # 4:12 hill country gable

r_l2 = make_roof("L2 upper",  L2X0, L2Y0, L2X1, L2Y1, L_L2R,
                  pitch=PITCH, slope_style="gable", oh_w=False)  # west is interior edge, east is exterior gable
if r_l2:
    attach_walls_to_roof([w_l2_s, w_l2_n, w_l2_w, w_l2_e], r_l2)

r_l1m = make_roof("L1 master", MX0, MY0, MASTER_X, MY1, L_L1R,
                   pitch=PITCH, slope_style="gable", oh_e=False)
if r_l1m:
    attach_walls_to_roof([w_l1_w, w_l1_s, w_l1_n], r_l1m)

r_gar = make_roof("Garage",    GX0, GY0, GX1, GY1, L_GARR,
                   pitch=PITCH, slope_style="gable", oh_w=False)
if r_gar:
    attach_walls_to_roof([w_gar_s, w_gar_n, w_gar_e, w_shared], r_gar)

# ── PHASE 10: ROOMS ──────────────────────────────────────────────
print("\n=== PHASE 10: ROOM LABELS ===")
label_rooms([
    {"name": "Master Bedroom",  "x": 13, "y": 22},   # x=0-26, y=14-30
    {"name": "Master Bath",     "x": 6,  "y": 4},    # x=0-13, y=0-14 (below CLOSET_Y split)
    {"name": "His Closet",      "x": 19, "y": 11},   # x=13-26, y=7-14
    {"name": "Hers Closet",     "x": 19, "y": 3},    # x=13-26, y=0-7
    {"name": "Great Room",      "x": 40, "y": 22},
    {"name": "Kitchen",         "x": 37, "y": 7},
    {"name": "Butler Pantry",   "x": 51, "y": 7},
    {"name": "Office",          "x": 63, "y": 24},
    {"name": "Laundry",         "x": 63, "y": 13},
    {"name": "Mudroom",         "x": 63, "y": 4},
], L1, upper_limit_level="L1 Roof")  # caps rooms at 10ft so Revit computes SF

label_rooms([
    {"name": "Media Room",      "x": 36, "y": 24, "z": L2_Z},
    {"name": "Bedroom 2",       "x": 51, "y": 24, "z": L2_Z},
    {"name": "Bath 2",          "x": 60, "y": 24, "z": L2_Z},
    {"name": "Bedroom 3",       "x": 68, "y": 24, "z": L2_Z},
    {"name": "Golf Simulator",  "x": 39, "y": 6,  "z": L2_Z},
    {"name": "Game Room",       "x": 57, "y": 6,  "z": L2_Z},
    {"name": "Bedroom 4",       "x": 67, "y": 6,  "z": L2_Z},
], L2)

# ── PHASE 11: FIXTURES ────────────────────────────────────────────
print("\n=== PHASE 11: FIXTURES ===")
# All placement is WALL-RELATIVE:
#   Cabinets/appliances against a wall → center 1.25ft from wall face
#   Toilet → tank 0.5ft from wall, center 1.0ft from wall
#   Shower column → 1.5ft from each adjacent corner wall
#   Tub → 2.5ft from wall (tub is 5ft long, half = 2.5ft)
# Rotation conventions:
#   Facing NORTH (away from south wall): rotation=0
#   Facing SOUTH (away from north wall): rotation=180
#   Facing EAST  (away from west wall):  rotation=90
#   Facing WEST  (away from east wall):  rotation=270

# Kitchen — north wall run (y=GROOM_Y=14)
# Zone: x=26-48, y=0-14. Back wall = north (y=14). Counter depth 2ft, center at y=12.75
KY = GROOM_Y - 1.25   # cabinet/appliance centerline (1.25ft from north wall)
KX0, KX1 = MASTER_X, BUTLER_X   # x=26-48
KCX = (KX0 + KX1) / 2
print(f"\n── Kitchen (wall-relative, back wall y={GROOM_Y}) ──")
place_fixture("Range-Gas",          '36"',        KCX - 4,   KY,       0, L1, rotation=180, label="range")
place_fixture("Hood-Wall",           '36"',        KCX - 4,   KY + 0.3, 0, L1, rotation=180, label="hood")
place_fixture("Refrigerator",        '36" RH',     KX1 - 2.5, KY,       0, L1, rotation=180, label="fridge")
place_fixture("Dishwasher",          '24"',        KCX - 1,   KY,       0, L1, rotation=180, label="DW")
place_fixture("Sink Kitchen-Single", '30" x 21"',  KCX + 1.5, KY,       0, L1, rotation=180, label="sink")
# Base cabinets (2ft deep, center at y=12.75)
for i, bx in enumerate([KX0+1.5, KX0+3.5, KX0+5.5, KCX+4, KCX+5.5]):
    _cab("Base Cabinet-Double Door & 1 Drawer", '36"', bx, KY - 0.1, L1, rotation=180, label=f"base{i}")
_cab("Base Cabinet-Double Door Sink Unit", '36"', KCX + 1.5, KY - 0.1, L1, rotation=180, label="sink-base")
# Upper cabinets (1ft deep, center at y=13.5)
for i, bx in enumerate([KX0+1.5, KX0+4, KCX-1, KCX+4, KCX+6]):
    _cab("Upper Cabinet-Single Door-Wall", '24"', bx, GROOM_Y - 0.5, L1, rotation=180, label=f"upper{i}")
_cab("Tall Cabinet-Double Door", '36"', KX0+1.5, KY, L1, rotation=90, label="pantry")
# Island (centered in remaining south space)
ISLE_Y = (MY0 + GROOM_Y) / 2 - 1   # y≈5.5
place_fixture("Sink Kitchen-Island", '18" x 18"', KCX, ISLE_Y, 0, L1, label="island sink")
_cab("Base Cabinet-Double Door & 1 Drawer", '36"', KCX - 1.5, ISLE_Y, L1, label="island base L")
_cab("Base Cabinet-Double Door & 1 Drawer", '36"', KCX + 1.5, ISLE_Y, L1, label="island base R")

# Master bath — zone x=0-13, y=0-14
# Toilet: tank against south wall (y=0), center at y=1.0, facing north (rotation=0)
# Shower: NE corner (x=MBATH_X-1.5, y=MBED_Y-1.5), facing SW (rotation=225)
# Tub: centered on north wall (y=MBED_Y), facing south (rotation=180)
# Vanities: against east wall (x=MBATH_X), facing west (rotation=270)
print(f"\n── Master Bath (wall-relative) ──")
place_fixture("Toilet-Domestic-3D",   "Toilet-Domestic-3D",
              2.0,              1.0,              0, L1, rotation=0,   label="toilet")
place_fixture("Shower_columns_15486", "Shower_columns_15486",
              MBATH_X - 1.5,   MBED_Y - 1.5,    0, L1, rotation=180, label="shower")
place_fixture("Tub-Free Standing-3D", '30" x 60"',
              MBATH_X / 2,     MBED_Y - 2.5,    0, L1, rotation=180, label="freestanding tub")
place_fixture("Sink Vanity-Square",   '20" x 18"',
              MBATH_X - 0.75,  5.0,              0, L1, rotation=270, label="vanity L")
place_fixture("Sink Vanity-Square",   '20" x 18"',
              MBATH_X - 0.75,  8.0,              0, L1, rotation=270, label="vanity R")
_cab("Base Cabinet-Double Door Sink Unit", '36"', MBATH_X - 1.5, 5.0,  L1, rotation=270, label="vanity cab L")
_cab("Base Cabinet-Double Door Sink Unit", '36"', MBATH_X - 1.5, 8.0,  L1, rotation=270, label="vanity cab R")
_cab("Base Cabinet-3 Drawers",             '27"', MBATH_X - 1.5, 6.5,  L1, rotation=270, label="makeup drawers")

# Half bath — in mudroom zone (x=54-64, y=0-8)
# Toilet against east wall (x=STAIR_X=64), vanity against south wall (y=0)
print(f"\n── Half Bath (wall-relative) ──")
place_fixture("Toilet-Domestic-3D", "Toilet-Domestic-3D",
              STAIR_X - 1.0, 1.0, 0, L1, rotation=270, label="toilet")
place_fixture("Sink Vanity-Square", '20" x 18"',
              SVC_X + 3,     0.75, 0, L1, rotation=0,   label="sink")
_cab("Base Cabinet-Double Door Sink Unit", '24"', SVC_X + 3, 0.75, L1, rotation=0, label="vanity cab")

# Laundry — against north wall of laundry zone (x=54-64, y=8-18)
print(f"\n── Laundry (wall-relative) ──")
place_fixture("Stacked Washer and Dryer", '26"x25" - Private',
              SVC_X + 2, LAUNDRY_Y - 1.25, 0, L1, rotation=180, label="W/D stack")

# Fireplace — center of great room north wall
print(f"\n── Fireplace ──")
place_fixture("HVAC_Fireplaces_Regency-Fireplace_Gas-Stove_RC500E", "Natural Gas Stove - Black",
              (MASTER_X + SVC_X) / 2, MY1 - 1.0, 0, L1, rotation=180, label="fireplace")

# L2 Bath 2 — zone x=56-64, y=17-30 (w_l2_n at y=30, corridor wall at y=17)
# Toilet against corridor wall (y=17), shower in NE corner, vanity on west wall
print(f"\n── Bath 2 (wall-relative) ──")
B2_X0, B2_X1, B2_Y0, B2_Y1 = L2_N_B2E, L2_N_B3W, L2_COR_N, L2Y1
place_fixture("Toilet-Domestic-3D",   "Toilet-Domestic-3D",
              (B2_X0+B2_X1)/2,  B2_Y0 + 1.0,  0, L2, rotation=0,   label="toilet")
place_fixture("Shower_columns_15486", "Shower_columns_15486",
              B2_X1 - 1.5,      B2_Y1 - 1.5,  0, L2, rotation=180, label="shower")
place_fixture("Sink Vanity-Square",   '20" x 18"',
              B2_X0 + 0.75,     (B2_Y0+B2_Y1)/2, 0, L2, rotation=90, label="vanity")
_cab("Base Cabinet-Double Door Sink Unit", '30"', B2_X0 + 1.5, (B2_Y0+B2_Y1)/2, L2, rotation=90, label="vanity cab")

# L2 Bath 3 — zone x=52-62, y=7-13 (bath3_n wall at y=7, corridor wall at y=13)
print(f"\n── Bath 3 (wall-relative) ──")
B3_X0, B3_X1, B3_Y0, B3_Y1 = L2_S_GOLF_E, L2_S_GAME_E, L2_COR_S-6, L2_COR_S
place_fixture("Toilet-Domestic-3D",   "Toilet-Domestic-3D",
              (B3_X0+B3_X1)/2,  B3_Y1 - 1.0,  0, L2, rotation=180, label="toilet")
place_fixture("Shower_columns_15486", "Shower_columns_15486",
              B3_X1 - 1.5,      B3_Y0 + 1.5,  0, L2, rotation=0,   label="shower")
place_fixture("Sink Vanity-Square",   '20" x 18"',
              B3_X0 + 0.75,     (B3_Y0+B3_Y1)/2, 0, L2, rotation=90, label="vanity")
_cab("Base Cabinet-Double Door Sink Unit", '30"', B3_X0 + 1.5, (B3_Y0+B3_Y1)/2, L2, rotation=90, label="vanity cab")

print("\n✅ Build complete — Mitchell Davis Madison (a57c6cde)")
print("   4,500 SF | Hill Country Gable | 4 bed / 3.5 bath")
print("   Manual: rebuild DLL for gable pitch, add stair family")
