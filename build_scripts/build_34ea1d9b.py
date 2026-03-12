"""
build_34ea1d9b.py
Mitchell Davis Madison — 34ea1d9b
5,200 SF | Single Story | Hill Country | T-Shape
Main: Gable | Garage: Single-Slope
6 bed | L-shape kitchen + island | Single corridor | His/Hers closets

T-SHAPE LAYOUT (north=front/entry):

y=60 ──────────────────────────────────────────── (NORTH/FRONT)
     │ Master Bed  │  Great Room    │ Bed2  │ Bed3 │
y=44 │(0-28,44-60) │  (28-62,38-60) │(62-76)│(76-88│
     │ Bath │Closet│  Kitchen+Eat-In│ Bed4  │ Bed5 │
y=32 │      │ H│H  │  (28-54,20-38) │(62-76)│(76-88│
y=28 ├──────┴──┴───┼─────┬──────────┤  Single Corr. │
     │             │Offic│ Butler   │  (62-88,28-32)│
y=20 │ Bonus Room  │     │ Pantry   ├───────────────┤
     │ (0-28,0-20) │(28- │(54-62,   │ Bed6  │Laundr│
y=8  │             │ 54, │  0-38)   │(62-76)│(76-88│
y=0  └─────────────┴─────┴──────────┴───────┴──────┘
     x=0  x=15 x=28  x=54 x=62      x=76   x=88

REAR WING (T crossbar projects south from main body center):
     y=-20 to y=0, x=20-68 = 48×20 = 960 SF rear wing

     y=0  ┌──────────────────────────────┐
          │     Rear Wing / Covered      │
          │  Patio / Flex Space          │
          │  (20,−20)→(68,0)             │
     y=-20 └──────────────────────────────┘
           x=20                       x=68

Garage: (88,0)→(118,24), single-slope roof
"""

from barnhaus_revit_utils import (
    create_wall, create_rect_exterior,
    place_door, place_window,
    smart_floor, make_roof,
    create_double_loaded_corridor, create_hallway,
    create_room, label_rooms,
    layout_kitchen, layout_bath_standard, layout_bath_master,
    layout_laundry, place_fixture, _cab,
    attach_walls_to_roof,
    call, T, WIN
)
import time

print("=" * 60)
print("BUILD: Mitchell Davis Madison | 34ea1d9b")
print("5,200 SF | Single Story | Hill Country | T-Shape")
print("Main: Gable | Garage: Single-Slope")
print("=" * 60)

# ── FOOTPRINT ─────────────────────────────────────────────────────────────────
# Main body (horizontal bar of T)
MX0, MY0 = 0,  0
MX1, MY1 = 88, 60

# Rear wing (vertical stem of T, projects south)
WX0, WY0 = 20, -20
WX1, WY1 = 68,  0    # connects flush to main body south wall

# Garage
GX0, GY0 = 88, 0
GX1, GY1 = 118, 24   # 30×24 = 720 SF, 2-car

H     = 10
GAR_H = 10
PITCH = 0.333

# Zone dividers — main body
MASTER_X  = 28;  SVC_X = 62;  BED_MID_X = 76
MBED_S    = 44;  MBATH_X = 14; CLOSET_Y = 37; BONUS_N = 20
KITCHEN_N = 38;  KITCHEN_S = 20; BUTLER_X = 54
COR_S     = 28;  COR_N = 32;  BED_MID_Y = 44
LAUNDRY_N = 20;  LAUNDRY_S = 8

L1     = "Level 1.0"
L_L1R  = "L1 Roof"
L_GARR = "Garage Roof"
EXT    = 'Wall 7.5" EXT PBR'
INT    = 'Wall 4.5 Interior"'
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

# Main body — skip south face between x=WX0 and x=WX1 (rear wing connects there)
# Strategy: draw south wall in two segments (west gap + east gap), skip middle
print("\n── Main body ──")
# North, west, east full walls
w_n  = create_wall(MX0, MY1, 0, MX1, MY1, 0, L1, EXT, H, "main north")
from barnhaus_revit_utils import verify_wall_facing
verify_wall_facing(w_n, 0, +1, "main north")

w_w  = create_wall(MX0, MY0, 0, MX0, MY1, 0, L1, EXT, H, "main west")
verify_wall_facing(w_w, -1, 0, "main west")

w_e_main = create_wall(MX1, MY1, 0, MX1, MY0, 0, L1, EXT, H, "main east")
verify_wall_facing(w_e_main, +1, 0, "main east")

# South wall — two segments flanking the wing opening
w_s_west = create_wall(WX0, MY0, 0, MX0, MY0, 0, L1, EXT, H, "main south west")
verify_wall_facing(w_s_west, 0, -1, "main south west")

w_s_east = create_wall(MX1, MY0, 0, WX1, MY0, 0, L1, EXT, H, "main south east")
verify_wall_facing(w_s_east, 0, -1, "main south east")

# Rear wing walls (3 sides — north face is the opening into main body)
print("\n── Rear wing ──")
w_wing_s = create_wall(WX1, WY0, 0, WX0, WY0, 0, L1, EXT, H, "wing south")
verify_wall_facing(w_wing_s, 0, -1, "wing south")

w_wing_w = create_wall(WX0, WY0, 0, WX0, WY1, 0, L1, EXT, H, "wing west")
verify_wall_facing(w_wing_w, -1, 0, "wing west")

w_wing_e = create_wall(WX1, WY1, 0, WX1, WY0, 0, L1, EXT, H, "wing east")
verify_wall_facing(w_wing_e, +1, 0, "wing east")

# Garage
print("\n── Garage ──")
w_gs = create_wall(GX1, GY0, 0, GX0, GY0, 0, L1, EXT, GAR_H, "garage south")
verify_wall_facing(w_gs, 0, -1, "garage south")
w_gn = create_wall(GX0, GY1, 0, GX1, GY1, 0, L1, EXT, GAR_H, "garage north")
verify_wall_facing(w_gn, 0, +1, "garage north")
w_ge = create_wall(GX1, GY1, 0, GX1, GY0, 0, L1, EXT, GAR_H, "garage east")
verify_wall_facing(w_ge, +1, 0, "garage east")

# Shared house/garage wall
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

# Garage door
r = call("revit.place_door", {
    "wall_id": w_ge,
    "location": {"x": GX1, "y": (GY0+GY1)/2, "z": 0},
    "family_name": GOHD, "type_name": "16' x 8'"
})
print(f"  door [garage OH]: {'ok' if r['Status']=='ok' else 'ERR ' + r.get('Message','')}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")
w_master_e   = create_wall(MASTER_X,  MY0,       0, MASTER_X,  MY1,       0, L1, INT, H, "master east")
w_svc_w      = create_wall(SVC_X,     MY0,       0, SVC_X,     MY1,       0, L1, INT, H, "service west")
w_mbed_s     = create_wall(MX0,       MBED_S,    0, MASTER_X,  MBED_S,    0, L1, INT, H, "master bed south")
w_mbath_cls  = create_wall(MBATH_X,   BONUS_N,   0, MBATH_X,   MBED_S,    0, L1, INT, H, "mbath/closet split")
w_closet_div = create_wall(MBATH_X,   CLOSET_Y,  0, MASTER_X,  CLOSET_Y,  0, L1, INT, H, "his/hers divider")
w_bonus_n    = create_wall(MX0,       BONUS_N,   0, MASTER_X,  BONUS_N,   0, L1, INT, H, "bonus north")
w_kitchen_n  = create_wall(MASTER_X,  KITCHEN_N, 0, SVC_X,     KITCHEN_N, 0, L1, INT, H, "kitchen north / great room south")
w_kitchen_s  = create_wall(MASTER_X,  KITCHEN_S, 0, BUTLER_X,  KITCHEN_S, 0, L1, INT, H, "kitchen south / office north")
w_butler_w   = create_wall(BUTLER_X,  MY0,       0, BUTLER_X,  KITCHEN_N, 0, L1, INT, H, "butler pantry west")

# Single corridor in bedroom wing (single wall, rooms on one side)
w_corridor   = create_wall(SVC_X,     COR_S,     0, MX1,       COR_S,     0, L1, INT, H, "bedroom corridor")
w_bed_mid_x  = create_wall(BED_MID_X, COR_S,     0, BED_MID_X, MY1,       0, L1, INT, H, "bed column divider")
w_bed_mid_y  = create_wall(SVC_X,     BED_MID_Y, 0, MX1,       BED_MID_Y, 0, L1, INT, H, "bed 2/3 south | 4/5 north")
w_laundry_n  = create_wall(BED_MID_X, LAUNDRY_N, 0, MX1,       LAUNDRY_N, 0, L1, INT, H, "laundry north")
w_laundry_s  = create_wall(BED_MID_X, LAUNDRY_S, 0, MX1,       LAUNDRY_S, 0, L1, INT, H, "laundry/mudroom divider")

# Rear wing interior (open flex/patio — no interior walls needed)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 3: FLOORS ===")
smart_floor(L1, 0, MX0, MY0, MX1, MY1)
smart_floor(L1, 0, WX0, WY0, WX1, WY1)
smart_floor(L1, 0, GX0, GY0, GX1, GY1)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 4: DOORS ===")
place_door(w_n,       44,  MY1, 0, ISLIDE, '8\'-0"W. x 8\'-0"H. 2',   label="front entry")
place_door(w_wing_s,  44,  WY0, 0, ISLIDE, '8\'-0"W. x 8\'-0"H. 2',   label="rear wing exit")
place_door(w_ge,      GX1, 12,  0, GOHD,   "16W X 10H",                label="garage OH door")

# Master suite
place_door(w_master_e,  MASTER_X, 52, 0, IDOOR, '36" x 96"', label="master entry")
place_door(w_mbed_s,    7,  MBED_S,  0, IDOOR, '36" x 96"',  label="master bath")
place_door(w_mbath_cls, MBATH_X, 40, 0, IDOOR, '30" x 96"',  label="his closet")
place_door(w_mbath_cls, MBATH_X, 32, 0, IDOOR, '30" x 96"',  label="hers closet")
place_door(w_bonus_n,   14,  BONUS_N, 0, IDOOR, '36" x 96"', label="bonus room")

# Central
place_door(w_butler_w,  BUTLER_X, 29, 0, IDOOR, '30" x 96"', label="butler pantry")
place_door(w_kitchen_s, 40, KITCHEN_S, 0, IDOOR, '36" x 96"',label="office")

# Bedroom wing — single corridor, all doors on corridor wall
place_door(w_corridor, 68, COR_S, 0, IDOOR, '36" x 96"', label="bed 4")
place_door(w_corridor, 80, COR_S, 0, IDOOR, '36" x 96"', label="bed 5")
place_door(w_bed_mid_y, 68, BED_MID_Y, 0, IDOOR, '36" x 96"', label="bed 2")
place_door(w_bed_mid_y, 80, BED_MID_Y, 0, IDOOR, '36" x 96"', label="bed 3")
place_door(w_svc_w, SVC_X, 14, 0, IDOOR, '36" x 96"',    label="bed 6")
place_door(w_laundry_n, 80, LAUNDRY_N, 0, IDOOR, '30" x 96"', label="laundry")
place_door(w_svc_w, SVC_X, 4,  0, IDOOR, '30" x 96"',    label="mudroom")
if w_shared:
    place_door(w_shared, GX0, 4, 0, IDOOR, '36" x 96"',   label="garage interior")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 5: WINDOWS ===")
# Hill Country — mixed sizes, strong north/south exposure
place_window(w_n,      15,  MY1, 2.5, WFAM, '48" x 96"', label="master N")
place_window(w_n,      44,  MY1, 2.5, WFAM, '72" x 36"', label="great rm N1")
place_window(w_n,      53,  MY1, 2.5, WFAM, '72" x 36"', label="great rm N2")
place_window(w_n,      68,  MY1, 2.5, WFAM, '48" x 96"', label="bed2 N")
place_window(w_n,      80,  MY1, 2.5, WFAM, '48" x 96"', label="bed3 N")

place_window(w_wing_s, 30,  WY0, 2.5, WFAM, '72" x 36"', label="wing S1")
place_window(w_wing_s, 50,  WY0, 2.5, WFAM, '72" x 36"', label="wing S2")
place_window(w_wing_w, WX0, -10, 2.5, WFAM, '48" x 48"', label="wing W")
place_window(w_wing_e, WX1, -10, 2.5, WFAM, '48" x 48"', label="wing E")

place_window(w_w,      MX0, 52,  2.5, WFAM, '48" x 96"', label="master W")
place_window(w_w,      MX0, 10,  4.0, WFAM, '60" x 24"', label="bonus W")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 6: ROOFS ===")
# Main house gable — east flush (shared garage), west exterior gable
r_main = make_roof("Main house", MX0, MY0, MX1, MY1, L_L1R,
                   pitch=PITCH, slope_style="gable", oh_e=False)
if r_main:
    attach_walls_to_roof([w_w, w_n, w_e_main], r_main)

# Rear wing gable (separate gable perpendicular to main)
r_wing = make_roof("Rear wing", WX0, WY0, WX1, WY1, L_L1R,
                   pitch=PITCH, slope_style="gable", oh_n=False)
if r_wing:
    attach_walls_to_roof([w_wing_w, w_wing_s, w_wing_e], r_wing)

# Garage single-slope — slopes front to back (south low, north high)
r_gar = make_roof("Garage", GX0, GY0, GX1, GY1, L_GARR,
                  pitch=PITCH, slope_style="shed", shed_low_edge=0, oh_w=False)
if r_gar:
    attach_walls_to_roof([w_gs, w_ge, w_shared], r_gar)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 7: ROOM LABELS ===")
label_rooms([
    {"name": "Master Bedroom", "x": 14, "y": 52},
    {"name": "Master Bath",    "x": 7,  "y": 36},
    {"name": "His Closet",     "x": 21, "y": 40},
    {"name": "Hers Closet",    "x": 21, "y": 32},
    {"name": "Bonus Room",     "x": 14, "y": 10},
    {"name": "Great Room",     "x": 44, "y": 50},
    {"name": "Kitchen",        "x": 38, "y": 29},
    {"name": "Butler Pantry",  "x": 58, "y": 19},
    {"name": "Office",         "x": 40, "y": 10},
    {"name": "Rear Wing",      "x": 44, "y": -10},
    {"name": "Bedroom 2",      "x": 68, "y": 52},
    {"name": "Bedroom 3",      "x": 80, "y": 52},
    {"name": "Bedroom 4",      "x": 68, "y": 38},
    {"name": "Bedroom 5",      "x": 80, "y": 38},
    {"name": "Bedroom 6",      "x": 68, "y": 14},
    {"name": "Laundry",        "x": 80, "y": 14},
    {"name": "Mudroom",        "x": 80, "y": 4},
], L1, upper_limit_level="L1 Roof")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== PHASE 8: FIXTURES ===")
# Kitchen L-shape, back wall north (y=38), with island
layout_kitchen(MASTER_X, KITCHEN_S, BUTLER_X, KITCHEN_N, 0, L1,
               back_wall="north", has_island=True,
               kitchen_layout="l-shape", label="Kitchen")

# Master bath — x=0-14, y=20-44
layout_bath_master(MX0, BONUS_N, MBATH_X, MBED_S, 0, L1, label="Master Bath")

# Shared bath for Bed 2/3
layout_bath_standard(BED_MID_X, BED_MID_Y, MX1, MY1, 0, L1, label="Bath 2/3")

# Laundry
layout_laundry(BED_MID_X + 2, (LAUNDRY_S + LAUNDRY_N) / 2, 0, L1, label="Laundry")

print(f"\n✅ Build complete — Mitchell Davis Madison (34ea1d9b)")
print(f"   5,200 SF | T-Shape | Hill Country | Gable+Shed | 6 bed")
print(f"   Rear wing = covered patio / flex space")
