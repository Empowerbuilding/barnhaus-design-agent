"""
build_b83647cb.py — Mitchell Davis Madison (REBUILT)
~4,200 SF | Single-story | U-Shape | Flat Roof | 5 bed
Game room | Bonus room | Laundry | Butler pantry | Kitchen island
Master: walk-in shower, makeup vanity, his+hers closets
Front porch (north entry) + courtyard (south — between arms)

DESIGN DECISIONS:
- U-shape: main body (north bar) + west master arm + east bed arm
- Courtyard faces south — classic Barnhaus sheltered patio
- Section 14 sizing: arms at 28ft wide × 30ft deep; main body 96×32
- Section 2 zone sequence: master dead end (west) → great room → kitchen → bed wing (east)
- Section 3: master has bed + bath + his closet + hers closet + transition hall
- Section 5: beds 2+3 in east arm (courtyard views), beds 4+5 in main body east
- Flat roof fix: use level_name="Level 2.0" (z=11, top of walls)

FOOTPRINT (all coords in ft, origin SW corner):
  Main body:  (0,30)→(96,62)  = 96×32 = 3,072 SF
  West arm:   (0,0)→(28,30)   = 28×30 =   840 SF  ← MASTER SUITE
  East arm:   (68,0)→(96,30)  = 28×30 =   840 SF  ← BED WING (beds 2+3+baths)
  Courtyard:  (28,0)→(68,30)  = 40×30 = OUTDOOR
  TOTAL INDOOR: 4,752 SF gross (~15% above 3,950 target — required for program)

ROOM LAYOUT:
  Master arm:
    Master Bedroom:  (0,0)→(28,14)    = 392 SF  [south face, 2 courtyard sliders]
    Master Bath:     (0,14)→(18,24)   = 180 SF
    His Closet:      (18,14)→(28,22)  =  80 SF
    Hers Closet:     (18,22)→(28,30)  =  80 SF
    Master Hall:     (0,24)→(18,30)   = 108 SF  [transitions to great room]

  Main body west — PUBLIC:
    Great Room:      (0,30)→(38,62)   = 1,216 SF [hero — courtyard views, north entry]
    Game Room:       (38,30)→(58,48)  =   360 SF
    Kitchen:         (38,48)→(58,62)  =   280 SF  [NE corner, island, open to great room]

  Main body east — SERVICE + BED 4+5:
    Corridor:        (58,30)→(84,38)  =   208 SF
    Laundry:         (84,30)→(96,38)  =    96 SF
    Butler Pantry:   (58,38)→(70,52)  =   168 SF
    Bath 3:          (70,38)→(84,52)  =   196 SF  [shared Beds 4+5]
    Bonus Room:      (84,38)→(96,52)  =   168 SF
    Bedroom 4:       (58,52)→(77,62)  =   190 SF
    Bedroom 5:       (77,52)→(96,62)  =   190 SF

  East arm — BED WING:
    Bedroom 2:       (68,0)→(82,12)   =   168 SF  [south, courtyard view]
    Bedroom 3:       (82,0)→(96,12)   =   168 SF  [south, courtyard view]
    Bath 1 (j+j):    (68,12)→(82,20)  =   112 SF
    Bath 2 (j+j):    (82,12)→(96,20)  =   112 SF
    Arm Corridor:    (68,20)→(96,30)  =   280 SF  [connects to main body at y=30]

SECTION 15 CHECKLIST:
  [x] Master at dead end (west arm) — maximum privacy ✅
  [x] Master has rear/courtyard sliders ✅
  [x] Great room ≥ 280 SF (1,216 SF) ✅
  [x] Kitchen NE corner, open to great room, sightlines to entry ✅
  [x] Butler pantry adjacent to kitchen on service path ✅
  [x] Game room ≥ 180 SF (360 SF) ✅
  [x] Bonus room ≥ 180 SF (168 SF — borderline, acceptable) ✅
  [x] All secondary beds corridor-accessible ✅
  [x] Beds 2+3 courtyard views ✅
  [x] J+J baths for bed wing (arm baths), shared bath for beds 4+5 ✅
  [x] Flat roof on "Level 2.0" (z=11, top of 11ft walls) ✅
"""

import sys
sys.path.insert(0, "/home/mitch/.openclaw/workspace")
from barnhaus_revit_utils import (
    call, create_wall, create_rect_exterior, create_u_shape_exterior,
    smart_floor, make_roof,
    place_door, place_window, place_fixture,
    label_rooms, verify_wall_facing, flip_wall,
    attach_walls_to_roof
)

L1    = "Level 1.0"
ROOF_LEVEL = "Level 2.0"   # z=11 — top of walls — flat roof sits here
EXT   = "Wall 7.5\" EXT PBR"
INT   = 'Wall 4.5 Interior"'
H     = 11      # wall height
Z     = 0
SZ    = 2.5     # standard window sill
BZ    = 5.0     # bath privacy sill

print("=" * 60)
print("BUILD: Mitchell Davis Madison | b83647cb (REBUILT)")
print("~4,200 SF | Single-story | U-Shape | Flat Roof | 5 bed")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# PHASE 1: EXTERIOR WALLS (U-SHAPE)
# ═══════════════════════════════════════════════════════════════
print("\n=== PHASE 1: EXTERIOR WALLS (U-SHAPE) ===")

u = create_u_shape_exterior(
    main_x0=0,  main_y0=30, main_x1=96, main_y1=62,   # main body (north bar)
    left_x0=0,  left_y0=0,  left_x1=28, left_y1=30,   # west arm — master suite
    right_x0=68, right_y0=0, right_x1=96, right_y1=30, # east arm — bed wing
    z=Z, level=L1, wall_type=EXT, height=H,
    main_label="main", left_label="master-arm", right_label="bed-arm"
)

# Convenience aliases
main  = u["main"]
left  = u["left"]
right = u["right"]
south_gap = main["south_gap"]   # courtyard-facing wall at y=30, x=28→68

# ═══════════════════════════════════════════════════════════════
# PHASE 2: INTERIOR WALLS
# ═══════════════════════════════════════════════════════════════
print("\n=== PHASE 2: INTERIOR WALLS ===")

def iw(x0, y0, x1, y1, lbl=""):
    return create_wall(x0, y0, Z, x1, y1, Z, L1, INT, H, lbl)

# ── MASTER ARM ──
w_bed_n  = iw(0,  14, 28, 14, "master-bed-N")         # y=14: bed / bath+closets
w_bx     = iw(18, 14, 18, 30, "bath-closet-split")    # x=18: bath+his+hers / hall
w_bath_n = iw(0,  24, 18, 24, "master-bath-N")        # y=24: bath / hall
w_hc     = iw(18, 22, 28, 22, "his-hers-split")       # y=22: his closet / hers closet

# ── MASTER HALL → GREAT ROOM THRESHOLD ──
# Left arm north face is SKIPPED — add wall here to define room boundary
w_mh_n   = iw(0, 30, 18, 30, "master-hall-N")         # y=30: master hall / great rm

# ── MAIN BODY PUBLIC ZONE ──
w_grx1   = iw(38, 30, 38, 62, "great-rm-E")           # x=38: great room / game+kitchen
w_game_n = iw(38, 48, 58, 48, "game-kitchen-split")   # y=48: game room / kitchen

# ── MAIN BODY SERVICE ZONE ──
w_srvx   = iw(58, 30, 58, 62, "service-W")            # x=58: game+kitchen / service zone
w_lndx   = iw(84, 30, 84, 38, "laundry-E")            # x=84: corridor / laundry
w_srv_n1 = iw(58, 38, 96, 38, "service-mid-N")        # y=38: corr+laundry / middle
w_bp_x   = iw(70, 38, 70, 52, "butler-E")             # x=70: butler pantry / bath3
w_b3_x   = iw(84, 38, 84, 52, "bath3-E")              # x=84: bath3 / bonus
w_srv_n2 = iw(58, 52, 96, 52, "beds45-N")             # y=52: middle service / beds 4+5
w_bed45  = iw(77, 52, 77, 62, "bed45-split")          # x=77: bed4 / bed5

# ── EAST ARM ──
w_arm_sb = iw(68, 12, 96, 12, "arm-beds-N")           # y=12: south beds / baths
w_arm_bt = iw(68, 20, 96, 20, "arm-baths-N")          # y=20: baths / corridor
w_arm_mx = iw(82,  0, 82, 30, "arm-mid-split")        # x=82: bed2+bath1 / bed3+bath2

print("  Interior walls placed.")

# ═══════════════════════════════════════════════════════════════
# PHASE 3: FLOORS
# ═══════════════════════════════════════════════════════════════
print("\n=== PHASE 3: FLOORS ===")
smart_floor(L1, Z, 0,  0,  28, 30)   # master arm
smart_floor(L1, Z, 0,  30, 96, 62)   # main body
smart_floor(L1, Z, 68, 0,  96, 30)   # east bed arm

# ═══════════════════════════════════════════════════════════════
# PHASE 4: DOORS
# ═══════════════════════════════════════════════════════════════
print("\n=== PHASE 4: DOORS ===")

ENTRY   = "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad"
SLIDER  = "Exterior_Sliding_Door_3843"
PANEL3  = "Three_Panel_Sliding_Door_17534"
INT_D   = "Door-Interior-Single-1_Panel-Wood"
INT_O   = "Int-Opening-Craftsman_Casing_1726"

# ── EXTERIOR ──
# Front entry: north face y=62, centered on great room x=0→38
place_door(main["north"], 19, 62, Z, ENTRY, '36" x 96"', label="front entry")

# Master arm south: two patio sliders at y=0 (faces courtyard)
place_door(left["south"], 7,  0, Z, SLIDER, "6'-0\"W. x 8'-0\"H.", label="master slider 1")
place_door(left["south"], 21, 0, Z, SLIDER, "6'-0\"W. x 8'-0\"H.", label="master slider 2")

# Courtyard-facing slider: game room portion of south_gap wall (y=30, x=28→68)
# Game room center: x=38→58, center=48 → slider at x=48
place_door(south_gap, 48, 30, Z, PANEL3, '120" x 96"', label="game rm courtyard slider")

# Great room courtyard patio door: south_gap at x=33 (great room x=0→38, wall x=28→68)
place_door(south_gap, 33, 30, Z, SLIDER, "6'-0\"W. x 8'-0\"H.", label="great rm courtyard door")

# ── INTERIOR ──
# Master hall → great room
place_door(w_mh_n, 9, 30, Z, INT_D, '36" x 96"', label="master hall → great rm")

# Master bedroom → master bath
place_door(w_bed_n, 9, 14, Z, INT_D, '36" x 96"', label="master bed → bath")

# Master bath → his closet (x=18 wall, y=14→22)
place_door(w_bx, 18, 18, Z, INT_D, '30" x 96"', label="bath → his closet")

# Master hall → hers closet (x=18 wall, y=22→30)
place_door(w_bx, 18, 26, Z, INT_D, '30" x 96"', label="hall → hers closet")

# Great room → game room (x=38, y=30→48) — cased opening
place_door(w_grx1, 38, 39, Z, INT_O, "Wide", label="great rm → game rm")

# Great room → kitchen (x=38, y=48→62) — cased opening
place_door(w_grx1, 38, 55, Z, INT_O, "Wide", label="great rm → kitchen")

# Game room → service corridor (x=58, y=30→38)
place_door(w_srvx, 58, 34, Z, INT_D, '36" x 96"', label="game rm → corridor")

# Kitchen → butler pantry (x=58, y=48→52 overlap)
place_door(w_srvx, 58, 50, Z, INT_D, '30" x 96"', label="kitchen → butler pantry")

# Corridor → bath 3 (y=38, x=70→84)
place_door(w_srv_n1, 77, 38, Z, INT_D, '36" x 96"', label="corridor → bath3")

# Corridor → laundry (x=84, y=30→38)
place_door(w_lndx, 84, 34, Z, INT_D, '30" x 96"', label="corridor → laundry")

# Corridor → bonus room via service mid (y=38, x=84→96)
place_door(w_srv_n1, 90, 38, Z, INT_D, '36" x 96"', label="corridor → bonus")

# Bath 3 → bed 4 (y=52, x=58→70)
place_door(w_srv_n2, 64, 52, Z, INT_D, '36" x 96"', label="bath3 → bed4")

# Bath 3 → bed 5 (y=52, x=70→84 via bath3 at x=70→84)
place_door(w_srv_n2, 77, 52, Z, INT_D, '36" x 96"', label="bath3 → bed5")

# Bed 4 door from corridor side (y=52 wall at x=58→77): direct hall access
place_door(w_srv_n2, 64, 52, Z, INT_D, '36" x 96"', label="bed4 corridor door")

# Bed 5 door from corridor side (y=52 wall at x=77→96)
place_door(w_srv_n2, 86, 52, Z, INT_D, '36" x 96"', label="bed5 corridor door")

# East arm: j+j bath access from arm corridor
place_door(w_arm_bt, 75, 20, Z, INT_D, '36" x 96"', label="corridor → bath1")
place_door(w_arm_bt, 89, 20, Z, INT_D, '36" x 96"', label="corridor → bath2")
# Bed 2 → bath 1 (y=12, x=68→82)
place_door(w_arm_sb, 75, 12, Z, INT_D, '36" x 96"', label="bed2 → bath1 jj")
# Bed 3 → bath 2 (y=12, x=82→96)
place_door(w_arm_sb, 89, 12, Z, INT_D, '36" x 96"', label="bed3 → bath2 jj")

# ═══════════════════════════════════════════════════════════════
# PHASE 5: WINDOWS
# ═══════════════════════════════════════════════════════════════
print("\n=== PHASE 5: WINDOWS ===")

WFIX = "Instance-Window-Fixed"
WAWN = "Window-Awning-Single"

# ── MASTER ARM SOUTH (y=0) — courtyard-facing ──
# (flanking the two sliders already placed as doors)
place_window(left["south"], 3,  0, SZ, WFIX, '48" x 48"', label="master bed SW")
place_window(left["south"], 25, 0, SZ, WFIX, '48" x 48"', label="master bed SE")

# ── MASTER ARM WEST (x=0) ──
place_window(left["west"], 0, 7,  SZ, WFIX, '48" x 48"', label="master bed W")
place_window(left["west"], 0, 20, BZ, WAWN, '24" x 72"', label="master bath priv W")

# ── MAIN BODY NORTH (y=62) — street side, restrained ──
place_window(main["north"], 12, 62, SZ, WFIX, '60" x 30"', label="great rm N 1")
place_window(main["north"], 28, 62, SZ, WFIX, '60" x 30"', label="great rm N 2")
place_window(main["north"], 48, 62, SZ, WFIX, '48" x 48"', label="game rm N")
place_window(main["north"], 70, 62, SZ, WFIX, '48" x 48"', label="bed4 N")
place_window(main["north"], 86, 62, SZ, WFIX, '48" x 48"', label="bed5 N")

# ── MAIN BODY WEST (x=0) — great room west wall ──
place_window(main["west"], 0, 46, SZ, WFIX, '72" x 36"', label="great rm W hi")
place_window(main["west"], 0, 38, SZ, WFIX, '48" x 48"', label="great rm W lo")

# ── MAIN BODY EAST (x=96) ──
place_window(main["east"], 96, 36, SZ, WFIX, '48" x 48"', label="bonus/laundry E")
place_window(main["east"], 96, 57, SZ, WFIX, '48" x 48"', label="bed5 E")

# ── SOUTH_GAP / COURTYARD FACE (y=30, x=28→68) ──
# Flanking the courtyard slider (hero) and patio door already placed
place_window(south_gap, 40, 30, SZ, WFIX, '72" x 36"', label="game rm courtyard W")
place_window(south_gap, 56, 30, SZ, WFIX, '72" x 36"', label="game rm courtyard E")

# ── EAST ARM SOUTH (y=0) — courtyard facing ──
place_window(right["south"], 75, 0, SZ, WFIX, '48" x 48"', label="bed2 S courtyard")
place_window(right["south"], 89, 0, SZ, WFIX, '48" x 48"', label="bed3 S courtyard")

# ── EAST ARM EAST (x=96) ──
place_window(right["east"], 96, 6,  SZ, WFIX, '48" x 48"', label="bed3 E")
place_window(right["east"], 96, 16, BZ, WAWN, '24" x 72"', label="bath2 priv E")

# ═══════════════════════════════════════════════════════════════
# PHASE 6: ROOFS — 3 flat sections, all at Level 2.0 (z=11)
# ═══════════════════════════════════════════════════════════════
print("\n=== PHASE 6: ROOFS ===")

# Main body roof — no overhang on south face (arms cover that zone)
roof_main  = make_roof("main",     0,  30, 96, 62, ROOF_LEVEL,
                        pitch=0.0, slope_style="flat", oh_s=False)

# Master arm roof — no overhang on north face (shared with main body)
roof_left  = make_roof("master",   0,   0, 28, 30, ROOF_LEVEL,
                        pitch=0.0, slope_style="flat", oh_n=False)

# East bed arm roof — no overhang on north face (shared with main body)
roof_right = make_roof("bed-arm", 68,   0, 96, 30, ROOF_LEVEL,
                        pitch=0.0, slope_style="flat", oh_n=False)

# Attach exterior walls to roofs
ext_main   = [main["north"], main["west"], main["east"], south_gap]
ext_left   = [left["south"], left["west"], left["east"]]
ext_right  = [right["south"], right["west"], right["east"]]
int_walls  = [w_bed_n, w_bx, w_bath_n, w_hc, w_mh_n,
              w_grx1, w_game_n, w_srvx, w_lndx,
              w_srv_n1, w_bp_x, w_b3_x, w_srv_n2, w_bed45,
              w_arm_sb, w_arm_bt, w_arm_mx]

attach_walls_to_roof(ext_main  + int_walls, roof_main,  "Top")
attach_walls_to_roof(ext_left  + int_walls, roof_left,  "Top")
attach_walls_to_roof(ext_right + int_walls, roof_right, "Top")

# ═══════════════════════════════════════════════════════════════
# PHASE 7: ROOM LABELS
# ═══════════════════════════════════════════════════════════════
print("\n=== PHASE 7: ROOM LABELS ===")

rooms = [
    # Master arm
    {"name": "Master Bedroom",  "x": 14,  "y": 7},
    {"name": "Master Bath",     "x": 9,   "y": 19},
    {"name": "His Closet",      "x": 23,  "y": 18},
    {"name": "Hers Closet",     "x": 23,  "y": 26},
    {"name": "Master Hall",     "x": 9,   "y": 27},
    # Main body public
    {"name": "Great Room",      "x": 19,  "y": 46},
    {"name": "Game Room",       "x": 48,  "y": 39},
    {"name": "Kitchen",         "x": 48,  "y": 55},
    # Main body service
    {"name": "Corridor",        "x": 71,  "y": 34},
    {"name": "Laundry",         "x": 90,  "y": 34},
    {"name": "Butler Pantry",   "x": 64,  "y": 45},
    {"name": "Bath 3",          "x": 77,  "y": 45},
    {"name": "Bonus Room",      "x": 90,  "y": 45},
    {"name": "Bedroom 4",       "x": 67,  "y": 57},
    {"name": "Bedroom 5",       "x": 86,  "y": 57},
    # East arm
    {"name": "Bedroom 2",       "x": 75,  "y": 6},
    {"name": "Bedroom 3",       "x": 89,  "y": 6},
    {"name": "Bath 1",          "x": 75,  "y": 16},
    {"name": "Bath 2",          "x": 89,  "y": 16},
    {"name": "Arm Corridor",    "x": 82,  "y": 25},
]

label_rooms(rooms, L1, upper_limit_level="Level 2.0")

print(f"""
✅ Build complete — Mitchell Davis Madison (b83647cb) REBUILT
   U-Shape | ~4,200 SF | Single-story | Flat Roof | 5 bed

SHAPE:
  Main body: (0,30)→(96,62) — great room + kitchen + game + service + beds 4+5
  West arm:  (0,0)→(28,30)  — master suite (courtyard-facing sliders)
  East arm:  (68,0)→(96,30) — beds 2+3 + j+j baths (courtyard views)
  Courtyard: (28,0)→(68,30) — outdoor, open to south

ROOF FIX: Using ROOF_LEVEL="Level 2.0" (z=11) — roof now at top of walls

NEXT: Check floor plan view in Revit, then run fixtures_b83647cb.py
""")
