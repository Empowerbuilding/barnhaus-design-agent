"""
Mitchell Madison - 237e8fc6
L-shape, Contemporary, 3000 SF living
Main wing 16ft, secondary wing (beds) 12ft
Layout: ft:gpt-4o-2024-08-06:personal:barnhaus:DGsyA2j2

FOOTPRINT (S=street/front, N=views/back porch):

y=60 ─── FRONT/STREET ──────────────────────────────
     │         MAIN WING (x=0-68, y=20-60)          │
     │    Living | Kitchen | Dining | Master(far R)  │
y=20 ├────────────────────┬──────────────────────────┘
     │  SEC WING           │  (main wing continues E)
     │  x=0-40, y=0-20    │  BACK PORCH x=22-46 y=8-20
     │  Beds 2/3/4        │
y=0  └────────────────────┘ ← NORTH/VIEWS
     x=0                 x=40              x=68

Garage: x=-26 to 0, y=20-46 (attached left, OH doors S)
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, create_rect_exterior,
    place_door, place_window,
    smart_floor, make_roof, 
    create_hallway, create_room, label_rooms,
    layout_kitchen, layout_bath_standard, layout_bath_master,
    layout_laundry, place_fixture, _cab,
    attach_walls_to_roof,
    call, T, WIN
)

L1     = "Level 1.0"
L1R    = "L1 Roof"       # 10ft — use for 12ft wing roof base
L_GARR = "Garage Roof"   # 12ft
L_CBR  = "CB Roof"       # 16ft — main wing roof base
EXT    = 'Wall 7.5" EXT PBR'
INT    = 'Wall 4.5 Interior"'
IDOOR  = "Door-Interior-Single-1_Panel-Wood"
ISLIDE = "Exterior_Sliding_Door_3843"
GOHD   = "Door-Garage-Flush_Panel"
WFAM   = "Instance-Window-Fixed"

H_MAIN = 16   # main wing plate height
H_SEC  = 12   # secondary wing (beds) plate height
H_GAR  = 12   # garage plate height
PITCH  = 0.333

print("=" * 60)
print("BUILD: Mitchell Madison | 237e8fc6")
print("3,000 SF | Contemporary | L-Shape | AI Layout")
print("=" * 60)

# ── PHASE 1: EXTERIOR WALLS ────────────────────────────────

print("\n=== PHASE 1: EXTERIOR WALLS ===")

# MAIN WING (x=0–68, y=20–60) — 16ft walls
# Skip north face on W half (0-40) where secondary wing attaches
mw = create_rect_exterior(0, 20, 68, 60, 0, L1, EXT, H_MAIN, "MW")
# North partial wall x=40–68 (right half only — left half is secondary wing)
w_mw_n_partial = create_wall(40, 20, 0, 68, 20, 0, L1, EXT, H_MAIN, "MW N partial")

# SECONDARY WING (x=0–40, y=0–20) — 12ft walls
# Skip south face (opens into main wing at y=20)
sw = create_rect_exterior(0, 0, 40, 20, 0, L1, EXT, H_SEC, "SW", skip_faces=["south"])

# GARAGE (x=-26–0, y=20–46) — 12ft walls
gw = create_rect_exterior(-26, 20, 0, 46, 0, L1, EXT, H_GAR, "GAR")

print("\n=== PHASE 2: FLOORS ===")

# Single polygon floor — entire L footprint + garage
smart_floor(L1, 0, -26, 20, 68, 60)   # won't work as single — do separately
# Main wing
smart_floor(L1, 0, 0, 20, 68, 60)
# Secondary wing  
smart_floor(L1, 0, 0, 0, 40, 20)
# Garage
smart_floor(L1, 0, -26, 20, 0, 46)

print("\n=== PHASE 3: ROOFS ===")

# Main wing gable — ridge E-W, 16ft walls → use CB Roof level (16ft)
r_main = make_roof("Main wing", 0, 20, 68, 60, L_CBR,
                   pitch=PITCH, slope_style="gable")
if r_main and mw:
    attach_walls_to_roof(list(mw.values()), r_main)

# Secondary wing shed — slopes N (low) to S (high joins main), 12ft walls → L1 Roof
r_sec = make_roof("Sec wing", 0, 0, 40, 20, L1R,
                  pitch=PITCH, slope_style="shed", shed_low_edge=0, oh_s=False)
if r_sec and sw:
    attach_walls_to_roof(list(sw.values()), r_sec)

# Garage flat — 12ft → Garage Roof level
r_gar = make_roof("Garage", -26, 20, 0, 46, L_GARR,
                  pitch=0, slope_style="flat")
if r_gar and gw:
    attach_walls_to_roof(list(gw.values()), r_gar)

# Back porch — flat, no walls (posts only)
r_porch = make_roof("Back porch", 22, 8, 46, 20, L1R,
                    pitch=0, slope_style="flat", oh_n=True, oh_e=True, oh_w=True)

print("\n=== PHASE 4: INTERIOR WALLS ===")

# ── MAIN WING divisions ──────────────────────────────────
# Master suite: far right x=50–68
w_master_w = create_wall(50, 20, 0, 50, 60, 0, L1, INT, H_MAIN, "Master W wall")

# Master bath/closet split (horizontal at y=40)
w_master_bath = create_wall(50, 40, 0, 68, 40, 0, L1, INT, H_MAIN, "Master bath N")

# Mud room / garage entry: x=0–12, y=20–36
w_mud_e = create_wall(12, 20, 0, 12, 36, 0, L1, INT, H_MAIN, "Mud E wall")
w_mud_n = create_wall(0, 36, 0, 12, 36, 0, L1, INT, H_MAIN, "Mud N wall")

# Butler pantry: x=12–24, y=20–32
w_bp_e = create_wall(24, 20, 0, 24, 32, 0, L1, INT, H_MAIN, "Butler pantry E")
w_bp_n = create_wall(12, 32, 0, 24, 32, 0, L1, INT, H_MAIN, "Butler pantry N")

# Great room open to kitchen — no wall, just ceiling change
# Half bath: x=24–32, y=20–28
w_hb_e = create_wall(32, 20, 0, 32, 28, 0, L1, INT, H_MAIN, "Half bath E")
w_hb_n = create_wall(24, 28, 0, 32, 28, 0, L1, INT, H_MAIN, "Half bath N")

# Laundry/utility: x=0–12, y=36–50
w_lau_e = create_wall(12, 36, 0, 12, 50, 0, L1, INT, H_MAIN, "Laundry E wall")
w_lau_n = create_wall(0, 50, 0, 12, 50, 0, L1, INT, H_MAIN, "Laundry N wall")

# ── SECONDARY WING divisions ─────────────────────────────
# 3 beds across 40ft: Bed2 x=0-14, Bath x=14-20, Bed3 x=20-28, Bed4 x=28-40
w_b2_e   = create_wall(14, 0, 0, 14, 20, 0, L1, INT, H_SEC, "Bed2 E / Bath W")
w_b3_w   = create_wall(20, 0, 0, 20, 20, 0, L1, INT, H_SEC, "Bath E / Bed3 W")
w_b3_e   = create_wall(28, 0, 0, 28, 20, 0, L1, INT, H_SEC, "Bed3 E / Bed4 W")

print("\n=== PHASE 5: DOORS ===")

# Front entry (S face main wing centered)
place_door(mw.get("south"), 34, 60, 0, "Door-Exterior-Single-1_Panel", '36" x 84"',
           label="Front Entry", level=L1)

# Garage OH door (S face garage)
place_door(gw.get("south"), -13, 46, 0, GOHD, "16W X 10H",
           label="Garage OH", level=L1)

# Garage man door to mud room
place_door(gw.get("east"), -1, 33, 0, IDOOR, '36" x 96"',
           label="Garage→Mud", level=L1)

# Back porch sliders (N face main wing)
place_door(mw.get("north") or w_mw_n_partial, 54, 20, 0, ISLIDE, '8\'-0"W. x 8\'-0"H. 2',
           label="Back porch slider", level=L1)

# Master bedroom door
place_door(w_master_w, 50, 50, 0, IDOOR, '36" x 96"',
           label="Master door", level=L1)

# Interior room doors
place_door(w_mud_e, 12, 28, 0, IDOOR, '36" x 96"', label="Mud door", level=L1)
place_door(w_lau_e, 12, 43, 0, IDOOR, '36" x 96"', label="Laundry door", level=L1)

print("\n=== PHASE 6: WINDOWS ===")

# Main wing — S face windows
place_window(mw.get("south"), 20, 60, 3.5, WFAM, '4\'0" x 5\'0"', "Living S win", L1)
place_window(mw.get("south"), 40, 60, 3.5, WFAM, '4\'0" x 5\'0"', "Kitchen S win", L1)

# Master — E face
place_window(mw.get("east"), 68, 30, 4, WFAM, '4\'0" x 5\'0"', "Master E win", L1)
place_window(mw.get("east"), 68, 50, 4, WFAM, '4\'0" x 5\'0"', "Master E win2", L1)

# Secondary wing — N face windows
place_window(sw.get("north"), 7, 0, 3.5, WFAM, '4\'0" x 5\'0"', "Bed2 N win", L1)
place_window(sw.get("north"), 24, 0, 3.5, WFAM, '4\'0" x 5\'0"', "Bed3 N win", L1)
place_window(sw.get("north"), 34, 0, 3.5, WFAM, '4\'0" x 5\'0"', "Bed4 N win", L1)

print("\n=== PHASE 7: ROOM LABELS ===")
label_rooms([
    {"name": "Great Room",     "x": 25, "y": 45},
    {"name": "Kitchen",        "x": 38, "y": 35},
    {"name": "Dining",         "x": 25, "y": 28},
    {"name": "Master Bedroom", "x": 59, "y": 50},
    {"name": "Master Bath",    "x": 59, "y": 30},
    {"name": "Mud Room",       "x": 6,  "y": 28},
    {"name": "Butler Pantry",  "x": 18, "y": 26},
    {"name": "Laundry",        "x": 6,  "y": 43},
    {"name": "Half Bath",      "x": 28, "y": 24},
    {"name": "Bedroom 2",      "x": 7,  "y": 10},
    {"name": "Bath 2",         "x": 17, "y": 10},
    {"name": "Bedroom 3",      "x": 24, "y": 10},
    {"name": "Bedroom 4",      "x": 34, "y": 10},
    {"name": "Garage",         "x": -13,"y": 33},
], L1, upper_limit_level="L1 Roof")

print("\n=== BUILD COMPLETE ===")
print("Mitchell Madison | L-shape | Contemporary")
print("Main wing 16ft | Sec wing 12ft | Garage 12ft")
