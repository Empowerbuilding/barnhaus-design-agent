"""
build_b8c74ce6.py
Mitchell Davis Madison — b8c74ce6
5,200 SF | Single Story | Industrial | Gable | 6 bed
Submitted: 2026-03-04

LAYOUT (north=front, south=rear):

y=60 ─────────────────────────────────────────────────── (NORTH/FRONT)
     │ Master Bed  │  Great Room       │ Bed2  │ Bed3  │
y=44 │(0-30,44-60) │  (30-64,38-60)    │(64-76)│(76-88)│
     │ MBath│Closet│  Kitchen+Eat-In   │ Bed4  │ Bed5  │
y=32 │      │ H│H  │  (30-54,20-38)    │(64-76)│(76-88)│
y=28 │      │  │   ├────────┬──────────┼───────┴───────┤
     │      │  │   │ Office │ Butler   │  Corridor      │
y=20 ├──────┴──┴───┤(30-54, │ Pantry   ├───────┬───────┤
     │ Bonus Room  │ 0-20)  │(54-64,   │ Bed6  │Laundry│
y=8  │(0-30, 0-28) │        │  0-38)   │(64-76)│(76-88)│
y=0  └─────────────┴────────┴──────────┴───────┴───────┘
     x=0  x=15 x=30  x=54   x=64      x=76   x=88
                         [Garage: (88-118, 0-26)]
"""

from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, create_garage,
    place_door, place_window,
    smart_floor, make_roof,
    create_double_loaded_corridor,
    create_room, label_rooms,
    layout_kitchen, layout_bath_standard, layout_bath_master,
    layout_laundry, place_fixture, _cab,
    attach_walls_to_roof,
    call, T, WIN
)
import time

print("=" * 60)
print("BUILD: Mitchell Davis Madison | b8c74ce6")
print("5,200 SF | Single Story | Industrial | Gable")
print("=" * 60)

# ── FOOTPRINT ─────────────────────────────────────────────────────────────────
MX0, MY0 = 0,  0
MX1, MY1 = 88, 60    # main house: 88×60 = 5,280 SF
GX0, GY0 = 88, 0
GX1, GY1 = 118, 26   # garage: 30×26, 2-car front-load east

H     = 10    # standard wall height
GAR_H = 12    # garage height
PITCH = 0.333 # 4:12 gable

# Zone dividers
MASTER_X  = 30;  SVC_X = 64;  BED_MID_X = 76
MBED_S    = 44;  MBATH_X = 15; CLOSET_Y = 37; BONUS_N = 28
KITCHEN_N = 38;  KITCHEN_S = 20; BUTLER_X = 54
BED_COR_S = 28;  BED_COR_N = 32; BED_MID_Y = 44
LAUNDRY_N = 20;  LAUNDRY_S = 8

L1     = "Level 1.0"
L_L1R  = "L1 Roof"
L_GARR = "Garage Roof"
EXT    = 'Wall 7.5" EXT PBR'
INT    = 'Wall 4.5 Interior"'

# Door/window family shortcuts
IDOOR  = "Door-Interior-Single-1_Panel-Wood"
ISLIDE = "Exterior_Sliding_Door_3843"
GOHD   = "Door-Garage-Flush_Panel"
WFAM   = "Instance-Window-Fixed"

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 0: LEVELS ===")
for name, elev in [("L1 Roof", H), ("Garage Roof", GAR_H)]:
    r = call("revit.create_level", {"name": name, "elevation": elev})
    ok = r["Status"] == "ok" or "already" in r.get("Message","").lower()
    print(f"  level [{name}]: {'exists/ok' if ok else 'ERR ' + r.get('Message','')}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 1: EXTERIOR WALLS ===")
L1w = create_rect_exterior(MX0, MY0, MX1, MY1, 0, L1, EXT, H, "L1", skip_faces=["east"])

print(f"\n── Garage ──")
Gw = create_garage(GX0, GY0, GX1, GY1, 0, L1, EXT, GAR_H, "Garage",
                   garage_load="front-load", skip_faces=["west"])

print(f"\n── Shared house/garage wall (x={GX0}, y={GY0}→{GY1}) ──")
w_shared = None
for attempt in range(3):
    r = call("revit.create_wall", {
        "start": {"x": GX0, "y": GY1, "z": 0},
        "end":   {"x": GX0, "y": GY0, "z": 0},
        "level": L1, "wall_type": EXT, "height": H, "location_line": 2
    })
    if r["Status"] == "ok":
        w_shared = r["Result"]["wall_id"]
        print(f"  wall [shared] ok {w_shared}"); break
    time.sleep(1.5)

w_l1_s  = L1w["south"]; w_l1_n = L1w["north"]; w_l1_w = L1w["west"]
w_gar_s = Gw["south"];  w_gar_n = Gw["north"];  w_gar_e = Gw["east"]

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")
w_master_e   = create_wall(MASTER_X,  MY0,       0, MASTER_X,  MY1,       0, L1, INT, H, "master east")
w_svc_w      = create_wall(SVC_X,     MY0,       0, SVC_X,     MY1,       0, L1, INT, H, "service west")
w_mbed_s     = create_wall(MX0,       MBED_S,    0, MASTER_X,  MBED_S,    0, L1, INT, H, "master bed south")
w_mbath_cls  = create_wall(MBATH_X,   BONUS_N,   0, MBATH_X,   MBED_S,    0, L1, INT, H, "mbath/closet split")
w_closet_div = create_wall(MBATH_X,   CLOSET_Y,  0, MASTER_X,  CLOSET_Y,  0, L1, INT, H, "closet his/hers divider")
w_bonus_n    = create_wall(MX0,       BONUS_N,   0, MASTER_X,  BONUS_N,   0, L1, INT, H, "bonus room north")
w_kitchen_n  = create_wall(MASTER_X,  KITCHEN_N, 0, SVC_X,     KITCHEN_N, 0, L1, INT, H, "great room south / kitchen north")
w_kitchen_s  = create_wall(MASTER_X,  KITCHEN_S, 0, BUTLER_X,  KITCHEN_S, 0, L1, INT, H, "kitchen south / office north")
w_butler_w   = create_wall(BUTLER_X,  MY0,       0, BUTLER_X,  KITCHEN_N, 0, L1, INT, H, "butler pantry west")
cor          = create_double_loaded_corridor(SVC_X, MX1, (BED_COR_S+BED_COR_N)/2, 0, L1, INT, H,
                                             corridor_width=4.0, label="bedroom corridor")
w_bed_cor_s  = cor["south_wall"]; w_bed_cor_n = cor["north_wall"]
w_bed_mid_x  = create_wall(BED_MID_X, BED_COR_S, 0, BED_MID_X, MY1,       0, L1, INT, H, "bed column divider")
w_bed_mid_y  = create_wall(SVC_X,     BED_MID_Y, 0, MX1,       BED_MID_Y, 0, L1, INT, H, "bed 2/3 south | 4/5 north")
w_laundry_n  = create_wall(BED_MID_X, LAUNDRY_N, 0, MX1,       LAUNDRY_N, 0, L1, INT, H, "laundry north")
w_laundry_s  = create_wall(BED_MID_X, LAUNDRY_S, 0, MX1,       LAUNDRY_S, 0, L1, INT, H, "laundry/mudroom divider")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 3: FLOORS ===")
smart_floor(MX0, MY0, MX1, MY1, 0, L1)
smart_floor(GX0, GY0, GX1, GY1, 0, L1)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 4: DOORS ===")
# Exterior
place_door(w_l1_n,   44,  MY1, 0, ISLIDE, '144" x 84"',   label="front entry")
place_door(w_l1_s,   44,  MY0, 0, ISLIDE, '144" x 84"',   label="rear slider")
place_door(w_gar_e,  GX1, 13,  0, GOHD,   '16\' x 8\'',   label="garage OH door",
           wall_height=GAR_H)

# Master suite
place_door(w_master_e,  MASTER_X, 52, 0, IDOOR, "36\" x 84\"", label="master entry")
place_door(w_mbed_s,    7,   MBED_S, 0, IDOOR, "36\" x 84\"",  label="master bath")
place_door(w_mbath_cls, MBATH_X, 40, 0, IDOOR, "30\" x 84\"",  label="his closet")
place_door(w_mbath_cls, MBATH_X, 31, 0, IDOOR, "30\" x 84\"",  label="hers closet")
place_door(w_bonus_n,   15,  BONUS_N, 0, IDOOR, "36\" x 84\"", label="bonus room")

# Central zone
place_door(w_butler_w,  BUTLER_X, 29, 0, IDOOR, "30\" x 84\"", label="butler pantry")
place_door(w_kitchen_s, 40, KITCHEN_S, 0, IDOOR, "36\" x 84\"",label="office")

# Bedroom wing
place_door(w_bed_cor_n, 70, BED_COR_N, 0, IDOOR, "36\" x 84\"", label="bed 4")
place_door(w_bed_cor_n, 82, BED_COR_N, 0, IDOOR, "36\" x 84\"", label="bed 5")
place_door(w_bed_mid_y, 70, BED_MID_Y, 0, IDOOR, "36\" x 84\"", label="bed 2")
place_door(w_bed_mid_y, 82, BED_MID_Y, 0, IDOOR, "36\" x 84\"", label="bed 3")
place_door(w_bed_cor_s, 70, BED_COR_S, 0, IDOOR, "36\" x 84\"", label="bed 6")
place_door(w_laundry_n, 82, LAUNDRY_N, 0, IDOOR, "30\" x 84\"", label="laundry")
place_door(w_svc_w,     SVC_X, 4, 0,   IDOOR, "30\" x 84\"",    label="mudroom")
place_door(w_shared,    GX0,   4, 0,   IDOOR, "36\" x 84\"",    label="garage interior")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 5: WINDOWS ===")
# Industrial — large fixed windows

# North wall
place_window(w_l1_n, 15,  MY1, 2.5, WFAM, '48" x 96"', label="master N")
place_window(w_l1_n, 44,  MY1, 2.5, WFAM, '72" x 36"', label="great rm N1")
place_window(w_l1_n, 53,  MY1, 2.5, WFAM, '72" x 36"', label="great rm N2")
place_window(w_l1_n, 70,  MY1, 2.5, WFAM, '48" x 96"', label="bed2 N")
place_window(w_l1_n, 82,  MY1, 2.5, WFAM, '48" x 96"', label="bed3 N")

# South wall
place_window(w_l1_s, 15,  MY0, 2.5, WFAM, '48" x 96"', label="bonus S")
place_window(w_l1_s, 42,  MY0, 4.0, WFAM, '60" x 24"', label="office S")
place_window(w_l1_s, 70,  MY0, 2.5, WFAM, '48" x 96"', label="bed6 S")

# West wall
place_window(w_l1_w, MX0, 52,  2.5, WFAM, '48" x 96"', label="master W1")
place_window(w_l1_w, MX0, 14,  4.0, WFAM, '60" x 24"', label="bonus W")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 6: ROOFS ===")
# Main house gable — ridge runs E-W, east=interior (no overhang), west=exterior gable
r_main = make_roof("Main house", MX0, MY0, MX1, MY1, L_L1R,
                   pitch=PITCH, slope_style="gable", oh_e=False)
if r_main:
    attach_walls_to_roof([w_l1_w, w_l1_s, w_l1_n], r_main)

# Garage gable — west=interior (no overhang), east=exterior gable
r_gar  = make_roof("Garage", GX0, GY0, GX1, GY1, L_GARR,
                   pitch=PITCH, slope_style="gable", oh_w=False)
if r_gar:
    attach_walls_to_roof([w_gar_s, w_gar_n, w_gar_e, w_shared], r_gar)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 7: ROOM LABELS ===")
label_rooms([
    {"name": "Master Bedroom", "x": 15, "y": 52},
    {"name": "Master Bath",    "x": 7,  "y": 36},
    {"name": "His Closet",     "x": 22, "y": 40},
    {"name": "Hers Closet",    "x": 22, "y": 32},
    {"name": "Bonus Room",     "x": 15, "y": 14},
    {"name": "Great Room",     "x": 47, "y": 50},
    {"name": "Kitchen",        "x": 40, "y": 29},
    {"name": "Butler Pantry",  "x": 59, "y": 19},
    {"name": "Office",         "x": 42, "y": 10},
    {"name": "Bedroom 2",      "x": 70, "y": 52},
    {"name": "Bedroom 3",      "x": 82, "y": 52},
    {"name": "Bedroom 4",      "x": 70, "y": 38},
    {"name": "Bedroom 5",      "x": 82, "y": 38},
    {"name": "Bedroom 6",      "x": 70, "y": 14},
    {"name": "Laundry",        "x": 82, "y": 14},
    {"name": "Mudroom",        "x": 82, "y": 4},
], L1, upper_limit_level="L1 Roof")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 8: FIXTURES ===")

# Kitchen — L-shape, back wall north (y=38), with island
layout_kitchen(MASTER_X, KITCHEN_S, BUTLER_X, KITCHEN_N, 0, L1,
               back_wall="north", has_island=True,
               kitchen_layout="l-shape", label="Kitchen")

# Master bath — zone x=0-15, y=28-44
layout_bath_master(MX0, BONUS_N, MBATH_X, MBED_S, 0, L1, label="Master Bath")

# Shared bath for Bed 2/3 — NE corner, zone x=76-88, y=44-60
layout_bath_standard(BED_MID_X, BED_MID_Y, MX1, MY1, 0, L1, label="Bath 2/3")

# Laundry
layout_laundry(BED_MID_X + 2, (LAUNDRY_S + LAUNDRY_N) / 2, 0, L1, label="Laundry")

print(f"\n✅ Build complete — Mitchell Davis Madison (b8c74ce6)")
print(f"   5,200 SF | Single Story | Industrial | Gable | 6 bed")
print(f"   Notes: Bed 4/5 bath manual | Bed 6 bath manual")
