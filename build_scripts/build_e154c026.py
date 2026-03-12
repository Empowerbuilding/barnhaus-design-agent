"""
build_e154c026.py
Mitchell Davis Madison — e154c026
2,800 SF | Two Story | Modern Desert | L-Shape
Main: Single-Slope | Garage: Flat
4 bed | U-shape kitchen + butler pantry | Open plan | His/Hers closets

L-SHAPE LAYOUT:
  Main body (2 stories): (0,0)→(50,36) = 1,800 SF/floor
  Garage wing (1 story): (50,0)→(72,22) = 484 SF

LEVEL 1 LAYOUT (north=front/entry):
y=36 ──────────────────────────────────── (NORTH/FRONT)
     │  Master Bed   │   Great Room       │
     │ (0-22, 14-36) │   (22-50, 0-36)   │
y=14 ├───────────────┤   Kitchen NE corner│
     │ Master Bath   │   Butler Pantry SE │
     │ (0-14, 0-14)  │   (44-50, 0-18)   │
y=7  │ His  │ Hers   │                   │
     │Closet│Closet  │                   │
y=0  └───────────────┴────────────────────┘
     x=0  x=14 x=22  x=44 x=50

LEVEL 2 LAYOUT (same footprint, z=11):
y=36 ────────────────────────────────────
     │   Bed 2       │     Bed 4          │
     │ (0-24, 22-36) │  (24-50, 16-36)   │
y=22 ├───────────────┤                   │
     │   Bed 3       ├───────────────────┤
     │ (0-24, 8-22)  │     Landing       │
y=8  ├───────────────┤  (24-50, 0-16)   │
     │  Bath L2      │                   │
     │ (0-24, 0-8)   │                   │
y=0  └───────────────┴───────────────────┘
     x=0           x=24               x=50

GARAGE (1 story, flat roof at z=12):
(50,0)→(72,22) — 2-car front load
"""

from barnhaus_revit_utils import (
    create_wall, create_rect_exterior,
    place_door, place_window,
    smart_floor, make_roof,
    create_room, label_rooms,
    layout_kitchen, layout_bath_standard, layout_bath_master,
    layout_laundry, place_fixture,
    attach_walls_to_roof,
    call, T, WIN
)
from barnhaus_revit_utils import verify_wall_facing
import time

print("=" * 60)
print("BUILD: Mitchell Davis Madison | e154c026")
print("2,800 SF | Two Story | Modern Desert | L-Shape")
print("Main: Single-Slope | Garage: Flat")
print("=" * 60)

# ── FOOTPRINT ─────────────────────────────────────────────
MX0, MY0 = 0,  0
MX1, MY1 = 50, 36

GX0, GY0 = 50, 0
GX1, GY1 = 72, 22

# ── HEIGHTS & LEVELS ──────────────────────────────────────
H1     = 11    # L1 wall height (floor-to-floor: Level 1.0 → Level 2.0)
H2     = 10    # L2 wall height (floor-to-roof)
GAR_H  = 12    # garage wall height
PITCH  = 0.25  # single-slope pitch

L1     = "Level 1.0"
L2     = "Level 2.0"
L_L1R  = "L1 Roof"      # z=10 (for L1 wall attachment reference)
L_L2R  = "L2 Roof"      # z=21
L_GARR = "Garage Roof"  # z=12

EXT   = 'Wall 7.5" EXT PBR'
INT   = 'Wall 4.5 Interior"'
IDOOR = "Door-Interior-Single-1_Panel-Wood"
ISLIDE= "Exterior_Sliding_Door_3843"
GOHD  = "Door-Garage-Flush_Panel"
WFAM  = "Instance-Window-Fixed"

# L1 zone dividers
MASTER_X  = 22
MBED_S    = 14
MBATH_E   = 14
CLOSET_DIV= 7
BUTLER_W  = 44
BUTLER_N  = 18

# L2 zone dividers
L2_DIV_X  = 24
L2_BED2_S = 22
L2_BED3_S = 8
L2_BED4_S = 16

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 0: LEVELS ===")
for name, elev in [("Level 2.0", 11), ("L1 Roof", 10), ("L2 Roof", 21), ("Garage Roof", 12)]:
    r = call("revit.create_level", {"name": name, "elevation": elev})
    ok = r["Status"] == "ok" or "already" in r.get("Message","").lower() or "unique" in r.get("Message","").lower()
    print(f"  level [{name}]: {'ok' if ok else 'ERR ' + r.get('Message','')}")

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 1: EXTERIOR WALLS ===")

# L1 main body — all 4 sides, height=H1 (reaches Level 2.0 floor)
print("\n── L1 Main body ──")
w1_n = create_wall(MX0, MY1, 0, MX1, MY1, 0, L1, EXT, H1, "L1 north")
verify_wall_facing(w1_n, 0, +1, "L1 north")
w1_w = create_wall(MX0, MY0, 0, MX0, MY1, 0, L1, EXT, H1, "L1 west")
verify_wall_facing(w1_w, -1, 0, "L1 west")
w1_e = create_wall(MX1, MY1, 0, MX1, MY0, 0, L1, EXT, H1, "L1 east")
verify_wall_facing(w1_e, +1, 0, "L1 east")
w1_s = create_wall(MX1, MY0, 0, MX0, MY0, 0, L1, EXT, H1, "L1 south")
verify_wall_facing(w1_s, 0, -1, "L1 south")

# Garage — 1 story
print("\n── Garage ──")
w_gn = create_wall(GX0, GY1, 0, GX1, GY1, 0, L1, EXT, GAR_H, "garage north")
verify_wall_facing(w_gn, 0, +1, "garage north")
w_ge = create_wall(GX1, GY1, 0, GX1, GY0, 0, L1, EXT, GAR_H, "garage east")
verify_wall_facing(w_ge, +1, 0, "garage east")
w_gs = create_wall(GX1, GY0, 0, GX0, GY0, 0, L1, EXT, GAR_H, "garage south")
verify_wall_facing(w_gs, 0, -1, "garage south")

# Shared wall between main body and garage
w_shared = None
for attempt in range(3):
    r = call("revit.create_wall", {
        "start": {"x": GX0, "y": GY1, "z": 0},
        "end":   {"x": GX0, "y": GY0, "z": 0},
        "level": L1, "wall_type": EXT, "height": GAR_H, "location_line": 2
    })
    if r["Status"] == "ok":
        w_shared = r["Result"]["wall_id"]
        print(f"  wall [shared house/garage]: ok {w_shared}")
        break
    time.sleep(1.5)

# L2 main body exterior — same footprint, sits at Level 2.0
print("\n── L2 Main body ──")
w2_n = create_wall(MX0, MY1, 11, MX1, MY1, 11, L2, EXT, H2, "L2 north")
verify_wall_facing(w2_n, 0, +1, "L2 north")
w2_w = create_wall(MX0, MY0, 11, MX0, MY1, 11, L2, EXT, H2, "L2 west")
verify_wall_facing(w2_w, -1, 0, "L2 west")
w2_e = create_wall(MX1, MY1, 11, MX1, MY0, 11, L2, EXT, H2, "L2 east")
verify_wall_facing(w2_e, +1, 0, "L2 east")
w2_s = create_wall(MX1, MY0, 11, MX0, MY0, 11, L2, EXT, H2, "L2 south")
verify_wall_facing(w2_s, 0, -1, "L2 south")

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")

# L1 interior
print("\n── L1 interior ──")
w_master_e   = create_wall(MASTER_X,  MY0, 0, MASTER_X,  MY1, 0, L1, INT, H1, "master east")
w_mbed_s     = create_wall(MX0,       MBED_S, 0, MASTER_X, MBED_S, 0, L1, INT, H1, "master bed south")
w_mbath_e    = create_wall(MBATH_E,   MY0, 0, MBATH_E,   MBED_S, 0, L1, INT, H1, "master bath east")
w_closet_div = create_wall(MBATH_E,   CLOSET_DIV, 0, MASTER_X, CLOSET_DIV, 0, L1, INT, H1, "his/hers closet div")
w_butler_w   = create_wall(BUTLER_W,  MY0, 0, BUTLER_W,  BUTLER_N, 0, L1, INT, H1, "butler pantry west")
w_butler_n   = create_wall(BUTLER_W,  BUTLER_N, 0, MX1, BUTLER_N, 0, L1, INT, H1, "butler pantry north")

# L2 interior
print("\n── L2 interior ──")
w_l2_divx  = create_wall(L2_DIV_X, MY0, 11, L2_DIV_X, MY1, 11, L2, INT, H2, "L2 divider x")
w_l2_bed2s = create_wall(MX0, L2_BED2_S, 11, L2_DIV_X, L2_BED2_S, 11, L2, INT, H2, "L2 bed2 south")
w_l2_bed3s = create_wall(MX0, L2_BED3_S, 11, L2_DIV_X, L2_BED3_S, 11, L2, INT, H2, "L2 bath south")
w_l2_bed4s = create_wall(L2_DIV_X, L2_BED4_S, 11, MX1, L2_BED4_S, 11, L2, INT, H2, "L2 bed4 south")

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 3: FLOORS ===")
smart_floor(L1, 0,  MX0, MY0, MX1, MY1)
smart_floor(L1, 0,  GX0, GY0, GX1, GY1)
smart_floor(L2, 11, MX0, MY0, MX1, MY1)

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 4: DOORS ===")
# Exterior entry
place_door(w1_n, 11, MY1, 0, ISLIDE, '6\'-0"W. x 8\'-0"H."', label="front entry")
place_door(w1_s, 25, MY0, 0, ISLIDE, '6\'-0"W. x 8\'-0"H."', label="rear patio")
place_door(w_ge, GX1, 11, 0, GOHD, "16W X 10H", label="garage OH")

# L1 master suite
place_door(w_master_e,   MASTER_X, 26, 0, IDOOR, '36" x 96"', label="master entry")
place_door(w_mbed_s,     7,  MBED_S, 0, IDOOR, '36" x 96"', label="master bath")
place_door(w_mbath_e,    MBATH_E, 10, 0, IDOOR, '30" x 96"', label="his closet")
place_door(w_mbath_e,    MBATH_E, 3,  0, IDOOR, '30" x 96"', label="hers closet")
place_door(w_butler_w,   BUTLER_W, 9, 0, IDOOR, '30" x 96"', label="butler pantry")
if w_shared:
    place_door(w_shared, GX0, 11, 0, IDOOR, '36" x 96"', label="garage interior")

# L2 doors — all on interior walls opening to landing
place_door(w_l2_divx,  L2_DIV_X, 29, 11, IDOOR, '36" x 96"', label="L2 bed2")
place_door(w_l2_divx,  L2_DIV_X, 15, 11, IDOOR, '36" x 96"', label="L2 bed3")
place_door(w_l2_divx,  L2_DIV_X, 4,  11, IDOOR, '30" x 96"', label="L2 bath")
place_door(w_l2_bed4s, 37, L2_BED4_S, 11, IDOOR, '36" x 96"', label="L2 bed4")

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 5: WINDOWS ===")
# Modern desert — large horizontal windows, generous glazing
place_window(w1_n, 11, MY1, 2.5, WFAM, '72" x 36"', label="master N")
place_window(w1_n, 33, MY1, 2.5, WFAM, '72" x 36"', label="great room N1")
place_window(w1_n, 43, MY1, 2.5, WFAM, '72" x 36"', label="great room N2")
place_window(w1_w, MX0, 25, 2.5, WFAM, '48" x 96"', label="master W")
place_window(w1_s, 11, MY0, 2.5, WFAM, '72" x 36"', label="great room S1")
place_window(w1_s, 33, MY0, 2.5, WFAM, '72" x 36"', label="great room S2")
place_window(w1_e, MX1, 18, 2.5, WFAM, '48" x 48"', label="kitchen E")

# L2 windows
place_window(w2_n, 12, MY1, 13.5, WFAM, '48" x 48"', label="L2 bed2 N")
place_window(w2_n, 37, MY1, 13.5, WFAM, '48" x 48"', label="L2 bed4 N")
place_window(w2_w, MX0, 29, 13.5, WFAM, '48" x 48"', label="L2 bed2 W")
place_window(w2_w, MX0, 15, 13.5, WFAM, '48" x 48"', label="L2 bed3 W")
place_window(w2_s, 37, MY0, 13.5, WFAM, '48" x 48"', label="L2 bed4 S")

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 6: ROOFS ===")
# Main house — single-slope (shed), low edge south
r_main = make_roof("Main house", MX0, MY0, MX1, MY1, L_L2R,
                   pitch=PITCH, slope_style="shed", shed_low_edge=0)
if r_main:
    attach_walls_to_roof([w2_n, w2_w, w2_e, w2_s], r_main)

# Garage — flat roof
r_gar = make_roof("Garage", GX0, GY0, GX1, GY1, L_GARR,
                  pitch=0.01, slope_style="flat")

# ─────────────────────────────────────────────────────────
print("\n=== PHASE 7: ROOM LABELS ===")

print("\n── L1 Rooms ──")
label_rooms([
    {"name": "Master Bedroom",  "x": 11, "y": 25},
    {"name": "Master Bath",     "x": 7,  "y": 7},
    {"name": "His Closet",      "x": 18, "y": 11},
    {"name": "Hers Closet",     "x": 18, "y": 3},
    {"name": "Great Room",      "x": 33, "y": 28},
    {"name": "Kitchen",         "x": 33, "y": 9},
    {"name": "Butler Pantry",   "x": 47, "y": 9},
    {"name": "Garage",          "x": 61, "y": 11},
], L1, upper_limit_level="L1 Roof")

print("\n── L2 Rooms ──")
label_rooms([
    {"name": "Bedroom 2",  "x": 12, "y": 29, "z": 11},
    {"name": "Bedroom 3",  "x": 12, "y": 15, "z": 11},
    {"name": "Bath L2",    "x": 12, "y": 4,  "z": 11},
    {"name": "Bedroom 4",  "x": 37, "y": 26, "z": 11},
    {"name": "Landing",    "x": 37, "y": 8,  "z": 11},
], L2, upper_limit_level="L2 Roof")

print("\n=== PHASE 8: FIXTURES ===")
# Master bath — walk-in shower + makeup vanity (no freestanding tub)
layout_bath_master(MX0, MY0, MBATH_E, MBED_S, 0, L1, label="Master Bath")

# Kitchen U-shape (NE corner of great room: x=22-50, y=0-36)
layout_kitchen(MASTER_X, MY0, MX1, MY1, 0, L1,
               back_wall="north", has_island=False,
               kitchen_layout="u-shape", label="Kitchen")

print(f"\n✅ Build complete — Mitchell Davis Madison (e154c026)")
print(f"   2,800 SF | L-Shape | Modern Desert | Single-Slope | 4 bed")
